#!/usr/bin/env python3
"""
Test script for database infrastructure
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from infrastructure.database import DatabaseManager, DatabaseConfig, MigrationManager, initialize_database, get_database_manager

def test_database_config():
    """Test database configuration"""
    print("Testing Database Configuration...")
    
    try:
        config = DatabaseConfig()
        print(f"✅ Database Config: Type = {config.db_type}")
        print(f"   - SQLite path: {config.sqlite_path}")
        print(f"   - PostgreSQL connection: {config.get_postgres_connection_string()}")
        return True
        
    except Exception as e:
        print(f"❌ Database Config failed: {e}")
        return False

def test_sqlite_manager():
    """Test SQLite database manager"""
    print("\nTesting SQLite Manager...")
    
    try:
        # Set environment to use SQLite
        os.environ["DB_TYPE"] = "sqlite"
        os.environ["SQLITE_PATH"] = "./data/test_chimera.db"
        
        config = DatabaseConfig()
        db_manager = DatabaseManager(config)
        
        # Test connection
        if not db_manager.test_connection():
            print("❌ SQLite Manager: Connection test failed")
            return False
        
        # Test basic query
        result = db_manager.execute_query("SELECT 1 as test")
        if result and result[0]['test'] == 1:
            print("✅ SQLite Manager: Basic query successful")
        else:
            print("❌ SQLite Manager: Basic query failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ SQLite Manager failed: {e}")
        return False

def test_postgresql_availability():
    """Test PostgreSQL driver availability"""
    print("\nTesting PostgreSQL Availability...")
    
    try:
        import psycopg2
        print("✅ psycopg2 available")
        
        import asyncpg
        print("✅ asyncpg available")
        
        return True
        
    except ImportError as e:
        print(f"❌ PostgreSQL drivers not available: {e}")
        return False

def test_migration_manager():
    """Test migration manager"""
    print("\nTesting Migration Manager...")
    
    try:
        # Use SQLite for testing
        os.environ["DB_TYPE"] = "sqlite"
        os.environ["SQLITE_PATH"] = "./data/test_migration.db"
        
        db_manager = DatabaseManager()
        migration_manager = MigrationManager(db_manager)
        
        # Test migrations table creation
        migration_manager.ensure_migrations_table()
        print("✅ Migration Manager: Migrations table created")
        
        # Test getting applied migrations
        applied = migration_manager.get_applied_migrations()
        print(f"✅ Migration Manager: Found {len(applied)} applied migrations")
        
        # Test applying migrations
        migration_manager.migrate_to_latest()
        print("✅ Migration Manager: Latest migrations applied")
        
        # Verify tables were created
        tables = db_manager.execute_query("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        
        table_names = [table['name'] for table in tables]
        expected_tables = ['missions', 'leads', 'conversations', 'messages', 'content', 'fulfillment_projects', 'schema_migrations']
        
        missing_tables = [table for table in expected_tables if table not in table_names]
        if missing_tables:
            print(f"❌ Migration Manager: Missing tables: {missing_tables}")
            return False
        
        print(f"✅ Migration Manager: All {len(expected_tables)} tables created")
        return True
        
    except Exception as e:
        print(f"❌ Migration Manager failed: {e}")
        return False

def test_database_operations():
    """Test basic database operations"""
    print("\nTesting Database Operations...")
    
    try:
        # Use SQLite for testing
        os.environ["DB_TYPE"] = "sqlite"
        os.environ["SQLITE_PATH"] = "./data/test_operations.db"
        
        # Initialize database
        initialize_database()
        print("✅ Database Operations: Database initialized")
        
        db_manager = DatabaseManager()
        
        # Test INSERT
        mission_id = "test_mission_001"
        rows_affected = db_manager.execute_update(
            "INSERT INTO missions (id, company_name, target_audience) VALUES (?, ?, ?)",
            (mission_id, "Test Company", "Small businesses")
        )
        
        if rows_affected == 1:
            print("✅ Database Operations: INSERT successful")
        else:
            print("❌ Database Operations: INSERT failed")
            return False
        
        # Test SELECT
        missions = db_manager.execute_query(
            "SELECT * FROM missions WHERE id = ?",
            (mission_id,)
        )
        
        if missions and missions[0]['company_name'] == "Test Company":
            print("✅ Database Operations: SELECT successful")
        else:
            print("❌ Database Operations: SELECT failed")
            return False
        
        # Test UPDATE
        rows_affected = db_manager.execute_update(
            "UPDATE missions SET brand_voice = ? WHERE id = ?",
            ("Professional", mission_id)
        )
        
        if rows_affected == 1:
            print("✅ Database Operations: UPDATE successful")
        else:
            print("❌ Database Operations: UPDATE failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database Operations failed: {e}")
        return False

def test_convenience_functions():
    """Test convenience functions"""
    print("\nTesting Convenience Functions...")
    
    try:
        # Test get_database_manager
        db_manager = get_database_manager()
        if db_manager and db_manager.test_connection():
            print("✅ Convenience Functions: get_database_manager works")
        else:
            print("❌ Convenience Functions: get_database_manager failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Convenience Functions failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Project Chimera Database Infrastructure Test ===")
    
    # Run tests
    tests = [
        test_database_config,
        test_sqlite_manager,
        test_postgresql_availability,
        test_migration_manager,
        test_database_operations,
        test_convenience_functions
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print(f"\n=== Test Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("🎉 All database infrastructure tests passed!")
    else:
        print("⚠️ Some tests failed - check the output above")
    
    # Cleanup test files
    try:
        import glob
        test_files = glob.glob("./data/test_*.db")
        for file in test_files:
            os.remove(file)
        print(f"\n🧹 Cleaned up {len(test_files)} test database files")
    except:
        pass
