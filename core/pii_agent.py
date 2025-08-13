#!/usr/bin/env python3
"""
AWS PII Detection Agent - Main Module
Clean, production-ready PII detection and Lake Formation tagging
"""

import asyncio
import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime
from enum import Enum
import boto3
from botocore.exceptions import ClientError, BotoCoreError

# Import AWS MCP client
try:
    from .aws_mcp_client import AWSMCPClient, S3ObjectInfo, DynamoDBTableInfo
except ImportError:
    from aws_mcp_client import AWSMCPClient, S3ObjectInfo, DynamoDBTableInfo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PIIDetectionResult:
    """Result of PII detection for a column"""
    database_name: str
    table_name: str
    column_name: str
    column_type: str
    pii_types: List[str] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    applied_lf_tags: Dict[str, str] = field(default_factory=dict)
    tagging_status: str = "pending"
    data_classification: str = "NO_RISK"

@dataclass
class PIIDetectionConfig:
    """Configuration for PII detection"""
    aws_region: str = "us-west-2"
    glue_databases: List[str] = field(default_factory=list)
    comprehend_enabled: bool = True
    confidence_threshold: float = 0.8
    dry_run: bool = False
    apply_lf_tags: bool = True
    tag_all_columns: bool = True
    # S3 and DynamoDB configuration
    enable_s3_discovery: bool = True
    enable_dynamodb_discovery: bool = True
    s3_buckets: List[str] = field(default_factory=list)
    s3_prefix: str = ""
    s3_max_objects: int = 100
    dynamodb_tables: List[str] = field(default_factory=list)
    dynamodb_max_items: int = 10
    # MCP server configuration
    use_mcp_servers: bool = True

