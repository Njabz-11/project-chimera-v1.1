#!/usr/bin/env python3
"""
PostgreSQL Setup Script for Project Chimera
Genesis Compliance: Ensures PostgreSQL is used consistently across all environments
"""

import os
import sys
import asyncio
import asyncpg
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from config.settings import get_settings
from utils.logger import ChimeraLogger

logger = ChimeraLogger.get_logger(__name__)

async def check_postgresql_connection():
    """Check if PostgreSQL is accessible"""
    settings = get_settings()
    
    try:
        # Parse the DATABASE_URL
        if settings.database_url.startswith("postgresql://"):
            # Extract connection parameters from URL
            url_parts = settings.database_url.replace("postgresql://", "").split("@")
            user_pass = url_parts[0].split(":")
            host_db = url_parts[1].split("/")
            host_port = host_db[0].split(":")
            
            user = user_pass[0]
            password = user_pass[1] if len(user_pass) > 1 else ""
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 5432
            database = host_db[1]
            
            logger.info(f"Attempting to connect to PostgreSQL at {host}:{port}/{database}")
            
            # Try to connect
            conn = await asyncpg.connect(
                user=user,
                password=password,
                database=database,
                host=host,
                port=port
            )
            
            # Test the connection
            version = await conn.fetchval("SELECT version()")
            logger.info(f"✅ PostgreSQL connection successful: {version}")
            
            await conn.close()
            return True
            
    except Exception as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        return False

async def create_database_schema():
    """Create the database schema if it doesn't exist"""
    settings = get_settings()
    
    try:
        # Parse connection parameters
        url_parts = settings.database_url.replace("postgresql://", "").split("@")
        user_pass = url_parts[0].split(":")
        host_db = url_parts[1].split("/")
        host_port = host_db[0].split(":")
        
        user = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ""
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 5432
        database = host_db[1]
        
        conn = await asyncpg.connect(
            user=user,
            password=password,
            database=database,
            host=host,
            port=port
        )
        
        # Create basic schema
        schema_sql = """
        -- Create extensions
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "pg_trgm";
        
        -- Create missions table
        CREATE TABLE IF NOT EXISTS missions (
            id SERIAL PRIMARY KEY,
            business_goal TEXT,
            target_audience TEXT,
            brand_voice TEXT,
            service_offerings JSONB,
            value_proposition TEXT,
            key_messaging TEXT,
            success_metrics JSONB,
            budget_range TEXT,
            timeline TEXT,
            strategic_approach TEXT,
            content_themes JSONB,
            lead_qualification_criteria TEXT,
            competitive_advantages TEXT,
            status VARCHAR(50) DEFAULT 'active',
            progress INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create leads table
        CREATE TABLE IF NOT EXISTS leads (
            id SERIAL PRIMARY KEY,
            mission_id INTEGER REFERENCES missions(id),
            company_name VARCHAR(255),
            contact_person VARCHAR(255),
            email VARCHAR(255),
            phone VARCHAR(50),
            website VARCHAR(255),
            pain_point TEXT,
            status VARCHAR(50) DEFAULT 'new',
            source VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create users table
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'client',
            is_active BOOLEAN DEFAULT true,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create content table
        CREATE TABLE IF NOT EXISTS content (
            id SERIAL PRIMARY KEY,
            mission_id INTEGER REFERENCES missions(id),
            title VARCHAR(255),
            content_type VARCHAR(100),
            content TEXT,
            platform VARCHAR(100),
            status VARCHAR(50) DEFAULT 'draft',
            scheduled_for TIMESTAMP,
            published_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create fulfillment_projects table
        CREATE TABLE IF NOT EXISTS fulfillment_projects (
            id SERIAL PRIMARY KEY,
            mission_id INTEGER REFERENCES missions(id),
            project_type VARCHAR(100),
            description TEXT,
            requirements JSONB,
            status VARCHAR(50) DEFAULT 'pending',
            deliverable_path VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        );
        
        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status);
        CREATE INDEX IF NOT EXISTS idx_leads_mission_id ON leads(mission_id);
        CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_content_mission_id ON content(mission_id);
        CREATE INDEX IF NOT EXISTS idx_fulfillment_mission_id ON fulfillment_projects(mission_id);
        """
        
        await conn.execute(schema_sql)
        logger.info("✅ Database schema created successfully")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create database schema: {e}")
        return False

async def main():
    """Main setup function"""
    logger.info("🚀 Starting PostgreSQL setup for Project Chimera (Genesis Compliance)")
    
    # Check PostgreSQL connection
    if not await check_postgresql_connection():
        logger.error("❌ PostgreSQL setup failed - cannot connect to database")
        logger.info("💡 Make sure PostgreSQL is running and accessible")
        logger.info("💡 You can start it with Docker: docker-compose up postgres")
        return False
    
    # Create database schema
    if not await create_database_schema():
        logger.error("❌ PostgreSQL setup failed - cannot create schema")
        return False
    
    logger.info("✅ PostgreSQL setup completed successfully!")
    logger.info("🎯 Project Chimera is now Genesis compliant with PostgreSQL")
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
