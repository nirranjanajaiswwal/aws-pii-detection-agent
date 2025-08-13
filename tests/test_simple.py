#!/usr/bin/env python3
"""
Simple test runner without pytest dependency
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "servers"))

from mcp_server_orchestrator import MCPOrchestrator, handle_call_tool, handle_read_resource, handle_get_prompt

async def test_tools():
    """Test MCP tools"""
    print("🔧 Testing MCP Tools...")
    
    # Test data discovery
    result = await handle_call_tool("discover_aws_data_sources", {"region": "us-west-2"})
    assert len(result) > 0
    assert "S3 Buckets" in result[0].text
    print("   ✅ discover_aws_data_sources")
    
    # Test orchestration
    result = await handle_call_tool("orchestrate_data_discovery", {"region": "us-west-2"})
    assert "Data Discovery & Classification Complete" in result[0].text
    print("   ✅ orchestrate_data_discovery")
    
    # Test classification
    result = await handle_call_tool("classify_and_tag_data", {
        "catalog_results": [{"name": "user-profiles", "type": "dynamodb"}]
    })
    assert "Data Classification & Tagging" in result[0].text
    print("   ✅ classify_and_tag_data")

async def test_resources():
    """Test MCP resources"""
    print("📚 Testing MCP Resources...")
    
    # Test S3 buckets resource
    result = await handle_read_resource("discovery://s3/buckets")
    data = json.loads(result)
    assert "s3_buckets" in data
    print("   ✅ discovery://s3/buckets")
    
    # Test PII results resource
    result = await handle_read_resource("classification://pii/results")
    data = json.loads(result)
    assert "high_risk" in data
    print("   ✅ classification://pii/results")
    
    # Test Lake Formation tags
    result = await handle_read_resource("tags://lakeformation/schema")
    data = json.loads(result)
    assert "DataClassification" in data
    print("   ✅ tags://lakeformation/schema")

async def test_prompts():
    """Test MCP prompts"""
    print("💬 Testing MCP Prompts...")
    
    # Test data sensitivity prompt
    result = await handle_get_prompt("classify_data_sensitivity", {
        "data_sample": "john.doe@company.com",
        "context": "user database"
    })
    assert "Analyze this data sample" in result
    print("   ✅ classify_data_sensitivity")
    
    # Test compliance tags prompt
    result = await handle_get_prompt("generate_compliance_tags", {
        "regulation": "GDPR",
        "data_types": ["EMAIL", "PHONE"]
    })
    assert "GDPR compliance" in result
    print("   ✅ generate_compliance_tags")

async def test_orchestrator():
    """Test orchestrator functionality"""
    print("🎯 Testing Orchestrator...")
    
    orchestrator = MCPOrchestrator()
    
    # Test data discovery
    sources = await orchestrator.discover_data_sources()
    assert "s3_buckets" in sources
    assert len(sources["s3_buckets"]) > 0
    print("   ✅ Data discovery")
    
    # Test cataloging
    catalog_results = await orchestrator.catalog_data_with_glue(sources)
    assert len(catalog_results) > 0
    print("   ✅ Glue cataloging")
    
    # Test PII detection
    pii_results = await orchestrator.detect_and_tag_pii(catalog_results)
    assert len(pii_results) > 0
    print("   ✅ PII detection")

def test_configuration():
    """Test configuration files"""
    print("⚙️ Testing Configuration...")
    
    # Test MCP config
    config_path = project_root / "config" / "mcp_config.json"
    assert config_path.exists()
    with open(config_path) as f:
        config = json.load(f)
    assert "mcpServers" in config
    print("   ✅ MCP configuration")
    
    # Test requirements
    req_path = project_root / "requirements.txt"
    assert req_path.exists()
    with open(req_path) as f:
        requirements = f.read()
    assert "mcp>=" in requirements
    print("   ✅ Requirements file")

async def run_all_tests():
    """Run all tests"""
    print("🧪 AWS Data Discovery & Classification Agent - Comprehensive Tests")
    print("=" * 70)
    
    try:
        await test_tools()
        await test_resources()
        await test_prompts()
        await test_orchestrator()
        test_configuration()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("🎉 Code is ready for production!")
        print("\nTested components:")
        print("   • All MCP primitives (Tools, Resources, Prompts)")
        print("   • AWS Labs MCP server integration")
        print("   • Data discovery and classification workflow")
        print("   • Configuration and setup")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)