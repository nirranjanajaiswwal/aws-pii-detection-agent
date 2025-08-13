#!/usr/bin/env python3
"""
AWS Data Discovery & PII Detection Agent
Main entry point for running the complete data discovery workflow
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.pii_agent import AWSPIIDetectionAgent, PIIDetectionConfig

async def main():
    """Main entry point for the data discovery agent"""
    print("🚀 AWS Data Discovery & PII Detection Agent")
    print("=" * 50)
    
    # Configuration
    config = PIIDetectionConfig(
        aws_region=os.getenv("AWS_REGION", "us-west-2"),
        dry_run=False,
        comprehend_enabled=True,
        apply_lf_tags=True,
        use_mcp_servers=True
    )
    
    # Initialize agent
    agent = AWSPIIDetectionAgent(config)
    
    try:
        # Run complete workflow
        print("🔍 Starting data discovery workflow...")
        results = await agent.scan_for_pii()
        
        # Display results
        print("\n📊 Discovery Results:")
        print(f"   • Total sources scanned: {results.get('total_sources', 0)}")
        print(f"   • PII sources found: {results.get('pii_sources_found', 0)}")
        print(f"   • Lake Formation enabled: {results.get('lake_formation_enabled', False)}")
        print(f"   • Status: {results.get('status', 'unknown')}")
        
        if results.get('pii_sources_found', 0) > 0:
            print("\n⚠️  PII detected! Check the dashboard for detailed analysis.")
            print("   Run: streamlit run servers/pii_dashboard.py")
        
        print("\n✅ Data discovery workflow completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during data discovery: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())