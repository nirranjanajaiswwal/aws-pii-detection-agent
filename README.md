# AWS Data Discovery & PII Detection Agent

A comprehensive MCP (Model Context Protocol) server for automated AWS data discovery, PII detection, and data governance using Lake Formation. This comprehensive server provides automated data discovery, PII classification, and governance workflows, featuring 14+ operational tools for discovering AWS data sources, creating and running Glue crawlers, applying Lake Formation tags, cataloging data, detecting sensitive data, launching interactive dashboards, and generating compliance documentation.

## Available MCP Tools

### Data Discovery & Orchestration
- `orchestrate_data_discovery` - Complete data discovery workflow with S3, DynamoDB, Glue cataloging, and PII detection
- `discover_aws_data_sources` - Discover S3 buckets and DynamoDB tables across AWS regions
- `get_dashboard_data` - Run data discovery workflow and prepare data for dashboard display
- `launch_data_discovery_dashboard` - Launch interactive Streamlit dashboard at http://localhost:8501

### Data Cataloging & Classification
- `catalog_with_glue` - Create and run Glue crawlers to catalog S3 and DynamoDB data sources
- `classify_and_tag_data` - Classify data and apply Lake Formation tags for governance
- `generate_architecture_diagram` - Generate AWS architecture diagrams for discovered infrastructure

### AWS Labs MCP Integration
- `list_s3_buckets` - List S3 buckets using s3-tables-mcp-server
- `manage_aws_glue_databases` - Create Glue databases using aws-dataprocessing-mcp-server
- `list_dynamodb_tables` - List DynamoDB tables using dynamodb-mcp-server

### Glue Crawler Operations
- `create_glue_crawler` - Create Glue crawlers for S3 and DynamoDB targets
- `start_glue_crawler` - Start/run Glue crawlers to catalog data
- `get_glue_crawler_status` - Monitor crawler execution status (RUNNING, SUCCEEDED, FAILED)

### Lake Formation Integration
- `create_lf_tags` - Create Lake Formation tag definitions for data governance
- `register_s3_with_lakeformation` - Register S3 locations with Lake Formation
- `register_table_with_lakeformation` - Register Glue tables with Lake Formation
- `apply_lf_tags` - Apply Lake Formation tags to resources based on PII detection

## Available MCP Resources

- `discovery://s3/buckets` - List of discovered S3 buckets
- `discovery://dynamodb/tables` - List of discovered DynamoDB tables
- `catalog://glue/databases` - Cataloged databases in Glue
- `classification://pii/results` - Data classification and PII detection results
- `lakeformation://tags/definitions` - Lake Formation tag definitions for governance
- `lakeformation://resources/registered` - S3 locations and tables registered with Lake Formation
- `lakeformation://tags/applied` - Applied Lake Formation tags by resource

## Available MCP Prompts

- `classify_data_sensitivity` - Classify data sensitivity based on content analysis
- `generate_compliance_tags` - Generate Lake Formation tags for compliance requirements
- `create_data_governance_policy` - Create data governance policy based on discovered data
- `setup_lakeformation_governance` - Setup complete Lake Formation governance for discovered resources

## Instructions

The MCP Server for AWS data discovery and classification provides a comprehensive set of tools for discovering, cataloging, and classifying sensitive data across AWS environments.

To use these tools, ensure you have proper AWS credentials configured with appropriate permissions for S3, DynamoDB, Glue, and Comprehend operations. The server will automatically use credentials from environment variables or other standard AWS credential sources.

All tools support an optional `region` parameter to specify which AWS region to operate in. If not provided, it will use the AWS_REGION environment variable or default to 'us-west-2'.

## 🚀 Features

