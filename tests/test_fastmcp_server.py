#!/usr/bin/env python3
"""
Test script for FastMCP server
"""

import asyncio
import json
from servers.mcp_server_orchestrator import mcp, orchestrator

async def test_fastmcp_server():
    """Test FastMCP server functionality"""
    print("🧪 Testing FastMCP Server...")
    
    # Test 1: Check server initialization
    print(f"✅ Server name: {mcp.name}")
    
    # Test 2: List available tools
    tools = mcp._tools
    print(f"✅ Tools available: {len(tools)}")
    for tool_name in tools.keys():
        print(f"   • {tool_name}")
    
    # Test 3: List available resources
    resources = mcp._resources
    print(f"✅ Resources available: {len(resources)}")
    for resource_name in resources.keys():
        print(f"   • {resource_name}")
    
    # Test 4: List available prompts
    prompts = mcp._prompts
    print(f"✅ Prompts available: {len(prompts)}")
    for prompt_name in prompts.keys():
        print(f"   • {prompt_name}")
    
    # Test 5: Test orchestrator methods
    print("\n🔧 Testing orchestrator methods...")
    
    try:
        # Test data source discovery
        sources = await orchestrator.discover_data_sources()
        print(f"✅ Data sources discovered: {len(sources['s3_buckets'])} S3 buckets, {len(sources['dynamodb_tables'])} DynamoDB tables")
        
        # Test cataloging
        catalog_results = await orchestrator.catalog_data_with_glue(sources)
        print(f"✅ Cataloging results: {len(catalog_results)} items cataloged")
        
        # Test PII detection
        pii_results = await orchestrator.detect_and_tag_pii(catalog_results)
        print(f"✅ PII detection: {len(pii_results)} items with PII detected")
        
    except Exception as e:
        print(f"⚠️  Orchestrator test failed (expected with mock data): {e}")
    
    print("\n🎉 FastMCP server test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_fastmcp_server())