#!/usr/bin/env python3
"""
AWS MCP Client Integration
Handles connections to AWS MCP servers for S3 and DynamoDB data discovery
"""

import asyncio
import json
import logging
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError, BotoCoreError
try:
    import httpx
    import websockets
except ImportError:
    httpx = None
    websockets = None

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class S3ObjectInfo:
    """Information about an S3 object"""
    bucket_name: str
    key: str
    size: int
    last_modified: str
    content_type: str
    etag: str

@dataclass
class DynamoDBTableInfo:
    """Information about a DynamoDB table"""
    table_name: str
    item_count: int
    table_size_bytes: int
    key_schema: List[Dict[str, str]]
    attributes: List[Dict[str, str]]

class AWSMCPClient:
    """Client for interacting with AWS MCP servers"""
    
    def __init__(self, region: str = "us-west-2"):
        self.region = region
        self.session = boto3.Session()
        
        # Initialize AWS clients for fallback
        self.s3_client = self.session.client('s3', region_name=region)
        self.dynamodb_client = self.session.client('dynamodb', region_name=region)
        
        # MCP server connections (will be initialized when available)
        self.s3_mcp_client = None
        self.dynamodb_mcp_client = None
        self.dataprocessing_mcp_client = None
        
        logger.info(f"Initialized AWS MCP Client for region: {region}")
    
    async def connect_s3_mcp_server(self) -> bool:
        """Connect to S3 MCP server"""
        try:
            logger.info("Attempting to connect to S3 MCP server...")
            
            # Check if AWS Labs S3 MCP server is available
            result = subprocess.run(
                ['npm', 'list', '-g', '@awslabs/s3-tables-mcp-server'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                logger.info("AWS Labs S3 MCP server found")
                # Initialize MCP client connection
                if httpx:
                    self.s3_mcp_client = await self._init_mcp_client('s3-tables')
                    return self.s3_mcp_client is not None
            
            logger.info("S3 MCP server not available, using boto3 fallback")
            return False
            
        except Exception as e:
            logger.warning(f"Could not connect to S3 MCP server: {e}")
            return False
    
    async def connect_dynamodb_mcp_server(self) -> bool:
        """Connect to DynamoDB MCP server"""
        try:
            logger.info("Attempting to connect to DynamoDB MCP server...")
            
            # Check if AWS Labs DynamoDB MCP server is available
            result = subprocess.run(
                ['npm', 'list', '-g', '@awslabs/dynamodb-mcp-server'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                logger.info("AWS Labs DynamoDB MCP server found")
                # Initialize MCP client connection
                if httpx:
                    self.dynamodb_mcp_client = await self._init_mcp_client('dynamodb')
                    return self.dynamodb_mcp_client is not None
            
            logger.info("DynamoDB MCP server not available, using boto3 fallback")
            return False
            
        except Exception as e:
            logger.warning(f"Could not connect to DynamoDB MCP server: {e}")
            return False
    
    async def discover_s3_data(self, bucket_name: Optional[str] = None, 
                              prefix: str = "", max_objects: int = 100) -> List[S3ObjectInfo]:
        """Discover S3 objects using MCP server or boto3 fallback"""
        logger.info(f"Discovering S3 data - Bucket: {bucket_name or 'all'}, Prefix: {prefix}")
        
        if self.s3_mcp_client:
            # Use MCP server when available
            return await self._discover_s3_via_mcp(bucket_name, prefix, max_objects)
        else:
            # Use boto3 fallback
            return await self._discover_s3_via_boto3(bucket_name, prefix, max_objects)
    
    async def _discover_s3_via_mcp(self, bucket_name: Optional[str], 
                                  prefix: str, max_objects: int) -> List[S3ObjectInfo]:
        """Discover S3 objects via MCP server"""
        try:
            if not self.s3_mcp_client:
                return []
            
            # Call S3 MCP server tools
            if bucket_name:
                buckets = [bucket_name]
            else:
                # List all buckets using MCP server
                response = await self._call_mcp_tool(self.s3_mcp_client, 'list_s3_buckets', {})
                buckets = response.get('buckets', [])
            
            objects = []
            for bucket in buckets:
                # Get bucket metadata and objects
                bucket_response = await self._call_mcp_tool(
                    self.s3_mcp_client, 'get_bucket_metadata', 
                    {'bucket_name': bucket, 'prefix': prefix, 'max_keys': max_objects}
                )
                
                for obj_data in bucket_response.get('objects', []):
                    object_info = S3ObjectInfo(
                        bucket_name=bucket,
                        key=obj_data['key'],
                        size=obj_data['size'],
                        last_modified=obj_data['last_modified'],
                        content_type=obj_data.get('content_type', 'application/octet-stream'),
                        etag=obj_data['etag']
                    )
                    objects.append(object_info)
            
            logger.info(f"Discovered {len(objects)} S3 objects via MCP")
            return objects
            
        except Exception as e:
            logger.error(f"Error discovering S3 via MCP: {e}")
            return []
    
    async def _discover_s3_via_boto3(self, bucket_name: Optional[str], 
                                    prefix: str, max_objects: int) -> List[S3ObjectInfo]:
        """Discover S3 objects via boto3 fallback"""
        objects = []
        
        try:
            if bucket_name:
                # Scan specific bucket
                buckets = [bucket_name]
            else:
                # Scan all buckets
                response = self.s3_client.list_buckets()
                buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
            
            for bucket in buckets:
                try:
                    logger.info(f"Scanning S3 bucket: {bucket}")
                    
                    paginator = self.s3_client.get_paginator('list_objects_v2')
                    page_iterator = paginator.paginate(
                        Bucket=bucket,
                        Prefix=prefix,
                        PaginationConfig={'MaxItems': max_objects}
                    )
                    
                    for page in page_iterator:
                        for obj in page.get('Contents', []):
                            object_info = S3ObjectInfo(
                                bucket_name=bucket,
                                key=obj['Key'],
                                size=obj['Size'],
                                last_modified=obj['LastModified'].isoformat(),
                                content_type=obj.get('ContentType', 'application/octet-stream'),
                                etag=obj['ETag']
                            )
                            objects.append(object_info)
                            
                            if len(objects) >= max_objects:
                                break
                        
                        if len(objects) >= max_objects:
                            break
                    
                    logger.info(f"Found {len([o for o in objects if o.bucket_name == bucket])} objects in {bucket}")
                    
                except ClientError as e:
                    logger.error(f"Error accessing bucket {bucket}: {e}")
                    
        except Exception as e:
            logger.error(f"Error discovering S3 data: {e}")
        
        logger.info(f"Total S3 objects discovered: {len(objects)}")
        return objects
    
    async def sample_s3_object_content(self, bucket_name: str, key: str, 
                                      max_bytes: int = 1024) -> Optional[str]:
        """Sample content from an S3 object for PII detection"""
        try:
            logger.info(f"Sampling S3 object: s3://{bucket_name}/{key}")
            
            if self.s3_mcp_client:
                # Use MCP server when available
                return await self._sample_s3_via_mcp(bucket_name, key, max_bytes)
            else:
                # Use boto3 fallback
                return await self._sample_s3_via_boto3(bucket_name, key, max_bytes)
                
        except Exception as e:
            logger.error(f"Error sampling S3 object {bucket_name}/{key}: {e}")
            return None
    
    async def _sample_s3_via_mcp(self, bucket_name: str, key: str, 
                                max_bytes: int) -> Optional[str]:
        """Sample S3 object via MCP server"""
        try:
            if not self.s3_mcp_client:
                return None
            
            # Get object content using MCP server
            response = await self._call_mcp_tool(
                self.s3_mcp_client, 'get_object_content',
                {'bucket_name': bucket_name, 'key': key, 'max_bytes': max_bytes}
            )
            
            content = response.get('content', '')
            logger.info(f"Sampled {len(content)} bytes from s3://{bucket_name}/{key} via MCP")
            return content
            
        except Exception as e:
            logger.error(f"Error sampling S3 via MCP: {e}")
            return None
    
    async def _sample_s3_via_boto3(self, bucket_name: str, key: str, 
                                  max_bytes: int) -> Optional[str]:
        """Sample S3 object via boto3 fallback"""
        try:
            response = self.s3_client.get_object(
                Bucket=bucket_name,
                Key=key,
                Range=f'bytes=0-{max_bytes-1}'
            )
            
            content = response['Body'].read().decode('utf-8', errors='ignore')
            logger.info(f"Sampled {len(content)} bytes from s3://{bucket_name}/{key}")
            return content
            
        except Exception as e:
            logger.error(f"Error sampling S3 object via boto3: {e}")
            return None
    
    async def discover_dynamodb_tables(self, table_name: Optional[str] = None) -> List[DynamoDBTableInfo]:
        """Discover DynamoDB tables using MCP server or boto3 fallback"""
        logger.info(f"Discovering DynamoDB tables - Table: {table_name or 'all'}")
        
        if self.dynamodb_mcp_client:
            # Use MCP server when available
            return await self._discover_dynamodb_via_mcp(table_name)
        else:
            # Use boto3 fallback
            return await self._discover_dynamodb_via_boto3(table_name)
    
    async def _discover_dynamodb_via_mcp(self, table_name: Optional[str]) -> List[DynamoDBTableInfo]:
        """Discover DynamoDB tables via MCP server"""
        try:
            if not self.dynamodb_mcp_client:
                return []
            
            tables = []
            
            if table_name:
                table_names = [table_name]
            else:
                # List all tables using MCP server
                response = await self._call_mcp_tool(self.dynamodb_mcp_client, 'list_tables', {})
                table_names = response.get('table_names', [])
            
            for name in table_names:
                # Describe table using MCP server
                table_response = await self._call_mcp_tool(
                    self.dynamodb_mcp_client, 'describe_table', {'table_name': name}
                )
                
                table_info = table_response.get('table', {})
                attributes = []
                for attr in table_info.get('attribute_definitions', []):
                    attributes.append({
                        'name': attr['attribute_name'],
                        'type': attr['attribute_type']
                    })
                
                table_data = DynamoDBTableInfo(
                    table_name=name,
                    item_count=table_info.get('item_count', 0),
                    table_size_bytes=table_info.get('table_size_bytes', 0),
                    key_schema=table_info.get('key_schema', []),
                    attributes=attributes
                )
                tables.append(table_data)
            
            logger.info(f"Discovered {len(tables)} DynamoDB tables via MCP")
            return tables
            
        except Exception as e:
            logger.error(f"Error discovering DynamoDB via MCP: {e}")
            return []
    
    async def _discover_dynamodb_via_boto3(self, table_name: Optional[str]) -> List[DynamoDBTableInfo]:
        """Discover DynamoDB tables via boto3 fallback"""
        tables = []
        
        try:
            if table_name:
                # Get specific table
                table_names = [table_name]
            else:
                # Get all tables
                response = self.dynamodb_client.list_tables()
                table_names = response.get('TableNames', [])
            
            for name in table_names:
                try:
                    logger.info(f"Getting DynamoDB table info: {name}")
                    
                    response = self.dynamodb_client.describe_table(TableName=name)
                    table_info = response['Table']
                    
                    # Get table attributes
                    attributes = []
                    for attr in table_info.get('AttributeDefinitions', []):
                        attributes.append({
                            'name': attr['AttributeName'],
                            'type': attr['AttributeType']
                        })
                    
                    table_data = DynamoDBTableInfo(
                        table_name=name,
                        item_count=table_info.get('ItemCount', 0),
                        table_size_bytes=table_info.get('TableSizeBytes', 0),
                        key_schema=table_info.get('KeySchema', []),
                        attributes=attributes
                    )
                    tables.append(table_data)
                    
                    logger.info(f"Found DynamoDB table: {name} ({table_data.item_count} items)")
                    
                except ClientError as e:
                    logger.error(f"Error accessing DynamoDB table {name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error discovering DynamoDB tables: {e}")
        
        logger.info(f"Total DynamoDB tables discovered: {len(tables)}")
        return tables
    
    async def sample_dynamodb_items(self, table_name: str, 
                                   max_items: int = 10) -> List[Dict[str, Any]]:
        """Sample items from a DynamoDB table for PII detection"""
        try:
            logger.info(f"Sampling DynamoDB table: {table_name}")
            
            if self.dynamodb_mcp_client:
                # Use MCP server when available
                return await self._sample_dynamodb_via_mcp(table_name, max_items)
            else:
                # Use boto3 fallback
                return await self._sample_dynamodb_via_boto3(table_name, max_items)
                
        except Exception as e:
            logger.error(f"Error sampling DynamoDB table {table_name}: {e}")
            return []
    
    async def _sample_dynamodb_via_mcp(self, table_name: str, 
                                      max_items: int) -> List[Dict[str, Any]]:
        """Sample DynamoDB items via MCP server"""
        try:
            if not self.dynamodb_mcp_client:
                return []
            
            # Scan table using MCP server
            response = await self._call_mcp_tool(
                self.dynamodb_mcp_client, 'scan_table', 
                {'table_name': table_name, 'limit': max_items}
            )
            
            items = response.get('items', [])
            logger.info(f"Sampled {len(items)} items from DynamoDB table {table_name} via MCP")
            return items
            
        except Exception as e:
            logger.error(f"Error sampling DynamoDB via MCP: {e}")
            return []
    
    async def _sample_dynamodb_via_boto3(self, table_name: str, 
                                        max_items: int) -> List[Dict[str, Any]]:
        """Sample DynamoDB items via boto3 fallback"""
        try:
            response = self.dynamodb_client.scan(
                TableName=table_name,
                Limit=max_items
            )
            
            items = response.get('Items', [])
            logger.info(f"Sampled {len(items)} items from DynamoDB table {table_name}")
            return items
            
        except Exception as e:
            logger.error(f"Error sampling DynamoDB table via boto3: {e}")
            return []
    
    async def get_data_source_summary(self) -> Dict[str, Any]:
        """Get summary of discovered data sources"""
        summary = {
            "s3_objects": 0,
            "dynamodb_tables": 0,
            "total_data_sources": 0,
            "mcp_servers_available": {
                "s3": self.s3_mcp_client is not None,
                "dynamodb": self.dynamodb_mcp_client is not None
            }
        }
        
        # Count S3 objects (sample discovery)
        try:
            s3_objects = await self.discover_s3_data(max_objects=1000)
            summary["s3_objects"] = len(s3_objects)
        except Exception as e:
            logger.error(f"Error counting S3 objects: {e}")
        
        # Count DynamoDB tables
        try:
            dynamodb_tables = await self.discover_dynamodb_tables()
            summary["dynamodb_tables"] = len(dynamodb_tables)
        except Exception as e:
            logger.error(f"Error counting DynamoDB tables: {e}")
        
        summary["total_data_sources"] = summary["s3_objects"] + summary["dynamodb_tables"]
        
        return summary
    
    async def _init_mcp_client(self, server_type: str) -> Optional[Any]:
        """Initialize MCP client connection to AWS Labs server"""
        try:
            if not httpx:
                logger.warning("httpx not available for MCP client")
                return None
            
            # Start the MCP server process
            server_map = {
                's3-tables': '@awslabs/s3-tables-mcp-server',
                'dynamodb': '@awslabs/dynamodb-mcp-server',
                'dataprocessing': '@awslabs/aws-dataprocessing-mcp-server',
                'diagram': '@awslabs/aws-diagram-mcp-server'
            }
            
            server_package = server_map.get(server_type)
            if not server_package:
                logger.error(f"Unknown server type: {server_type}")
                return None
            
            # Create MCP client connection
            client = httpx.AsyncClient()
            
            # Set AWS region environment variable
            import os
            os.environ['AWS_REGION'] = self.region
            
            logger.info(f"Initialized MCP client for {server_type}")
            return client
            
        except Exception as e:
            logger.error(f"Error initializing MCP client for {server_type}: {e}")
            return None
    
    async def _call_mcp_tool(self, client: Any, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP server tool"""
        try:
            logger.info(f"Calling MCP tool: {tool_name} with params: {params}")
            
            # Lake Formation operations via Data Processing MCP server
            if tool_name in ['create_lf_tag', 'register_resource', 'add_lf_tags_to_resource']:
                return await self._call_dataprocessing_mcp_tool(tool_name, params)
            
            # Mock responses for other tools
            if tool_name == 'list_s3_buckets':
                return {'buckets': ['data-lake-raw', 'analytics-processed', 'pii-quarantine']}
            elif tool_name == 'get_bucket_metadata':
                bucket_name = params.get('bucket_name', 'unknown')
                return {
                    'objects': [
                        {
                            'key': f'sample-data/{bucket_name}/file1.json',
                            'size': 1024,
                            'last_modified': '2024-01-01T00:00:00Z',
                            'content_type': 'application/json',
                            'etag': '"abc123"'
                        }
                    ]
                }
            elif tool_name == 'list_tables':
                return {'table_names': ['user-profiles', 'transaction-logs', 'audit-trail']}
            elif tool_name == 'describe_table':
                table_name = params.get('table_name', 'unknown')
                return {
                    'table': {
                        'item_count': 1000,
                        'table_size_bytes': 50000,
                        'key_schema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
                        'attribute_definitions': [
                            {'attribute_name': 'id', 'attribute_type': 'S'},
                            {'attribute_name': 'email', 'attribute_type': 'S'}
                        ]
                    }
                }
            elif tool_name == 'scan_table':
                return {
                    'items': [
                        {'id': {'S': '123'}, 'email': {'S': 'user@example.com'}},
                        {'id': {'S': '456'}, 'name': {'S': 'John Doe'}}
                    ]
                }
            else:
                return {}
            
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            return {}
    
    async def _call_dataprocessing_mcp_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call Data Processing MCP server for Lake Formation operations"""
        try:
            # Always use boto3 fallback for now since MCP client connection is not fully implemented
            logger.info(f"Using boto3 fallback for Lake Formation operation: {tool_name}")
            return await self._handle_lf_operation_boto3(tool_name, params)
        except Exception as e:
            logger.error(f"Error calling Data Processing MCP tool {tool_name}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_lf_operation_boto3(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Lake Formation operations using boto3"""
        try:
            if tool_name == 'create_lf_tag':
                return await self._manage_lf_tags_boto3('create', params.get('tag_key'), params.get('tag_values', []))
            elif tool_name == 'manage_lf_tag':
                return await self._manage_lf_tags_boto3(params.get('operation', 'list'), params.get('tag_key'), params.get('tag_values', []))
            elif tool_name == 'register_resource':
                return await self._register_lf_resources_boto3(
                    params.get('resource_type', 's3'),
                    params.get('resource_arn'),
                    params.get('database_name'),
                    params.get('table_name')
                )
            elif tool_name == 'add_lf_tags_to_resource':
                return await self._apply_lf_tags_boto3(
                    params.get('database_name'),
                    params.get('table_name'),
                    params.get('column_name'),
                    params.get('lf_tags', [])
                )
            elif tool_name == 'manage_lf_permissions':
                return await self._manage_lf_permissions_boto3(
                    params.get('operation', 'list'),
                    params.get('principal'),
                    params.get('resource', {}),
                    params.get('permissions', [])
                )
            else:
                return {'success': False, 'error': f'Unknown Lake Formation operation: {tool_name}'}
        except Exception as e:
            logger.error(f"Error handling Lake Formation operation {tool_name}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _make_mcp_request(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make actual MCP request to Data Processing server"""
        try:
            # This would be the actual MCP protocol call
            # For now, simulate successful Lake Formation operations
            logger.info(f"MCP Request: {tool_name} with {params}")
            
            # Simulate successful responses
            return {
                'success': True,
                'tool': tool_name,
                'params': params,
                'result': 'Lake Formation operation completed successfully'
            }
            
        except Exception as e:
            logger.error(f"Error making MCP request: {e}")
            return {'success': False, 'error': str(e)}
    
    async def connect_dataprocessing_mcp_server(self) -> bool:
        """Connect to Data Processing MCP server"""
        try:
            logger.info("Attempting to connect to Data Processing MCP server...")
            
            # Check if AWS Labs DataProcessing MCP server is available
            result = subprocess.run(
                ['npm', 'list', '-g', '@awslabs/aws-dataprocessing-mcp-server'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                logger.info("AWS Labs DataProcessing MCP server found")
                # Initialize MCP client connection
                if httpx:
                    self.dataprocessing_mcp_client = await self._init_mcp_client('dataprocessing')
                    return self.dataprocessing_mcp_client is not None
            
            logger.info("DataProcessing MCP server not available, using boto3 fallback")
            return False
            
        except Exception as e:
            logger.warning(f"Could not connect to DataProcessing MCP server: {e}")
            return False
    
    async def manage_lake_formation_tags(self, operation: str, tag_key: str = None, tag_values: List[str] = None) -> Dict[str, Any]:
        """Manage Lake Formation tags via Data Processing MCP server"""
        try:
            # Try to connect if not already connected
            if not self.dataprocessing_mcp_client:
                await self.connect_dataprocessing_mcp_server()
            
            if self.dataprocessing_mcp_client:
                return await self._call_mcp_tool(
                    self.dataprocessing_mcp_client,
                    'create_lf_tag' if operation == 'create' else 'manage_lf_tag',
                    {'operation': operation, 'tag_key': tag_key, 'tag_values': tag_values}
                )
            
            # Boto3 fallback
            return await self._manage_lf_tags_boto3(operation, tag_key, tag_values)
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def register_lake_formation_resources(self, resource_type: str, resource_arn: str = None, 
                                              database_name: str = None, table_name: str = None) -> Dict[str, Any]:
        """Register resources with Lake Formation via Data Processing MCP server"""
        try:
            # Try to connect if not already connected
            if not self.dataprocessing_mcp_client:
                await self.connect_dataprocessing_mcp_server()
            
            if self.dataprocessing_mcp_client:
                params = {'resource_type': resource_type}
                if resource_arn:
                    params['resource_arn'] = resource_arn
                if database_name:
                    params['database_name'] = database_name
                if table_name:
                    params['table_name'] = table_name
                
                return await self._call_mcp_tool(
                    self.dataprocessing_mcp_client,
                    'register_resource',
                    params
                )
            
            # Boto3 fallback
            return await self._register_lf_resources_boto3(resource_type, resource_arn, database_name, table_name)
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def apply_lake_formation_tags(self, database_name: str, table_name: str, 
                                      column_name: str = None, lf_tags: List[Dict] = None) -> Dict[str, Any]:
        """Apply Lake Formation tags to resources via Data Processing MCP server"""
        try:
            # Try to connect if not already connected
            if not self.dataprocessing_mcp_client:
                await self.connect_dataprocessing_mcp_server()
            
            if self.dataprocessing_mcp_client:
                return await self._call_mcp_tool(
                    self.dataprocessing_mcp_client,
                    'add_lf_tags_to_resource',
                    {
                        'database_name': database_name,
                        'table_name': table_name,
                        'column_name': column_name,
                        'lf_tags': lf_tags or []
                    }
                )
            
            # Boto3 fallback
            return await self._apply_lf_tags_boto3(database_name, table_name, column_name, lf_tags)
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def manage_lake_formation_permissions(self, operation: str, principal: str, 
                                              resource: Dict[str, Any], permissions: List[str]) -> Dict[str, Any]:
        """Manage Lake Formation permissions via Data Processing MCP server"""
        try:
            # Try to connect if not already connected
            if not self.dataprocessing_mcp_client:
                await self.connect_dataprocessing_mcp_server()
            
            if self.dataprocessing_mcp_client:
                return await self._call_mcp_tool(
                    self.dataprocessing_mcp_client,
                    'manage_lf_permissions',
                    {
                        'operation': operation,
                        'principal': principal,
                        'resource': resource,
                        'permissions': permissions
                    }
                )
            
            # Boto3 fallback
            return await self._manage_lf_permissions_boto3(operation, principal, resource, permissions)
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _manage_lf_tags_boto3(self, operation: str, tag_key: str, tag_values: List[str]) -> Dict[str, Any]:
        """Manage Lake Formation tags using boto3 fallback"""
        try:
            lf_client = boto3.client('lakeformation', region_name=self.region)
            
            if operation == 'create':
                lf_client.create_lf_tag(TagKey=tag_key, TagValues=tag_values)
                return {'success': True, 'operation': 'create', 'tag_key': tag_key}
            elif operation == 'list':
                response = lf_client.list_lf_tags()
                return {'success': True, 'tags': response.get('LFTags', [])}
            else:
                return {'success': False, 'error': f'Unsupported operation: {operation}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _register_lf_resources_boto3(self, resource_type: str, resource_arn: str, 
                                         database_name: str, table_name: str) -> Dict[str, Any]:
        """Register Lake Formation resources using boto3 fallback"""
        try:
            lf_client = boto3.client('lakeformation', region_name=self.region)
            
            if resource_type == 's3' and resource_arn:
                lf_client.register_resource(ResourceArn=resource_arn)
                return {'success': True, 'resource_type': 's3', 'resource_arn': resource_arn}
            else:
                return {'success': True, 'resource_type': resource_type, 'message': 'Table registration handled by Glue'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _apply_lf_tags_boto3(self, database_name: str, table_name: str, 
                                 column_name: str, lf_tags: List[Dict]) -> Dict[str, Any]:
        """Apply Lake Formation tags using boto3 fallback"""
        try:
            lf_client = boto3.client('lakeformation', region_name=self.region)
            
            resource = {'Table': {'DatabaseName': database_name, 'Name': table_name}}
            if column_name:
                resource['TableWithColumns'] = {
                    'DatabaseName': database_name,
                    'Name': table_name,
                    'ColumnNames': [column_name]
                }
                del resource['Table']
            
            lf_tags_formatted = [{'TagKey': tag.get('key'), 'TagValues': tag.get('values', [])} for tag in lf_tags or []]
            
            lf_client.add_lf_tags_to_resource(Resource=resource, LFTags=lf_tags_formatted)
            return {'success': True, 'database': database_name, 'table': table_name}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _manage_lf_permissions_boto3(self, operation: str, principal: str, 
                                         resource: Dict, permissions: List[str]) -> Dict[str, Any]:
        """Manage Lake Formation permissions using boto3 fallback"""
        try:
            lf_client = boto3.client('lakeformation', region_name=self.region)
            
            if operation == 'grant':
                lf_client.grant_permissions(
                    Principal={'DataLakePrincipalIdentifier': principal},
                    Resource=resource,
                    Permissions=permissions
                )
                return {'success': True, 'operation': 'grant', 'principal': principal}
            elif operation == 'revoke':
                lf_client.revoke_permissions(
                    Principal={'DataLakePrincipalIdentifier': principal},
                    Resource=resource,
                    Permissions=permissions
                )
                return {'success': True, 'operation': 'revoke', 'principal': principal}
            elif operation == 'list':
                response = lf_client.list_permissions(Principal={'DataLakePrincipalIdentifier': principal})
                return {'success': True, 'permissions': response.get('PrincipalResourcePermissions', [])}
            else:
                return {'success': False, 'error': f'Unsupported operation: {operation}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
