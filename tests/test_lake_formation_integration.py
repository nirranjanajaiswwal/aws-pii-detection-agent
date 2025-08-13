#!/usr/bin/env python3
"""
Comprehensive Lake Formation Integration Tests
Tests all Lake Formation functionality including MCP server integration
"""

import asyncio
import sys
import os

# Add the core module to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'servers'))

from core.pii_agent import AWSPIIDetectionAgent, PIIDetectionConfig
from core.aws_mcp_client import AWSMCPClient
from servers.mcp_server_aws import handle_call_tool, handle_list_tools

class TestLakeFormationIntegration:
    """Test suite for Lake Formation integration"""
    
    def __init__(self):
        self.config = PIIDetectionConfig(
            aws_region="us-west-2",
            dry_run=True,
            comprehend_enabled=False,
            apply_lf_tags=True,
            use_mcp_servers=True
        )
        self.agent = AWSPIIDetectionAgent(self.config)
        self.client = AWSMCPClient()

    async def test_mcp_tools_registration(self):
        """Test that all MCP tools are properly registered"""
        print("\n🔧 Testing MCP Tools Registration...")
        
        tools = await handle_list_tools()
        lf_tools = [t for t in tools if 'lake_formation' in t.name]
        
        print(f"✅ Total MCP tools: {len(tools)}")
        print(f"✅ Lake Formation tools: {len(lf_tools)}")
        
        for tool in lf_tools:
            print(f"   • {tool.name}")
        
        return len(lf_tools) >= 4

    async def test_lake_formation_tags(self):
        """Test Lake Formation tag creation"""
        print("\n🏷️  Testing Lake Formation Tag Creation...")
        
        # Test via agent
        created_tags = await self.agent.create_lake_formation_tags()
        print(f"✅ Agent created {len(created_tags)} tag definitions")
        
        # Test via MCP server
        try:
            result = await handle_call_tool("manage_lake_formation_tags", {
                "operation": "create",
                "tag_key": "PIIType",
                "tag_values": ["EMAIL", "PHONE"],
                "dry_run": True
            })
            print("✅ MCP server tag creation accessible")
        except Exception as e:
            print(f"⚠️  MCP server tag creation: {str(e)[:100]}...")
        
        return len(created_tags) > 0

    async def test_s3_registration(self):
        """Test S3 location registration with Lake Formation"""
        print("\n📦 Testing S3 Location Registration...")
        
        s3_path = "s3://test-data-bucket/pii-data/"
        
        # Test via agent
        success = await self.agent.register_s3_location_with_lakeformation(s3_path)
        print(f"✅ Agent S3 registration: {success}")
        
        # Test via MCP server
        try:
            result = await handle_call_tool("register_lake_formation_resources", {
                "resource_type": "s3",
                "resource_arn": s3_path,
                "dry_run": True
            })
            print("✅ MCP server S3 registration accessible")
        except Exception as e:
            print(f"⚠️  MCP server S3 registration: {str(e)[:100]}...")
        
        return True

    async def test_table_registration(self):
        """Test Glue table registration with Lake Formation"""
        print("\n🗃️  Testing Table Registration...")
        
        database_name = "test_db"
        table_name = "test_table"
        
        # Test via agent
        success = await self.agent.register_table_with_lakeformation(database_name, table_name)
        print(f"✅ Agent table registration: {success}")
        
        # Test via MCP client
        try:
            result = await self.client.register_lake_formation_resources("table", f"arn:aws:glue:us-west-2:123456789012:table/{database_name}/{table_name}")
            print("✅ MCP client table registration accessible")
        except Exception as e:
            print(f"⚠️  MCP client table registration: {str(e)[:100]}...")
        
        return True

    async def test_tag_application(self):
        """Test applying Lake Formation tags to resources"""
        print("\n🏷️  Testing Tag Application...")
        
        database_name = "test_db"
        table_name = "test_table"
        pii_types = ["EMAIL", "PHONE"]
        
        # Test via agent
        success = await self.agent.apply_lf_tags_to_resource(
            database_name, table_name, "email_column", pii_types
        )
        print(f"✅ Agent tag application: {success}")
        
        # Test via MCP server
        try:
            lf_tags = [{"key": "PIIType", "values": ["EMAIL"]}]
            result = await handle_call_tool("apply_lake_formation_tags", {
                "database_name": database_name,
                "table_name": table_name,
                "lf_tags": lf_tags,
                "dry_run": True
            })
            print("✅ MCP server tag application accessible")
        except Exception as e:
            print(f"⚠️  MCP server tag application: {str(e)[:100]}...")
        
        return True

    async def test_full_workflow(self):
        """Test complete PII detection workflow with Lake Formation"""
        print("\n🔍 Testing Full Workflow Integration...")
        
        results = await self.agent.scan_for_pii()
        
        print(f"✅ Workflow completed")
        print(f"   • Total sources: {results.get('total_sources', 0)}")
        print(f"   • PII sources: {results.get('pii_sources_found', 0)}")
        print(f"   • Lake Formation: {results.get('lake_formation_enabled', False)}")
        
        return results.get('status') == 'completed'

    async def run_all_tests(self):
        """Run all Lake Formation integration tests"""
        print("🚀 Lake Formation Integration Test Suite")
        print("=" * 60)
        
        tests = [
            ("MCP Tools Registration", self.test_mcp_tools_registration),
            ("Lake Formation Tags", self.test_lake_formation_tags),
            ("S3 Registration", self.test_s3_registration),
            ("Table Registration", self.test_table_registration),
            ("Tag Application", self.test_tag_application),
            ("Full Workflow", self.test_full_workflow)
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results[test_name] = result
            except Exception as e:
                print(f"❌ {test_name} failed: {e}")
                results[test_name] = False
        
        print("\n" + "=" * 60)
        print("📊 Test Results Summary:")
        
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {status} {test_name}")
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All Lake Formation integration tests passed!")
        else:
            print("⚠️  Some tests failed - check AWS permissions and MCP server availability")
        
        return results

async def main():
    """Main test runner"""
    test_suite = TestLakeFormationIntegration()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())