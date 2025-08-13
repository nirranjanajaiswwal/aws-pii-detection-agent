#!/usr/bin/env python3
"""
Setup script for AWS PII Detection Agent MCP Server
Configures the MCP server for use with Q Chat and other MCP clients
"""

import json
import os
import sys
from pathlib import Path

def get_project_root():
    """Get the absolute path to the project root"""
    return Path(__file__).parent.absolute()

def create_mcp_config():
    """Create MCP configuration for Q Chat"""
    project_root = get_project_root()
    
    # User-specific config with absolute paths
    config = {
        "mcpServers": {
            "aws-pii-detection-agent": {
                "command": "python",
                "args": [str(project_root / "mcp_server.py")],
                "env": {
                    "AWS_PROFILE": os.getenv("AWS_PROFILE", "default"),
                    "AWS_REGION": os.getenv("AWS_REGION", "us-west-2"),
                    "PYTHONPATH": str(project_root)
                }
            }
        }
    }
    
    # Write user-specific config (this will be gitignored)
    config_path = project_root / "mcp_config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ MCP configuration created: {config_path}")
    print(f"   (This file is gitignored and won't be committed)")
    
    # Check if config exists
    config_path = project_root / "mcp_config.json"
    if config_path.exists():
        print(f"✅ Configuration file available: {config_path}")
        print(f"   (This will be overwritten with your specific paths)")
    
    return config_path

def install_dependencies():
    """Install required dependencies"""
    project_root = get_project_root()
    requirements_path = project_root / "requirements.txt"
    
    print("📦 Installing dependencies...")
    os.system(f"pip install -r {requirements_path}")
    print("✅ Dependencies installed")

def test_mcp_server():
    """Test that the MCP server can start"""
    project_root = get_project_root()
    server_path = project_root / "mcp_server.py"
    
    print("🧪 Testing MCP server...")
    # Add a simple import test
    try:
        sys.path.insert(0, str(project_root))
        from mcp_server import server
        print("✅ MCP server imports successfully")
        return True
    except Exception as e:
        print(f"❌ MCP server test failed: {e}")
        return False

def show_usage_instructions(config_path):
    """Show instructions for using the MCP server"""
    print("\n" + "="*60)
    print("🚀 AWS PII Detection Agent MCP Server Setup Complete!")
    print("="*60)
    
    print("\n📋 Usage Instructions:")
    print("\n1. For Q Chat CLI:")
    print(f"   Add this to your Q Chat MCP configuration:")
    print(f"   {config_path}")
    
    print("\n2. Manual MCP Server Start:")
    print(f"   python {config_path.parent}/mcp_server.py")
    
    print("\n3. Available Tools:")
    tools = [
        "scan_pii - Scan AWS Glue Data Catalog for PII",
        "analyze_table - Analyze specific table for PII",
        "preview_masking - Preview PII masking strategies",
        "create_lf_tags - Create Lake Formation tags",
        "get_classification_summary - Get PII classification summary"
    ]
    for tool in tools:
        print(f"   • {tool}")
    
    print("\n4. Available Resources:")
    resources = [
        "pii://detection/config - PII detection configuration",
        "pii://masking/strategies - Available masking strategies",
        "pii://detection/patterns - PII detection patterns"
    ]
    for resource in resources:
        print(f"   • {resource}")
    
    print("\n🔧 Configuration:")
    print("   • AWS credentials should be configured (aws configure)")
    print("   • Default region: us-west-2 (configurable)")
    print("   • Dry run mode enabled by default for safety")
    
    print("\n📖 Example Usage in Q Chat:")
    print('   "Scan for PII in my AWS data catalog"')
    print('   "Show me masking strategies for email addresses"')
    print('   "Analyze the employee_data table for PII"')
    print('   "Create Lake Formation tags for data governance"')

def main():
    """Main setup function"""
    print("🔧 Setting up AWS PII Detection Agent MCP Server...")
    
    # Install dependencies
    install_dependencies()
    
    # Create MCP config
    config_path = create_mcp_config()
    
    # Test server
    if test_mcp_server():
        show_usage_instructions(config_path)
    else:
        print("❌ Setup failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