class AWSPIIDetectionAgent:
    """Main PII detection agent with comprehensive data classification"""
    
    # Column name patterns for PII detection
    COLUMN_NAME_PATTERNS = {
        "email": ["email", "mail", "e_mail", "email_address"],
        "ssn": ["ssn", "social_security", "social_security_number", "tax_id"],
        "phone": ["phone", "telephone", "mobile", "cell", "phone_number", "phone-no"],
        "name": ["first_name", "last_name", "full_name", "name", "fname", "lname", "first name", "last name"],
        "address": ["address", "street", "city", "state", "zip", "postal_code"],
        "credit_card": ["cc_num", "credit_card", "card_number", "payment_card"],
        "date_of_birth": ["dob", "birth_date", "date_of_birth", "birthday"],
        "salary": ["salary", "wage", "income", "compensation", "pay", "earnings"],
        "age": ["age", "birth_year", "years_old"]
    }
    
    # Lake Formation tag definitions
    LF_TAG_DEFINITIONS = {
        "PIIType": ["EMAIL", "SSN", "PHONE", "NAME", "ADDRESS", "CREDIT_CARD", "DATE_OF_BIRTH", "SALARY", "AGE", "NONE"],
        "PIIClassification": ["SENSITIVE", "HIGHLY_SENSITIVE", "CONFIDENTIAL"],
        "DataGovernance": ["PII_DETECTED", "REQUIRES_MASKING", "ACCESS_RESTRICTED", "PUBLIC"],
        "DataClassification": ["NO_RISK", "LOW_RISK", "MEDIUM_RISK", "HIGH_RISK", "CRITICAL_RISK"],
        "AccessLevel": ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED", "TOP_SECRET"]
    }
    
    def __init__(self, config: PIIDetectionConfig):
        self.config = config
        self.session = boto3.Session()
        
        # Initialize AWS clients
        self.glue_client = self.session.client('glue', region_name=config.aws_region)
        self.lakeformation_client = self.session.client('lakeformation', region_name=config.aws_region)
        
        if config.comprehend_enabled:
            try:
                self.comprehend_client = self.session.client('comprehend', region_name=config.aws_region)
                logger.info(f"Comprehend client initialized for {config.aws_region}")
            except Exception as e:
                logger.warning(f"Could not initialize Comprehend client: {e}")
                self.comprehend_client = None
        
        # Initialize AWS MCP client
        self.mcp_client = AWSMCPClient(region=config.aws_region)
        
        # Initialize data processing MCP client for Lake Formation
        self.dataprocessing_mcp_client = None
        
        # Connect to MCP servers if enabled
        if config.use_mcp_servers:
            asyncio.create_task(self._connect_mcp_servers())
        
        logger.info(f"Initialized AWS PII Detection Agent for region: {config.aws_region}")
    
    async def _connect_mcp_servers(self):
        """Connect to AWS MCP servers"""
        try:
            logger.info("Connecting to AWS Labs MCP servers...")
            s3_connected = await self.mcp_client.connect_s3_mcp_server()
            dynamodb_connected = await self.mcp_client.connect_dynamodb_mcp_server()
            dataprocessing_connected = await self._connect_dataprocessing_mcp_server()
            
            if s3_connected:
                logger.info("✅ Connected to S3 MCP server")
            else:
                logger.info("⚠️ S3 MCP server not available, using boto3 fallback")
            
            if dynamodb_connected:
                logger.info("✅ Connected to DynamoDB MCP server")
            else:
                logger.info("⚠️ DynamoDB MCP server not available, using boto3 fallback")
            
            if dataprocessing_connected:
                logger.info("✅ Connected to Data Processing MCP server for Lake Formation")
            else:
                logger.info("⚠️ Data Processing MCP server not available, using boto3 fallback for Lake Formation")
                
        except Exception as e:
            logger.warning(f"Error connecting to MCP servers: {e}")
    
    def detect_pii_by_column_name(self, column_name: str) -> Tuple[List[str], Dict[str, float]]:
        """Detect PII based on column name patterns"""
        pii_types = []
        confidence_scores = {}
        
        column_lower = column_name.lower().strip()
        
        for pii_type, patterns in self.COLUMN_NAME_PATTERNS.items():
            for pattern in patterns:
                if pattern in column_lower:
                    pii_types.append(pii_type.upper())
                    confidence_scores[pii_type.upper()] = 0.8
                    break
        
        return pii_types, confidence_scores
    
    def get_data_classification(self, pii_types: List[str]) -> str:
        """Determine comprehensive data classification based on PII types"""
        if not pii_types:
            return "NO_RISK"
        
        critical_risk = {"SSN", "CREDIT_CARD"}
        high_risk = {"DATE_OF_BIRTH", "SALARY"}
        medium_risk = {"EMAIL", "PHONE", "NAME"}
        low_risk = {"ADDRESS", "AGE"}
        
        if any(pii_type in critical_risk for pii_type in pii_types):
            return "CRITICAL_RISK"
        elif any(pii_type in high_risk for pii_type in pii_types):
            return "HIGH_RISK"
        elif any(pii_type in medium_risk for pii_type in pii_types):
            return "MEDIUM_RISK"
        elif any(pii_type in low_risk for pii_type in pii_types):
            return "LOW_RISK"
        else:
            return "NO_RISK"
    
    def get_access_level(self, data_classification: str) -> str:
        """Determine access level based on data classification"""
        access_mapping = {
            "NO_RISK": "PUBLIC",
            "LOW_RISK": "INTERNAL", 
            "MEDIUM_RISK": "CONFIDENTIAL",
            "HIGH_RISK": "RESTRICTED",
            "CRITICAL_RISK": "TOP_SECRET"
        }
        return access_mapping.get(data_classification, "INTERNAL")
    
    async def scan_glue_catalog(self) -> List[Dict[str, Any]]:
        """Scan AWS Glue Data Catalog for tables"""
        logger.info(f"Starting Glue Data Catalog scan in {self.config.aws_region}...")
        
        all_tables = []
        
        try:
            # Get databases to scan
            if self.config.glue_databases:
                databases_to_scan = self.config.glue_databases
            else:
                response = self.glue_client.get_databases()
                databases_to_scan = [db['Name'] for db in response.get('DatabaseList', [])]
            
            logger.info(f"Scanning {len(databases_to_scan)} databases: {databases_to_scan}")
            
            for db_name in databases_to_scan:
                try:
                    paginator = self.glue_client.get_paginator('get_tables')
                    page_iterator = paginator.paginate(DatabaseName=db_name)
                    
                    for page in page_iterator:
                        for table in page.get('TableList', []):
                            table_info = {
                                'DatabaseName': db_name,
                                'TableName': table['Name'],
                                'Location': table.get('StorageDescriptor', {}).get('Location', ''),
                                'Columns': table.get('StorageDescriptor', {}).get('Columns', [])
                            }
                            all_tables.append(table_info)
                            
                    logger.info(f"Found {len([t for t in all_tables if t['DatabaseName'] == db_name])} tables in {db_name}")
                    
                except ClientError as e:
                    logger.error(f"Error accessing database {db_name}: {e}")
                    
        except ClientError as e:
            logger.error(f"Error accessing Glue catalog: {e}")
            raise
            
        logger.info(f"Total tables found: {len(all_tables)}")
        return all_tables
    
    async def scan_s3_data(self) -> List[Dict[str, Any]]:
        """Scan S3 objects for PII using AWS Labs MCP server or boto3 fallback"""
        logger.info(f"Starting S3 data scan in {self.config.aws_region}...")
        
        if not self.config.enable_s3_discovery:
            logger.info("S3 discovery disabled in configuration")
            return []
        
        try:
            # MCP server connection is handled in initialization
            logger.info("Using AWS Labs S3 MCP server (with boto3 fallback)")
            
            # Discover S3 objects
            s3_objects = await self.mcp_client.discover_s3_data(
                bucket_name=None if not self.config.s3_buckets else self.config.s3_buckets[0],
                prefix=self.config.s3_prefix,
                max_objects=self.config.s3_max_objects
            )
            
            s3_results = []
            for obj in s3_objects:
                # Sample content for PII detection
                content = await self.mcp_client.sample_s3_object_content(
                    obj.bucket_name, 
                    obj.key, 
                    max_bytes=1024
                )
                
                if content:
                    # Detect PII in content
                    pii_types, confidence_scores = self.detect_pii_in_content(content)
                    
                    if pii_types:
                        result = {
                            'source_type': 's3',
                            'bucket_name': obj.bucket_name,
                            'key': obj.key,
                            'size': obj.size,
                            'content_type': obj.content_type,
                            'pii_types': pii_types,
                            'confidence_scores': confidence_scores,
                            'data_classification': self.get_data_classification(pii_types)
                        }
                        s3_results.append(result)
                        logger.info(f"  🚨 PII found in s3://{obj.bucket_name}/{obj.key}: {', '.join(pii_types)}")
                    else:
                        logger.info(f"  ✅ No PII found in s3://{obj.bucket_name}/{obj.key}")
            
            logger.info(f"S3 scan completed: {len(s3_results)} objects with PII found")
            return s3_results
            
        except Exception as e:
            logger.error(f"Error scanning S3 data: {e}")
            return []
    
    async def scan_dynamodb_data(self) -> List[Dict[str, Any]]:
        """Scan DynamoDB tables for PII using AWS Labs MCP server or boto3 fallback"""
        logger.info(f"Starting DynamoDB data scan in {self.config.aws_region}...")
        
        if not self.config.enable_dynamodb_discovery:
            logger.info("DynamoDB discovery disabled in configuration")
            return []
        
        try:
            # MCP server connection is handled in initialization
            logger.info("Using AWS Labs DynamoDB MCP server (with boto3 fallback)")
            
            # Discover DynamoDB tables
            dynamodb_tables = await self.mcp_client.discover_dynamodb_tables(
                table_name=None if not self.config.dynamodb_tables else self.config.dynamodb_tables[0]
            )
            
            dynamodb_results = []
            for table in dynamodb_tables:
                # Sample items for PII detection
                items = await self.mcp_client.sample_dynamodb_items(
                    table.table_name,
                    max_items=self.config.dynamodb_max_items
                )
                
                table_pii_found = []
                for item in items:
                    # Convert DynamoDB item to string for PII detection
                    item_str = json.dumps(item, default=str)
                    pii_types, confidence_scores = self.detect_pii_in_content(item_str)
                    
                    if pii_types:
                        table_pii_found.extend(pii_types)
                
                if table_pii_found:
                    # Remove duplicates
                    unique_pii_types = list(set(table_pii_found))
                    result = {
                        'source_type': 'dynamodb',
                        'table_name': table.table_name,
                        'item_count': table.item_count,
                        'table_size_bytes': table.table_size_bytes,
                        'pii_types': unique_pii_types,
                        'confidence_scores': {pii: 0.8 for pii in unique_pii_types},
                        'data_classification': self.get_data_classification(unique_pii_types)
                    }
                    dynamodb_results.append(result)
                    logger.info(f"  🚨 PII found in DynamoDB table {table.table_name}: {', '.join(unique_pii_types)}")
                else:
                    logger.info(f"  ✅ No PII found in DynamoDB table {table.table_name}")
            
            logger.info(f"DynamoDB scan completed: {len(dynamodb_results)} tables with PII found")
            return dynamodb_results
            
        except Exception as e:
            logger.error(f"Error scanning DynamoDB data: {e}")
            return []
    
    def detect_pii_in_content(self, content: str) -> Tuple[List[str], Dict[str, float]]:
        """Detect PII in text content using pattern matching and Comprehend"""
        pii_types = []
        confidence_scores = {}
        
        if not content:
            return pii_types, confidence_scores
        
        # Pattern-based detection
        patterns = {
            "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "SSN": r'\b\d{3}-\d{2}-\d{4}\b',
            "PHONE": r'\b(?:\(\d{3}\)\s?|\d{3}[-.]?)\d{3}[-.]?\d{4}\b',
            "CREDIT_CARD": r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            "DATE_OF_BIRTH": r'\b(0[1-9]|1[0-2])[/-](0[1-9]|[12]\d|3[01])[/-]\d{4}\b'
        }
        
        for pii_type, pattern in patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                pii_types.append(pii_type)
                confidence_scores[pii_type] = 0.7  # Pattern-based confidence
        
        # AWS Comprehend detection if enabled
        if self.config.comprehend_enabled and self.comprehend_client:
            try:
                # Sample content for Comprehend (limit to 5000 bytes)
                sample_content = content[:5000]
                
                response = self.comprehend_client.detect_pii_entities(
                    Text=sample_content,
                    LanguageCode='en'
                )
                
                for entity in response.get('Entities', []):
                    comprehend_type = entity['Type']
                    confidence = entity['Score']
                    
                    # Map Comprehend types to our types
                    type_mapping = {
                        'EMAIL': 'EMAIL',
                        'SSN': 'SSN',
                        'PHONE': 'PHONE',
                        'CREDIT_DEBIT_NUMBER': 'CREDIT_CARD',
                        'DATE_TIME': 'DATE_OF_BIRTH'
                    }
                    
                    if comprehend_type in type_mapping:
                        mapped_type = type_mapping[comprehend_type]
                        if mapped_type not in pii_types:
                            pii_types.append(mapped_type)
                        confidence_scores[mapped_type] = max(
                            confidence_scores.get(mapped_type, 0),
                            confidence
                        )
                        
            except Exception as e:
                logger.warning(f"Error using Comprehend for PII detection: {e}")
        
        return pii_types, confidence_scores
    
    async def analyze_table(self, database: str, table: str) -> Dict[str, Any]:
        """Analyze a specific table for PII content"""
        try:
            response = self.glue_client.get_table(DatabaseName=database, Name=table)
            table_info = response['Table']
            
            columns = table_info.get('StorageDescriptor', {}).get('Columns', [])
            column_results = []
            
            for column in columns:
                pii_types, confidence_scores = self.detect_pii_by_column_name(column['Name'])
                is_pii = len(pii_types) > 0
                
                column_results.append({
                    'name': column['Name'],
                    'type': column['Type'],
                    'is_pii': is_pii,
                    'pii_type': pii_types[0] if pii_types else 'N/A',
                    'confidence': max(confidence_scores.values()) if confidence_scores else 0.0
                })
            
            return {
                'database': database,
                'table': table,
                'columns': column_results
            }
            
        except Exception as e:
            logger.error(f"Error analyzing table {database}.{table}: {e}")
            return {'database': database, 'table': table, 'columns': [], 'error': str(e)}
    
    async def _connect_dataprocessing_mcp_server(self) -> bool:
        """Connect to Data Processing MCP server for Lake Formation operations"""
        try:
            logger.info("Attempting to connect to Data Processing MCP server...")
            
            # Check if AWS Labs Data Processing MCP server is available
            result = subprocess.run(
                ['uvx', 'awslabs.aws-dataprocessing-mcp-server@latest', '--help'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                logger.info("AWS Labs Data Processing MCP server found")
                # Initialize MCP client connection
                if httpx:
                    self.dataprocessing_mcp_client = await self._init_mcp_client('dataprocessing')
                    return self.dataprocessing_mcp_client is not None
            
            logger.info("Data Processing MCP server not available, using boto3 fallback")
            return False
            
        except Exception as e:
            logger.warning(f"Could not connect to Data Processing MCP server: {e}")
            return False
    
    async def create_lake_formation_tags(self) -> Dict[str, List[str]]:
        """Create Lake Formation tags for data governance"""
        if self.config.dry_run:
            logger.info("DRY RUN: Would create Lake Formation tags")
            return self.LF_TAG_DEFINITIONS
        
        try:
            created_tags = {}
            
            # Try MCP client first
            if self.dataprocessing_mcp_client:
                for tag_key, tag_values in self.LF_TAG_DEFINITIONS.items():
                    response = await self.mcp_client._call_mcp_tool(
                        self.dataprocessing_mcp_client,
                        'create_lf_tag',
                        {'tag_key': tag_key, 'tag_values': tag_values}
                    )
                    if response.get('success'):
                        created_tags[tag_key] = tag_values
                        logger.info(f"Created Lake Formation tag via MCP: {tag_key}")
                return created_tags
            
            # Fallback to boto3
            for tag_key, tag_values in self.LF_TAG_DEFINITIONS.items():
                try:
                    self.lakeformation_client.create_lf_tag(
                        TagKey=tag_key,
                        TagValues=tag_values
                    )
                    created_tags[tag_key] = tag_values
                    logger.info(f"Created Lake Formation tag: {tag_key}")
                except Exception as e:
                    if "AlreadyExistsException" in str(e):
                        created_tags[tag_key] = tag_values
                        logger.info(f"Lake Formation tag already exists: {tag_key}")
                    else:
                        logger.error(f"Error creating tag {tag_key}: {e}")
            
            return created_tags
            
        except Exception as e:
            logger.error(f"Error creating Lake Formation tags: {e}")
            return {}
    
    async def register_s3_location_with_lakeformation(self, s3_path: str) -> bool:
        """Register S3 location with Lake Formation"""
        if self.config.dry_run:
            logger.info(f"DRY RUN: Would register S3 location {s3_path} with Lake Formation")
            return True
        
        try:
            # Try MCP client first
            if self.dataprocessing_mcp_client:
                response = await self.mcp_client._call_mcp_tool(
                    self.dataprocessing_mcp_client,
                    'register_resource',
                    {'resource_arn': s3_path, 'bucket_name': s3_path.split('/')[2] if s3_path.startswith('s3://') else None}
                )
                if response.get('success'):
                    logger.info(f"Successfully registered S3 location {s3_path} via MCP")
                    return True
            
            # Fallback to boto3
            self.lakeformation_client.register_resource(
                ResourceArn=s3_path,
                UseServiceLinkedRole=True
            )
            logger.info(f"Successfully registered S3 location {s3_path} with Lake Formation")
            return True
        except Exception as e:
            if "AlreadyExistsException" in str(e):
                logger.info(f"S3 location {s3_path} already registered with Lake Formation")
                return True
            logger.error(f"Error registering S3 location {s3_path}: {e}")
            return False
    
    async def register_table_with_lakeformation(self, database_name: str, table_name: str) -> bool:
        """Register Glue table with Lake Formation"""
        if self.config.dry_run:
            logger.info(f"DRY RUN: Would register table {database_name}.{table_name} with Lake Formation")
            return True
        
        try:
            # Try MCP client first
            if self.dataprocessing_mcp_client:
                response = await self.mcp_client._call_mcp_tool(
                    self.dataprocessing_mcp_client,
                    'register_resource',
                    {'database_name': database_name, 'table_name': table_name}
                )
                if response.get('success'):
                    logger.info(f"Successfully registered table {database_name}.{table_name} via MCP")
                    return True
            
            # Fallback to boto3
            sts_client = self.session.client('sts')
            account_id = sts_client.get_caller_identity()['Account']
            table_arn = f"arn:aws:glue:{self.config.aws_region}:{account_id}:table/{database_name}/{table_name}"
            
            self.lakeformation_client.register_resource(
                ResourceArn=table_arn,
                UseServiceLinkedRole=True
            )
            logger.info(f"Successfully registered table {database_name}.{table_name} with Lake Formation")
            return True
        except Exception as e:
            if "AlreadyExistsException" in str(e):
                logger.info(f"Table {database_name}.{table_name} already registered with Lake Formation")
                return True
            logger.error(f"Error registering table {database_name}.{table_name}: {e}")
            return False
    
    async def apply_lf_tags_to_resource(self, database_name: str, table_name: str, 
                                       column_name: str = None, pii_types: List[str] = None) -> bool:
        """Apply Lake Formation tags to resources based on PII detection results"""
        if self.config.dry_run:
            resource_desc = f"{database_name}.{table_name}"
            if column_name:
                resource_desc += f".{column_name}"
            logger.info(f"DRY RUN: Would apply LF tags to {resource_desc}")
            return True
        
        try:
            # Determine tags based on PII types
            lf_tags = []
            
            if pii_types:
                primary_pii = pii_types[0] if pii_types else "NONE"
                data_classification = self.get_data_classification(pii_types)
                access_level = self.get_access_level(data_classification)
                governance_tag = "PII_DETECTED" if pii_types else "PUBLIC"
                
                if data_classification in ["HIGH_RISK", "CRITICAL_RISK"]:
                    pii_classification = "HIGHLY_SENSITIVE"
                elif data_classification == "MEDIUM_RISK":
                    pii_classification = "SENSITIVE"
                else:
                    pii_classification = "CONFIDENTIAL"
                
                lf_tags = [
                    {"TagKey": "PIIType", "TagValues": [primary_pii]},
                    {"TagKey": "DataClassification", "TagValues": [data_classification]},
                    {"TagKey": "AccessLevel", "TagValues": [access_level]},
                    {"TagKey": "DataGovernance", "TagValues": [governance_tag]},
                    {"TagKey": "PIIClassification", "TagValues": [pii_classification]}
                ]
            else:
                lf_tags = [
                    {"TagKey": "PIIType", "TagValues": ["NONE"]},
                    {"TagKey": "DataClassification", "TagValues": ["NO_RISK"]},
                    {"TagKey": "AccessLevel", "TagValues": ["PUBLIC"]},
                    {"TagKey": "DataGovernance", "TagValues": ["PUBLIC"]}
                ]
            
            # Try MCP client first
            if self.dataprocessing_mcp_client:
                response = await self.mcp_client._call_mcp_tool(
                    self.dataprocessing_mcp_client,
                    'add_lf_tags_to_resource',
                    {
                        'database_name': database_name,
                        'table_name': table_name,
                        'column_name': column_name,
                        'lf_tags': lf_tags
                    }
                )
                if response.get('success'):
                    resource_desc = f"{database_name}.{table_name}"
                    if column_name:
                        resource_desc += f".{column_name}"
                    logger.info(f"Successfully applied LF tags to {resource_desc} via MCP")
                    return True
            
            # Fallback to boto3
            if column_name:
                resource = {
                    "TableWithColumns": {
                        "DatabaseName": database_name,
                        "Name": table_name,
                        "ColumnNames": [column_name]
                    }
                }
            else:
                resource = {
                    "Table": {
                        "DatabaseName": database_name,
                        "Name": table_name
                    }
                }
            
            self.lakeformation_client.add_lf_tags_to_resource(
                Resource=resource,
                LFTags=lf_tags
            )
            
            resource_desc = f"{database_name}.{table_name}"
            if column_name:
                resource_desc += f".{column_name}"
            logger.info(f"Successfully applied LF tags to {resource_desc}")
            return True
            
        except Exception as e:
            logger.error(f"Error applying LF tags: {e}")
            return False
    
    async def get_classification_summary(self) -> Dict[str, Any]:
        """Get summary of PII classifications across databases"""
        try:
            scan_results = await self.scan_for_pii()
            
            classifications = {}
            for finding in scan_results.get('findings', []):
                if hasattr(finding, 'data_classification'):
                    classification = finding.data_classification
                    table_name = f"{finding.database_name}.{finding.table_name}"
                elif isinstance(finding, dict):
                    classification = finding.get('data_classification', 'UNKNOWN')
                    table_name = finding.get('table_name', 'unknown')
                else:
                    continue
                
                if classification not in classifications:
                    classifications[classification] = {'count': 0, 'tables': set()}
                
                classifications[classification]['count'] += 1
                classifications[classification]['tables'].add(table_name)
            
            # Convert sets to lists for JSON serialization
            for classification in classifications:
                classifications[classification]['tables'] = list(classifications[classification]['tables'])
            
            return classifications
            
        except Exception as e:
            logger.error(f"Error getting classification summary: {e}")
            return {}
    
    async def scan_for_pii(self) -> Dict[str, Any]:
        """Main method to scan for PII across all data sources"""
        logger.info("Starting comprehensive PII scan across all data sources...")
        
        all_results = []
        total_sources = 0
        pii_sources_found = 0
        total_tables = 0
        total_columns = 0
        pii_columns_found = 0
        no_risk_columns_found = 0
        
        # 0. Create Lake Formation tags first
        logger.info("🏷️ Phase 0: Creating Lake Formation tags...")
        await self.create_lake_formation_tags()
        
        # 1. Scan Glue Data Catalog
        logger.info("🔍 Phase 1: Scanning Glue Data Catalog...")
        glue_tables = await self.scan_glue_catalog()
        total_tables = len(glue_tables)
        
        if glue_tables:
            for table in glue_tables:
                total_sources += 1
                
                # Register table with Lake Formation
                await self.register_table_with_lakeformation(table['DatabaseName'], table['TableName'])
                
                # Register S3 location if available
                if table.get('Location'):
                    await self.register_s3_location_with_lakeformation(table['Location'])
                
                for column in table['Columns']:
                    total_columns += 1
                    # Detect PII
                    pii_types, confidence_scores = self.detect_pii_by_column_name(column['Name'])
                    data_classification = self.get_data_classification(pii_types)
                    
                    # Apply Lake Formation tags
                    lf_tags_applied = await self.apply_lf_tags_to_resource(
                        table['DatabaseName'], 
                        table['TableName'], 
                        column['Name'], 
                        pii_types
                    )
                    
                    result = PIIDetectionResult(
                        database_name=table['DatabaseName'],
                        table_name=table['TableName'],
                        column_name=column['Name'],
                        column_type=column['Type'],
                        pii_types=pii_types,
                        confidence_scores=confidence_scores,
                        data_classification=data_classification,
                        tagging_status="applied" if lf_tags_applied else "failed"
                    )
                    
                    all_results.append(result)
                    
                    if result.pii_types:
                        pii_columns_found += 1
                        logger.info(f"  🚨 PII found in {column['Name']}: {', '.join(result.pii_types)} ({result.data_classification})")
                    else:
                        no_risk_columns_found += 1
                        logger.info(f"  ✅ No-risk data in {column['Name']}: {result.data_classification}")
        
        # 2. Scan S3 Data
        logger.info("🔍 Phase 2: Scanning S3 Data...")
        s3_results = await self.scan_s3_data()
        
        for s3_result in s3_results:
            total_sources += 1
            if s3_result['pii_types']:
                pii_sources_found += 1
                # Register S3 location with Lake Formation
                s3_path = f"s3://{s3_result['bucket_name']}/{s3_result['key']}"
                await self.register_s3_location_with_lakeformation(s3_path)
        
        all_results.extend(s3_results)
        
        # 3. Scan DynamoDB Data
        logger.info("🔍 Phase 3: Scanning DynamoDB Data...")
        dynamodb_results = await self.scan_dynamodb_data()
        
        for dynamodb_result in dynamodb_results:
            total_sources += 1
            if dynamodb_result['pii_types']:
                pii_sources_found += 1
        
        all_results.extend(dynamodb_results)
        
        # Separate findings by risk level
        pii_findings = [r for r in all_results if hasattr(r, 'pii_types') and r.pii_types or 
                       (isinstance(r, dict) and r.get('pii_types'))]
        no_risk_findings = [r for r in all_results if hasattr(r, 'pii_types') and not r.pii_types or 
                           (isinstance(r, dict) and not r.get('pii_types'))]
        
        logger.info(f"Comprehensive scan completed:")
        logger.info(f"  Total data sources: {total_sources}")
        logger.info(f"  PII sources found: {pii_sources_found}")
        logger.info(f"  Glue tables: {len(glue_tables)}")
        logger.info(f"  S3 objects with PII: {len(s3_results)}")
        logger.info(f"  DynamoDB tables with PII: {len(dynamodb_results)}")
        logger.info(f"  Lake Formation resources registered and tagged")
        
        return {
            "status": "completed",
            "region": self.config.aws_region,
            "total_sources": total_sources,
            "total_tables": total_tables,
            "total_columns": total_columns,
            "pii_columns_found": pii_columns_found,
            "no_risk_columns_found": no_risk_columns_found,
            "pii_sources_found": pii_sources_found,
            "glue_tables_scanned": len(glue_tables),
            "s3_objects_with_pii": len(s3_results),
            "dynamodb_tables_with_pii": len(dynamodb_results),
            "lake_formation_enabled": True,
            "findings": all_results,
            "pii_findings": pii_findings,
            "no_risk_findings": no_risk_findings
        }

# Convenience function for quick usage
async def scan_pii(region: str = "us-west-2", databases: List[str] = None, dry_run: bool = True,
                   enable_s3: bool = True, enable_dynamodb: bool = True, use_mcp_servers: bool = True,
                   apply_lf_tags: bool = True) -> Dict[str, Any]:
    """Convenience function to scan for PII across all data sources with Lake Formation integration"""
    config = PIIDetectionConfig(
        aws_region=region,
        glue_databases=databases or [],
        dry_run=dry_run,
        enable_s3_discovery=enable_s3,
        enable_dynamodb_discovery=enable_dynamodb,
        use_mcp_servers=use_mcp_servers,
        apply_lf_tags=apply_lf_tags
    )
    
    agent = AWSPIIDetectionAgent(config)
    return await agent.scan_for_pii()

if __name__ == "__main__":
    async def main():
        print("🚀 AWS PII Detection Agent")
        print("=" * 50)
        
        config = PIIDetectionConfig(
            aws_region="us-west-2",
            dry_run=True,
            comprehend_enabled=True,
            apply_lf_tags=True
        )
        
        agent = AWSPIIDetectionAgent(config)
        results = await agent.scan_for_pii()
        
        print(f"\n📊 Results: {results['pii_columns_found']} PII columns found")
        return results
    
    asyncio.run(main())
