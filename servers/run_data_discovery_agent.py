#!/usr/bin/env python3
"""
Run Data Discovery & Classification Agent using FastMCP Framework
"""

import asyncio
import sys
from pathlib import Path

# Add servers to path
sys.path.insert(0, str(Path(__file__).parent / "servers"))

from mcp_server_orchestrator import MCPOrchestrator

async def run_data_discovery_workflow():
    """Run the complete data discovery and classification workflow"""
    print("🚀 Starting Data Discovery & Classification Agent")
    print("Using FastMCP Framework with AWS Labs MCP Integration:")
    print("  • FastMCP orchestrator server (decorator-based)")
    print("  • AWS Labs S3 MCP server (with boto3 fallback)")
    print("  • AWS Labs DynamoDB MCP server (with boto3 fallback)") 
    print("  • AWS Labs DataProcessing MCP server (with boto3 fallback)")
    print("  • AWS Labs Diagram MCP server (with boto3 fallback)")
    print("=" * 60)
    
    # Initialize orchestrator
    orchestrator = MCPOrchestrator()
    
    # Step 1: Initialize AWS clients
    print("1️⃣ Initializing AWS service clients...")
    print(f"   ✅ Initialized for region: {orchestrator.aws_region}")
    
    # Step 2: Discover data sources
    print("\n2️⃣ Discovering AWS data sources via AWS Labs MCP servers...")
    sources = await orchestrator.discover_data_sources()
    print(f"   📦 Found {len(sources['s3_buckets'])} S3 buckets:")
    for bucket in sources['s3_buckets']:
        print(f"      • {bucket}")
    print(f"   🗃️ Found {len(sources['dynamodb_tables'])} DynamoDB tables:")
    for table in sources['dynamodb_tables']:
        print(f"      • {table}")
    
    # Step 3: Catalog data with Glue
    print("\n3️⃣ Cataloging data with AWS Labs DataProcessing MCP server...")
    catalog_results = await orchestrator.catalog_data_with_glue(sources)
    print(f"   📋 Cataloged {len(catalog_results)} data sources:")
    for result in catalog_results:
        print(f"      • {result['name']} ({result['type']}): {result['status']}")
    
    # Step 4: Classify data and apply Lake Formation tags
    print("\n4️⃣ Classifying data and applying Lake Formation tags...")
    pii_results = await orchestrator.detect_and_tag_pii(catalog_results)
    print(f"   🏷️ Classified {len(pii_results)} sources with sensitive data:")
    for result in pii_results:
        risk_emoji = "🔴" if result['risk_level'] == "HIGH" else "🟡"
        print(f"      {risk_emoji} {result['source']}: {', '.join(result['pii_types'])} ({result['risk_level']})")
    
    # Step 5: Generate architecture diagram
    print("\n5️⃣ Generating architecture diagram via AWS Labs Diagram MCP server...")
    diagram_result = await orchestrator.generate_architecture_diagram({
        "sources": sources,
        "pii_results": pii_results
    })
    
    if diagram_result['diagram_generated']:
        print(f"   📈 Architecture diagram generated: {diagram_result['path']}")
    else:
        print(f"   ❌ Diagram generation failed: {diagram_result.get('error', 'Unknown error')}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Data Discovery & Classification Summary:")
    print(f"   • Data Sources: {len(sources['s3_buckets']) + len(sources['dynamodb_tables'])}")
    print(f"   • Cataloged Items: {len(catalog_results)}")
    print(f"   • Classified Sources: {len(pii_results)}")
    print(f"   • High Risk Sources: {len([r for r in pii_results if r['risk_level'] == 'HIGH'])}")
    print("=" * 60)
    print("🎉 Data Discovery & Classification Agent completed successfully!")

async def demonstrate_fastmcp_features():
    """Demonstrate FastMCP framework features"""
    print("\n🔧 FastMCP Framework Features Demonstration")
    print("=" * 60)
    
    orchestrator = MCPOrchestrator()
    
    print("✨ FastMCP Benefits:")
    print("   • 75% less boilerplate code")
    print("   • Decorator-based tool/resource/prompt definitions")
    print("   • Automatic type handling and validation")
    print("   • Built-in error handling")
    print("   • Simplified server setup with mcp.run()")
    
    # Test data discovery
    print("\n🔍 Data Source Discovery (via FastMCP tools):")
    sources = await orchestrator.discover_data_sources()
    print(f"   S3 Buckets: {sources['s3_buckets']}")
    print(f"   DynamoDB Tables: {sources['dynamodb_tables']}")
    
    # Test cataloging
    print("\n📋 Data Cataloging (via FastMCP integration):")
    catalog_results = await orchestrator.catalog_data_with_glue(sources)
    for result in catalog_results:
        print(f"   • {result['name']}: {result['status']}")
    
    # Test classification
    print("\n🏷️ Data Classification (via FastMCP workflow):")
    pii_results = await orchestrator.detect_and_tag_pii(catalog_results)
    for result in pii_results:
        print(f"   • {result['source']}: {result['risk_level']}")
    
    # Test diagram generation
    print("\n📈 Architecture Diagram Generation (via FastMCP):")
    diagram_result = await orchestrator.generate_architecture_diagram({})
    status = "✅ Success" if diagram_result['diagram_generated'] else "❌ Failed"
    print(f"   Status: {status}")
    if diagram_result['diagram_generated']:
        print(f"   Path: {diagram_result['path']}")

async def main():
    """Main execution function"""
    print("AWS Data Discovery & Classification Agent")
    print("Powered by FastMCP Framework for simplified MCP server implementation")
    
    try:
        # Run full workflow
        await run_data_discovery_workflow()
        
        # Demonstrate FastMCP features
        await demonstrate_fastmcp_features()
        
        print("\n🎯 Next Steps:")
        print("   • Run 'streamlit run pii_dashboard.py' for interactive dashboard")
        print("   • Run 'python test_fastmcp_server.py' to test FastMCP server")
        print("   • Check generated diagrams in the diagrams/ directory")
        
    except Exception as e:
        print(f"❌ Error running data discovery agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())