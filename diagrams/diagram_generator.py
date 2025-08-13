#!/usr/bin/env python3
"""AWS Diagram Generator for PII Detection Architecture"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.storage import S3
from diagrams.aws.database import Dynamodb
from diagrams.aws.analytics import Glue
from diagrams.aws.ml import Comprehend
from diagrams.aws.security import IAM
from diagrams.aws.integration import MQ
from diagrams.aws.compute import Lambda

def generate_pii_detection_architecture(filename="pii_detection_mcp_architecture"):
    """Generate PII detection architecture with MCP servers"""
    import os
    from pathlib import Path
    
    # Use dedicated diagrams folder in user home directory
    diagrams_dir = Path.home() / "aws-data-discovery-diagrams"
    diagrams_dir.mkdir(exist_ok=True)
    
    # Full path for diagram output
    full_path = diagrams_dir / filename
    
    with Diagram("PII Detection with MCP Servers", show=False, filename=str(full_path), direction="TB"):
        
        # MCP Server Layer
        with Cluster("MCP Server Layer"):
            orchestrator = MQ("PII Orchestrator\nMCP Server")
            data_proc_mcp = MQ("Data Processing\nMCP Server")
            s3_mcp = MQ("S3 Tables\nMCP Server")
            dynamo_mcp = MQ("DynamoDB\nMCP Server")
            diagram_mcp = MQ("Diagram\nMCP Server")
        
        # Data Sources
        with Cluster("Data Sources"):
            s3_buckets = S3("S3 Data Lake")
            dynamo_tables = Dynamodb("DynamoDB Tables")
        
        # Processing Layer
        with Cluster("Data Processing & Cataloging"):
            glue_catalog = Glue("Glue Data Catalog")
            pii_detection = Comprehend("PII Detection")
            lambda_processor = Lambda("PII Processor")
        
        # Governance Layer
        with Cluster("Data Governance"):
            lake_formation = Glue("Lake Formation")
            iam_roles = IAM("IAM Roles & Policies")
        
        # MCP Server Connections
        orchestrator >> Edge(label="orchestrate") >> [data_proc_mcp, s3_mcp, dynamo_mcp]
        orchestrator >> Edge(label="generate") >> diagram_mcp
        
        # Data Flow
        s3_mcp >> Edge(label="discover") >> s3_buckets
        dynamo_mcp >> Edge(label="discover") >> dynamo_tables
        data_proc_mcp >> Edge(label="catalog") >> glue_catalog
        
        # Processing Flow
        s3_buckets >> glue_catalog >> pii_detection
        dynamo_tables >> glue_catalog >> pii_detection
        pii_detection >> lambda_processor
        
        # Governance Flow
        lambda_processor >> lake_formation
        glue_catalog >> lake_formation
        iam_roles >> [glue_catalog, pii_detection, lambda_processor]
    
    return f"{full_path}.png"

if __name__ == "__main__":
    diagram_path = generate_pii_detection_architecture()
    print(f"Generated diagram: {diagram_path}")