- **Automated Data Discovery**: Discover S3 buckets and DynamoDB tables across AWS regions
- **PII Detection**: Identify sensitive data using AWS Comprehend and pattern matching
- **Data Cataloging**: Create and manage AWS Glue databases and tables
- **Lake Formation Integration**: Complete governance with automated tagging and permissions
- **Interactive Dashboard**: Real-time visualization with Streamlit
- **Architecture Diagrams**: Auto-generate AWS architecture documentation
- **MCP Integration**: Leverages official AWS Labs MCP servers

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│     FastMCP Orchestrator Server     │
│  (data-discovery-orchestrator)      │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│      AWS Labs MCP Servers           │
│  • aws-dataprocessing-mcp-server    │
│  • dynamodb-mcp-server              │
│  • s3-tables-mcp-server             │
│  • aws-diagram-mcp-server           │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│           AWS Services              │
│  • Amazon S3                        │
│  • Amazon DynamoDB                  │
│  • AWS Glue                         │
│  • AWS Lake Formation               │
│  • Amazon Comprehend                │
└─────────────────────────────────────┘
```

## 📋 Prerequisites

1. **Python 3.8+**
2. **Node.js 18+** (required for AWS Labs MCP servers)
3. **AWS CLI configured** with appropriate permissions:
   - S3: ListBucket, GetObject
   - DynamoDB: ListTables, DescribeTable, Scan
   - Glue: CreateDatabase, CreateTable, GetDatabase, GetTable
   - Lake Formation: RegisterResource, AddLFTagsToResource
   - Comprehend: DetectPiiEntities

## 🛠️ Installation

### 1. Install AWS Labs MCP Servers

```bash
npm install -g @awslabs/aws-dataprocessing-mcp-server
npm install -g @awslabs/dynamodb-mcp-server
npm install -g @awslabs/s3-tables-mcp-server
npm install -g @awslabs/aws-diagram-mcp-server
```

### 2. Install Python Dependencies

```bash
git clone <repository-url>
cd aws-data-discovery-agent
pip install -r requirements.txt
```

### 3. Configure AWS Credentials

```bash
aws configure
export AWS_REGION=us-west-2
```

## 🚀 Quick Start

### Run Complete Data Discovery Workflow

```bash
python servers/run_data_discovery_agent.py
```

This will:
1. Discover S3 buckets and DynamoDB tables
2. Create Glue databases for cataloging
3. Run Glue crawlers to catalog data
4. Detect PII in cataloged data
5. Register resources with Lake Formation
6. Apply governance tags based on PII detection
7. Generate architecture diagrams

### Launch Interactive Dashboard

```bash
streamlit run servers/pii_dashboard.py
```

Access at `http://localhost:8501` to view:
- Real-time data discovery metrics
- PII classification results
- Lake Formation governance status
- Risk assessments and compliance tracking

## 🔧 MCP Server Configuration

Add to your MCP client configuration (e.g., `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "aws-data-discovery-agent": {
      "command": "python",
      "args": ["~/aws-data-discovery-agent/servers/mcp_server_orchestrator.py", "--allow-write"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "default"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## 🛠️ Available MCP Tools

### Data Discovery & Orchestration
- `orchestrate_data_discovery` - Complete workflow with S3, DynamoDB, Glue, and PII detection
- `discover_aws_data_sources` - Discover data sources across AWS regions
- `get_dashboard_data` - Prepare data for dashboard display
- `launch_data_discovery_dashboard` - Launch Streamlit dashboard

### Data Cataloging & Classification
- `catalog_with_glue` - Create and run Glue crawlers
- `classify_and_tag_data` - Classify data and apply Lake Formation tags
- `generate_architecture_diagram` - Generate AWS architecture diagrams

### Lake Formation Integration
- `create_lf_tags` - Create Lake Formation tag definitions
- `register_s3_with_lakeformation` - Register S3 locations
- `register_table_with_lakeformation` - Register Glue tables
- `apply_lf_tags` - Apply tags based on PII detection

### AWS Labs MCP Integration
- `list_s3_buckets` - List S3 buckets via s3-tables-mcp-server
- `manage_aws_glue_databases` - Manage Glue databases via aws-dataprocessing-mcp-server
- `list_dynamodb_tables` - List DynamoDB tables via dynamodb-mcp-server

## 🏷️ Lake Formation Governance

### Automated Tag Definitions
- **PIIType**: EMAIL, SSN, PHONE, NAME, ADDRESS, CREDIT_CARD, DATE_OF_BIRTH, SALARY, AGE, NONE
- **DataClassification**: NO_RISK, LOW_RISK, MEDIUM_RISK, HIGH_RISK, CRITICAL_RISK
- **AccessLevel**: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED, TOP_SECRET
- **DataGovernance**: PII_DETECTED, REQUIRES_MASKING, ACCESS_RESTRICTED, PUBLIC
- **PIIClassification**: SENSITIVE, HIGHLY_SENSITIVE, CONFIDENTIAL

### Resource Registration
- S3 locations automatically registered with Lake Formation
- Glue tables registered with Lake Formation
- Handles existing registrations gracefully

### Risk-Based Tagging
- Tags applied based on actual PII detection results
- Column-level and table-level tagging
- Automated access control classification

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Documentation**: See the `docs/` directory for detailed documentation

## 🎯 Roadmap

- [ ] Support for additional AWS data sources (RDS, Redshift)
- [ ] Enhanced PII detection with custom models
- [ ] Integration with AWS Config for compliance monitoring
- [ ] Multi-account support
- [ ] Advanced data lineage tracking
- [ ] Custom governance policies
