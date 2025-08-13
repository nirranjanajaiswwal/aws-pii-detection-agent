#!/usr/bin/env python3
"""
Data discovery and Data classificationAgent - Real AWS MCP Server
"""

import asyncio
import json
import logging
import boto3
import re
import sys
import os
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent

# Add the core module to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
from pii_agent import AWSPIIDetectionAgent, PIIDetectionConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aws-pii-detection-mcp")

server = Server("aws-pii-detection-agent")

class AWSPIIDetector:
    def __init__(self, region='us-west-2'):
        self.region = region
        self.s3 = boto3.client('s3', region_name=region)
        self.dynamodb = boto3.client('dynamodb', region_name=region)
        self.glue = boto3.client('glue', region_name=region)
        
    def detect_pii_in_text(self, text: str) -> List[str]:
        """Simple PII detection patterns"""
        pii_types = []
        
        # Email pattern
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
            pii_types.append('EMAIL')
        
        # SSN pattern
        if re.search(r'\b\d{3}-\d{2}-\d{4}\b', text):
            pii_types.append('SSN')
        
        # Phone pattern
        if re.search(r'\b\d{3}-\d{3}-\d{4}\b', text):
            pii_types.append('PHONE')
        
        return pii_types
    
    async def scan_s3_bucket(self, bucket_name: str, max_objects: int = 10):
        """Scan S3 bucket for PII"""
        try:
            response = self.s3.list_objects_v2(Bucket=bucket_name, MaxKeys=max_objects)
            results = []
            
            for obj in response.get('Contents', [])[:max_objects]:
                key = obj['Key']
                if key.endswith(('.txt', '.csv', '.json')):
                    try:
                        content = self.s3.get_object(Bucket=bucket_name, Key=key)
                        text = content['Body'].read().decode('utf-8')[:1000]  # First 1KB
                        pii_types = self.detect_pii_in_text(text)
                        
                        if pii_types:
                            results.append({
                                'bucket': bucket_name,
                                'key': key,
                                'pii_types': pii_types,
                                'size': obj['Size']
                            })
                    except Exception as e:
                        logger.warning(f"Error reading {key}: {e}")
            
            return results
        except Exception as e:
            logger.error(f"Error scanning S3 bucket {bucket_name}: {e}")
            return []
    
    async def scan_dynamodb_table(self, table_name: str, max_items: int = 10):
        """Scan DynamoDB table for PII"""
        try:
            response = self.dynamodb.scan(
                TableName=table_name,
                Limit=max_items
            )
            
            results = []
            for item in response.get('Items', []):
                pii_types = []
                for attr_name, attr_value in item.items():
                    if 'S' in attr_value:  # String attribute
                        text = attr_value['S']
                        pii_types.extend(self.detect_pii_in_text(text))
                
                if pii_types:
                    results.append({
                        'table': table_name,
                        'pii_types': list(set(pii_types)),
                        'attributes': list(item.keys())
                    })
            
            return results
        except Exception as e:
            logger.error(f"Error scanning DynamoDB table {table_name}: {e}")
            return []

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    return [
        Tool(
            name="scan_s3_real",
            description="Scan real S3 bucket for PII content",
            inputSchema={
                "type": "object",
                "properties": {
                    "bucket_name": {"type": "string", "description": "S3 bucket name"},
                    "region": {"type": "string", "default": "us-west-2"},
                    "max_objects": {"type": "integer", "default": 10, "maximum": 50}
                },
                "required": ["bucket_name"]
            }
        ),
        Tool(
            name="scan_dynamodb_real",
            description="Scan real DynamoDB table for PII content",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "DynamoDB table name"},
                    "region": {"type": "string", "default": "us-west-2"},
                    "max_items": {"type": "integer", "default": 10, "maximum": 100}
                },
                "required": ["table_name"]
            }
        ),
        Tool(
            name="list_s3_buckets",
            description="List available S3 buckets",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {"type": "string", "default": "us-west-2"}
                }
            }
        ),
        Tool(
            name="list_dynamodb_tables",
            description="List available DynamoDB tables",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {"type": "string", "default": "us-west-2"}
                }
            }
        ),
        Tool(
            name="create_lf_tags",
            description="Create Lake Formation tag definitions",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {"type": "string", "default": "us-west-2"},
                    "dry_run": {"type": "boolean", "default": True}
                }
            }
        ),
        Tool(
            name="register_s3_with_lakeformation",
            description="Register S3 location with Lake Formation",
            inputSchema={
                "type": "object",
                "properties": {
                    "s3_path": {"type": "string", "description": "S3 path to register (e.g., s3://bucket/path/)"},
                    "region": {"type": "string", "default": "us-west-2"},
                    "dry_run": {"type": "boolean", "default": True}
                },
                "required": ["s3_path"]
            }
        ),
        Tool(
            name="register_table_with_lakeformation",
            description="Register Glue table with Lake Formation",
            inputSchema={
                "type": "object",
                "properties": {
                    "database_name": {"type": "string", "description": "Glue database name"},
                    "table_name": {"type": "string", "description": "Glue table name"},
                    "region": {"type": "string", "default": "us-west-2"},
                    "dry_run": {"type": "boolean", "default": True}
                },
                "required": ["database_name", "table_name"]
            }
        ),
        Tool(
            name="apply_lf_tags",
            description="Apply Lake Formation tags to resources based on PII detection",
            inputSchema={
                "type": "object",
                "properties": {
                    "database_name": {"type": "string", "description": "Glue database name"},
                    "table_name": {"type": "string", "description": "Glue table name"},
                    "column_name": {"type": "string", "description": "Column name (optional)"},
                    "pii_types": {"type": "array", "items": {"type": "string"}, "description": "List of detected PII types"},
                    "region": {"type": "string", "default": "us-west-2"},
                    "dry_run": {"type": "boolean", "default": True}
                },
                "required": ["database_name", "table_name"]
            }
        ),
        Tool(
            name="manage_lake_formation_tags",
            description="Manage Lake Formation tag definitions",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["create", "delete", "update", "list"]},
                    "tag_key": {"type": "string", "description": "Tag key name"},
                    "tag_values": {"type": "array", "items": {"type": "string"}, "description": "Tag values"},
                    "region": {"type": "string", "default": "us-west-2"},
                    "dry_run": {"type": "boolean", "default": True}
                },
                "required": ["operation"]
            }
        ),
        Tool(
            name="register_lake_formation_resources",
            description="Register resources with Lake Formation",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_type": {"type": "string", "enum": ["s3", "table", "database"]},
                    "resource_arn": {"type": "string", "description": "Resource ARN for S3 locations"},
                    "database_name": {"type": "string", "description": "Database name for tables"},
                    "table_name": {"type": "string", "description": "Table name"},
                    "region": {"type": "string", "default": "us-west-2"},
                    "dry_run": {"type": "boolean", "default": True}
                },
                "required": ["resource_type"]
            }
        ),
        Tool(
            name="apply_lake_formation_tags",
            description="Apply Lake Formation tags to specific resources",
            inputSchema={
                "type": "object",
                "properties": {
                    "database_name": {"type": "string", "description": "Database name"},
                    "table_name": {"type": "string", "description": "Table name"},
                    "column_name": {"type": "string", "description": "Column name (optional)"},
                    "lf_tags": {"type": "array", "items": {"type": "object"}, "description": "Lake Formation tags to apply"},
                    "region": {"type": "string", "default": "us-west-2"},
                    "dry_run": {"type": "boolean", "default": True}
                },
                "required": ["database_name", "table_name"]
            }
        ),
        Tool(
            name="manage_lake_formation_permissions",
            description="Manage Lake Formation permissions and access control",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["grant", "revoke", "list"]},
                    "principal": {"type": "string", "description": "IAM principal (user/role ARN)"},
                    "resource": {"type": "object", "description": "Resource definition"},
                    "permissions": {"type": "array", "items": {"type": "string"}, "description": "Permissions to grant/revoke"},
                    "region": {"type": "string", "default": "us-west-2"},
                    "dry_run": {"type": "boolean", "default": True}
                },
                "required": ["operation"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    try:
        region = arguments.get("region", "us-west-2")
        detector = AWSPIIDetector(region)
        
        if name == "scan_s3_real":
            bucket_name = arguments["bucket_name"]
            max_objects = arguments.get("max_objects", 10)
            
            results = await detector.scan_s3_bucket(bucket_name, max_objects)
            
            if results:
                text = f"🔍 S3 PII Scan Results - Bucket: {bucket_name}\n\n"
                for result in results:
                    text += f"📄 {result['key']}\n"
                    text += f"   PII Types: {', '.join(result['pii_types'])}\n"
                    text += f"   Size: {result['size']} bytes\n\n"
            else:
                text = f"✅ No PII found in bucket: {bucket_name}"
            
            return [TextContent(type="text", text=text)]
        
        elif name == "scan_dynamodb_real":
            table_name = arguments["table_name"]
            max_items = arguments.get("max_items", 10)
            
            results = await detector.scan_dynamodb_table(table_name, max_items)
            
            if results:
                text = f"🔍 DynamoDB PII Scan Results - Table: {table_name}\n\n"
                for result in results:
                    text += f"📊 PII Types: {', '.join(result['pii_types'])}\n"
                    text += f"   Attributes: {', '.join(result['attributes'])}\n\n"
            else:
                text = f"✅ No PII found in table: {table_name}"
            
            return [TextContent(type="text", text=text)]
        
        elif name == "list_s3_buckets":
            try:
                response = detector.s3.list_buckets()
                buckets = [bucket['Name'] for bucket in response['Buckets']]
                text = f"📦 S3 Buckets in {region}:\n\n"
                for bucket in buckets[:20]:  # Limit to 20
                    text += f"   • {bucket}\n"
                if len(buckets) > 20:
                    text += f"   ... and {len(buckets) - 20} more"
            except Exception as e:
                text = f"❌ Error listing S3 buckets: {str(e)}"
            
            return [TextContent(type="text", text=text)]
        
        elif name == "list_dynamodb_tables":
            try:
                response = detector.dynamodb.list_tables()
                tables = response['TableNames']
                text = f"🗃️ DynamoDB Tables in {region}:\n\n"
                for table in tables[:20]:  # Limit to 20
                    text += f"   • {table}\n"
                if len(tables) > 20:
                    text += f"   ... and {len(tables) - 20} more"
            except Exception as e:
                text = f"❌ Error listing DynamoDB tables: {str(e)}"
            
            return [TextContent(type="text", text=text)]
        
        elif name == "create_lf_tags":
            region = arguments.get("region", "us-west-2")
            dry_run = arguments.get("dry_run", True)
            
            config = PIIDetectionConfig(
                aws_region=region,
                dry_run=dry_run
            )
            
            agent = AWSPIIDetectionAgent(config)
            created_tags = await agent.create_lake_formation_tags()
            
            text = f"🏷️ Lake Formation Tag Definitions Created\n\n"
            text += f"🌍 Region: {region}\n"
            if dry_run:
                text += "🔍 Mode: DRY RUN (no actual changes made)\n"
            text += "\n📋 Tag Definitions:\n"
            
            for tag_key, tag_values in created_tags.items():
                text += f"\n🔖 {tag_key}:\n"
                for value in tag_values:
                    text += f"   • {value}\n"
            
            return [TextContent(type="text", text=text)]
        
        elif name == "register_s3_with_lakeformation":
            s3_path = arguments["s3_path"]
            region = arguments.get("region", "us-west-2")
            dry_run = arguments.get("dry_run", True)
            
            config = PIIDetectionConfig(
                aws_region=region,
                dry_run=dry_run
            )
            
            agent = AWSPIIDetectionAgent(config)
            success = await agent.register_s3_location_with_lakeformation(s3_path)
            
            if success:
                text = f"✅ Successfully registered S3 location with Lake Formation\n"
                text += f"📍 Location: {s3_path}\n"
                text += f"🌍 Region: {region}\n"
                if dry_run:
                    text += "🔍 Mode: DRY RUN (no actual changes made)"
            else:
                text = f"❌ Failed to register S3 location with Lake Formation\n"
                text += f"📍 Location: {s3_path}"
            
            return [TextContent(type="text", text=text)]
        
        elif name == "register_table_with_lakeformation":
            database_name = arguments["database_name"]
            table_name = arguments["table_name"]
            region = arguments.get("region", "us-west-2")
            dry_run = arguments.get("dry_run", True)
            
            config = PIIDetectionConfig(
                aws_region=region,
                dry_run=dry_run
            )
            
            agent = AWSPIIDetectionAgent(config)
            success = await agent.register_table_with_lakeformation(database_name, table_name)
            
            if success:
                text = f"✅ Successfully registered table with Lake Formation\n"
                text += f"🗃️ Table: {database_name}.{table_name}\n"
                text += f"🌍 Region: {region}\n"
                if dry_run:
                    text += "🔍 Mode: DRY RUN (no actual changes made)"
            else:
                text = f"❌ Failed to register table with Lake Formation\n"
                text += f"🗃️ Table: {database_name}.{table_name}"
            
            return [TextContent(type="text", text=text)]
        
        elif name == "apply_lf_tags":
            database_name = arguments["database_name"]
            table_name = arguments["table_name"]
            column_name = arguments.get("column_name")
            pii_types = arguments.get("pii_types", [])
            region = arguments.get("region", "us-west-2")
            dry_run = arguments.get("dry_run", True)
            
            config = PIIDetectionConfig(
                aws_region=region,
                dry_run=dry_run
            )
            
            agent = AWSPIIDetectionAgent(config)
            success = await agent.apply_lf_tags_to_resource(
                database_name, table_name, column_name, pii_types
            )
            
            resource_desc = f"{database_name}.{table_name}"
            if column_name:
                resource_desc += f".{column_name}"
            
            if success:
                text = f"✅ Successfully applied Lake Formation tags\n"
                text += f"🎯 Resource: {resource_desc}\n"
                text += f"🏷️ PII Types: {', '.join(pii_types) if pii_types else 'None'}\n"
                text += f"🌍 Region: {region}\n"
                if dry_run:
                    text += "🔍 Mode: DRY RUN (no actual changes made)"
            else:
                text = f"❌ Failed to apply Lake Formation tags\n"
                text += f"🎯 Resource: {resource_desc}"
            
            return [TextContent(type="text", text=text)]
        
        elif name == "manage_lake_formation_tags":
            operation = arguments["operation"]
            tag_key = arguments.get("tag_key")
            tag_values = arguments.get("tag_values", [])
            region = arguments.get("region", "us-west-2")
            dry_run = arguments.get("dry_run", True)
            
            config = PIIDetectionConfig(aws_region=region, dry_run=dry_run)
            agent = AWSPIIDetectionAgent(config)
            
            response = await agent.mcp_client.manage_lake_formation_tags(operation, tag_key, tag_values)
            
            if response.get('success'):
                text = f"✅ Lake Formation tag {operation} completed\n"
                text += f"🏷️ Tag: {tag_key}\n" if tag_key else ""
                text += f"🌍 Region: {region}\n"
                if dry_run:
                    text += "🔍 Mode: DRY RUN"
            else:
                text = f"❌ Lake Formation tag {operation} failed: {response.get('error')}"
            
            return [TextContent(type="text", text=text)]
        
        elif name == "register_lake_formation_resources":
            resource_type = arguments["resource_type"]
            resource_arn = arguments.get("resource_arn")
            database_name = arguments.get("database_name")
            table_name = arguments.get("table_name")
            region = arguments.get("region", "us-west-2")
            dry_run = arguments.get("dry_run", True)
            
            config = PIIDetectionConfig(aws_region=region, dry_run=dry_run)
            agent = AWSPIIDetectionAgent(config)
            
            response = await agent.mcp_client.register_lake_formation_resources(
                resource_type, resource_arn, database_name, table_name
            )
            
            if response.get('success'):
                text = f"✅ {resource_type.upper()} resource registered with Lake Formation\n"
                text += f"🎯 Resource: {resource_arn or f'{database_name}.{table_name}'}\n"
                text += f"🌍 Region: {region}\n"
                if dry_run:
                    text += "🔍 Mode: DRY RUN"
            else:
                text = f"❌ Resource registration failed: {response.get('error')}"
            
            return [TextContent(type="text", text=text)]
        
        elif name == "apply_lake_formation_tags":
            database_name = arguments["database_name"]
            table_name = arguments["table_name"]
            column_name = arguments.get("column_name")
            lf_tags = arguments.get("lf_tags", [])
            region = arguments.get("region", "us-west-2")
            dry_run = arguments.get("dry_run", True)
            
            config = PIIDetectionConfig(aws_region=region, dry_run=dry_run)
            agent = AWSPIIDetectionAgent(config)
            
            response = await agent.mcp_client.apply_lake_formation_tags(
                database_name, table_name, column_name, lf_tags
            )
            
            resource_desc = f"{database_name}.{table_name}"
            if column_name:
                resource_desc += f".{column_name}"
            
            if response.get('success'):
                text = f"✅ Lake Formation tags applied\n"
                text += f"🎯 Resource: {resource_desc}\n"
                text += f"🏷️ Tags: {len(lf_tags)} applied\n"
                text += f"🌍 Region: {region}\n"
                if dry_run:
                    text += "🔍 Mode: DRY RUN"
            else:
                text = f"❌ Tag application failed: {response.get('error')}"
            
            return [TextContent(type="text", text=text)]
        
        elif name == "manage_lake_formation_permissions":
            operation = arguments["operation"]
            principal = arguments.get("principal")
            resource = arguments.get("resource", {})
            permissions = arguments.get("permissions", [])
            region = arguments.get("region", "us-west-2")
            dry_run = arguments.get("dry_run", True)
            
            config = PIIDetectionConfig(aws_region=region, dry_run=dry_run)
            agent = AWSPIIDetectionAgent(config)
            
            response = await agent.mcp_client.manage_lake_formation_permissions(
                operation, principal, resource, permissions
            )
            
            if response.get('success'):
                text = f"✅ Lake Formation permissions {operation} completed\n"
                text += f"👤 Principal: {principal}\n" if principal else ""
                text += f"🔐 Permissions: {', '.join(permissions)}\n" if permissions else ""
                text += f"🌍 Region: {region}\n"
                if dry_run:
                    text += "🔍 Mode: DRY RUN"
            else:
                text = f"❌ Permission {operation} failed: {response.get('error')}"
            
            return [TextContent(type="text", text=text)]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="aws-pii-detection-agent",
                server_version="1.0.0",
                capabilities=server.get_capabilities()
            )
        )

if __name__ == "__main__":
    asyncio.run(main())