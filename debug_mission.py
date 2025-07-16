#!/usr/bin/env python3
"""
Debug script to test mission creation endpoint
"""

import asyncio
import json
import sys
import os

# Add the Backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'Backend'))

from database.db_manager import DatabaseManager
from agents.orchestrator import OrchestratorAgent

async def test_mission_creation():
    """Test mission creation components individually"""
    print("🔍 Testing mission creation components...")
    
    # Test database connection
    print("\n1. Testing database connection...")
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Test orchestrator initialization
    print("\n2. Testing orchestrator initialization...")
    try:
        orchestrator = OrchestratorAgent(db_manager)
        await orchestrator.initialize()
        print("✅ Orchestrator initialization successful")
    except Exception as e:
        print(f"❌ Orchestrator initialization failed: {e}")
        return
    
    # Test mission data creation
    print("\n3. Testing mission data creation...")
    try:
        mission_data = {
            "business_goal": "Test mission for debugging",
            "target_audience": "Test audience",
            "brand_voice": "professional",
            "service_offerings": ["Test Service 1", "Test Service 2"],
            "contact_info": {
                "email": "test@example.com",
                "phone": "+1-555-123-4567",
                "company": "Test Company"
            },
            "created_by": 1,
            "created_by_username": "test_user"
        }
        print("✅ Mission data created successfully")
        print(f"Mission data: {json.dumps(mission_data, indent=2)}")
    except Exception as e:
        print(f"❌ Mission data creation failed: {e}")
        return
    
    # Test database mission creation
    print("\n4. Testing database mission creation...")
    try:
        mission_id = await db_manager.create_mission(mission_data)
        print(f"✅ Mission created in database with ID: {mission_id}")
    except Exception as e:
        print(f"❌ Database mission creation failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return
    
    # Test orchestrator mission start
    print("\n5. Testing orchestrator mission start...")
    try:
        await orchestrator.start_mission(mission_id, mission_data)
        print("✅ Orchestrator mission start successful")
    except Exception as e:
        print(f"❌ Orchestrator mission start failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return
    
    # Test mission retrieval
    print("\n6. Testing mission retrieval...")
    try:
        missions = await db_manager.get_all_missions()
        print(f"✅ Retrieved {len(missions)} missions from database")
        for mission in missions:
            print(f"  - Mission {mission.get('id')}: {mission.get('business_goal', 'No goal')[:50]}...")
    except Exception as e:
        print(f"❌ Mission retrieval failed: {e}")
        return
    
    # Cleanup
    print("\n7. Cleaning up...")
    try:
        await db_manager.close()
        print("✅ Database connection closed")
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
    
    print("\n🎉 All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_mission_creation())
