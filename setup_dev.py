#!/usr/bin/env python3
"""
Development setup script for AWS Data Discovery Agent
Installs dependencies and configures the development environment
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def check_node_version():
    """Check if Node.js 18+ is installed"""
    try:
        result = subprocess.run("node --version", shell=True, capture_output=True, text=True)
        version = result.stdout.strip()
        major_version = int(version.replace('v', '').split('.')[0])
        if major_version >= 18:
            print(f"✅ Node.js {version} is installed")
            return True
        else:
            print(f"❌ Node.js {version} is too old. Please install Node.js 18+")
            return False
    except:
        print("❌ Node.js is not installed. Please install Node.js 18+")
        return False

def main():
    """Main setup function"""
    print("🚀 AWS Data Discovery Agent - Development Setup")
    print("=" * 50)
    
    # Check Node.js
    if not check_node_version():
        print("\n📋 To install Node.js:")
        print("   macOS: brew install node")
        print("   Ubuntu: sudo apt update && sudo apt install nodejs npm")
        print("   Windows: Download from https://nodejs.org/")
        return False
    
    # Install Python dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return False
    
    # Install development dependencies
    if not run_command("pip install -e .[dev]", "Installing development dependencies"):
        return False
    
    # Install AWS Labs MCP servers
    mcp_servers = [
        "@awslabs/aws-dataprocessing-mcp-server",
        "@awslabs/dynamodb-mcp-server", 
        "@awslabs/s3-tables-mcp-server",
        "@awslabs/aws-diagram-mcp-server"
    ]
    
    for server in mcp_servers:
        if not run_command(f"npm install -g {server}", f"Installing {server}"):
            print(f"⚠️  Failed to install {server} - continuing anyway")
    
    # Setup pre-commit hooks
    if run_command("pre-commit install", "Setting up pre-commit hooks"):
        print("✅ Pre-commit hooks installed")
    
    # Check AWS CLI
    try:
        subprocess.run("aws --version", shell=True, check=True, capture_output=True)
        print("✅ AWS CLI is installed")
    except:
        print("⚠️  AWS CLI not found. Please install and configure:")
        print("   pip install awscli")
        print("   aws configure")
    
    print("\n🎉 Development setup completed!")
    print("\n📋 Next steps:")
    print("   1. Configure AWS credentials: aws configure")
    print("   2. Set AWS region: export AWS_REGION=us-west-2")
    print("   3. Run tests: python -m pytest tests/ -v")
    print("   4. Start the agent: python run_agent.py")
    print("   5. Launch dashboard: streamlit run servers/pii_dashboard.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)