# AWS Data Discovery & PII Detection Agent

A comprehensive MCP (Model Context Protocol) server for automated AWS data discovery, PII detection, and data governance using Lake Formation.

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
│      AWS Labs MCP Servers          │
│  • aws-dataprocessing-mcp-server   │
│  • dynamodb-mcp-server             │
│  • s3-tables-mcp-server            │
│  • aws-diagram-mcp-server          │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│           AWS Services              │
│  • Amazon S3                       │
│  • Amazon DynamoDB                 │
│  • AWS Glue                        │
│  • AWS Lake Formation              │
│  • Amazon Comprehend               │
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

## 🧪 Testing

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Test Lake Formation Integration
```bash
python tests/test_lake_formation_integration.py
```

### Test Individual Components
```bash
python tests/test_fastmcp_server.py
python tests/test_simple.py
```

## 📁 Project Structure

```
aws-data-discovery-agent/
├── core/                          # Core functionality
│   ├── pii_agent.py              # Main PII detection agent
│   ├── aws_mcp_client.py         # AWS MCP client
│   └── masking.py                # Data masking utilities
├── servers/                       # MCP servers
│   ├── mcp_server_orchestrator.py # Main orchestrator server
│   ├── mcp_server_aws.py         # AWS-specific server
│   ├── pii_dashboard.py          # Streamlit dashboard
│   └── run_data_discovery_agent.py # Standalone runner
├── tests/                         # Test suite
│   ├── test_lake_formation_integration.py # LF integration tests
│   ├── test_fastmcp_server.py    # Server tests
│   └── test_simple.py            # Basic functionality tests
├── config/                        # Configuration
│   ├── mcp_config.json           # MCP server config
│   └── setup_mcp.py              # MCP setup utilities
├── diagrams/                      # Generated diagrams
│   └── diagram_generator.py      # Diagram generation
├── docs/                          # Documentation
└── requirements.txt               # Python dependencies
```

## 🔒 Security & Compliance

- **Dry Run Mode**: All operations support safe testing mode
- **IAM Permissions**: Follows least privilege principle
- **Data Privacy**: PII detection without data exposure
- **Audit Trail**: Complete logging of all operations
- **Encryption**: Supports encryption at rest and in transit

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
- **AWS Labs MCP**: Visit [awslabs/mcp](https://github.com/awslabs/mcp) for MCP server documentation

## 🎯 Roadmap

- [ ] Support for additional AWS data sources (RDS, Redshift)
- [ ] Enhanced PII detection with custom models
- [ ] Integration with AWS Config for compliance monitoring
- [ ] Multi-account support
- [ ] Advanced data lineage tracking
- [ ] Custom governance policies