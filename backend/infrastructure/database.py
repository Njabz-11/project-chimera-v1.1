"""
Database Infrastructure for Project Chimera
Supports both SQLite (development) and PostgreSQL (production)
"""

import os
import logging
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
import json
from datetime import datetime

# Database imports
try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False


class DatabaseConfig:
    """Database configuration management"""
    
    def __init__(self):
        self.db_type = os.getenv("DB_TYPE", "sqlite")
        self.sqlite_path = os.getenv("SQLITE_PATH", "./data/chimera.db")
        
        # PostgreSQL configuration
        self.pg_host = os.getenv("POSTGRES_HOST", "localhost")
        self.pg_port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.pg_database = os.getenv("POSTGRES_DB", "chimera")
        self.pg_user = os.getenv("POSTGRES_USER", "chimera_user")
        self.pg_password = os.getenv("POSTGRES_PASSWORD", "chimera_pass")
        
    def get_sqlite_connection_string(self) -> str:
        """Get SQLite connection string"""
        return self.sqlite_path
    
    def get_postgres_connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        return f"postgresql://{self.pg_user}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_database}"
    
    def get_postgres_connection_params(self) -> Dict[str, Any]:
        """Get PostgreSQL connection parameters"""
        return {
            "host": self.pg_host,
            "port": self.pg_port,
            "database": self.pg_database,
            "user": self.pg_user,
            "password": self.pg_password
        }


class SQLiteManager:
    """SQLite database manager"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.ensure_directory()
    
    def ensure_directory(self):
        """Ensure database directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Get SQLite connection with context manager"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def execute_script(self, script: str):
        """Execute a SQL script"""
        with self.get_connection() as conn:
            conn.executescript(script)
            conn.commit()


class PostgreSQLManager:
    """PostgreSQL database manager"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection_params = config.get_postgres_connection_params()
    
    @contextmanager
    def get_connection(self):
        """Get PostgreSQL connection with context manager"""
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2 is not available")
        
        conn = None
        try:
            conn = psycopg2.connect(**self.connection_params, cursor_factory=RealDictCursor)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def execute_script(self, script: str):
        """Execute a SQL script"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(script)
            conn.commit()
    
    def test_connection(self) -> bool:
        """Test PostgreSQL connection"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logging.error(f"PostgreSQL connection test failed: {e}")
            return False


class DatabaseManager:
    """Unified database manager that works with both SQLite and PostgreSQL"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.sqlite_manager = None
        self.postgres_manager = None
        
        if self.config.db_type.lower() == "sqlite":
            self.sqlite_manager = SQLiteManager(self.config.sqlite_path)
            self.active_manager = self.sqlite_manager
        elif self.config.db_type.lower() == "postgresql":
            self.postgres_manager = PostgreSQLManager(self.config)
            self.active_manager = self.postgres_manager
        else:
            raise ValueError(f"Unsupported database type: {self.config.db_type}")
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query"""
        return self.active_manager.execute_query(query, params)
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query"""
        return self.active_manager.execute_update(query, params)
    
    def execute_script(self, script: str):
        """Execute a SQL script"""
        return self.active_manager.execute_script(script)
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            if isinstance(self.active_manager, PostgreSQLManager):
                return self.active_manager.test_connection()
            else:
                # For SQLite, try a simple query
                self.execute_query("SELECT 1")
                return True
        except Exception as e:
            logging.error(f"Database connection test failed: {e}")
            return False


class MigrationManager:
    """Handles database migrations and schema updates"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.migrations_table = "schema_migrations"
    
    def ensure_migrations_table(self):
        """Ensure the migrations tracking table exists"""
        if self.db_manager.config.db_type.lower() == "sqlite":
            query = f"""
            CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        else:  # PostgreSQL
            query = f"""
            CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        
        self.db_manager.execute_update(query)
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions"""
        try:
            self.ensure_migrations_table()
            results = self.db_manager.execute_query(
                f"SELECT version FROM {self.migrations_table} ORDER BY applied_at"
            )
            return [row['version'] for row in results]
        except Exception as e:
            logging.error(f"Failed to get applied migrations: {e}")
            return []
    
    def apply_migration(self, version: str, sql: str):
        """Apply a migration"""
        try:
            # Execute the migration SQL
            self.db_manager.execute_script(sql)
            
            # Record the migration
            self.db_manager.execute_update(
                f"INSERT INTO {self.migrations_table} (version) VALUES (?)",
                (version,)
            )
            
            logging.info(f"Applied migration {version}")
            
        except Exception as e:
            logging.error(f"Failed to apply migration {version}: {e}")
            raise
    
    def migrate_to_latest(self):
        """Apply all pending migrations"""
        # Define migrations
        migrations = {
            "001_initial_schema": self.get_initial_schema(),
            "002_add_content_table": self.get_content_table_schema(),
            "003_add_fulfillment_table": self.get_fulfillment_table_schema()
        }
        
        applied = self.get_applied_migrations()
        
        for version, sql in migrations.items():
            if version not in applied:
                logging.info(f"Applying migration {version}")
                self.apply_migration(version, sql)
            else:
                logging.debug(f"Migration {version} already applied")
    
    def get_initial_schema(self) -> str:
        """Get the initial database schema"""
        if self.db_manager.config.db_type.lower() == "sqlite":
            return """
            CREATE TABLE IF NOT EXISTS missions (
                id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                target_audience TEXT,
                brand_voice TEXT,
                service_offerings TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                company_name TEXT,
                website_url TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                pain_point TEXT,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mission_id) REFERENCES missions (id)
            );
            
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL,
                subject TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            );
            
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                message_type TEXT DEFAULT 'email',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            );
            """
        else:  # PostgreSQL
            return """
            CREATE TABLE IF NOT EXISTS missions (
                id VARCHAR(255) PRIMARY KEY,
                company_name VARCHAR(255) NOT NULL,
                target_audience TEXT,
                brand_voice TEXT,
                service_offerings TEXT,
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS leads (
                id VARCHAR(255) PRIMARY KEY,
                mission_id VARCHAR(255) NOT NULL,
                company_name VARCHAR(255),
                website_url TEXT,
                contact_email VARCHAR(255),
                contact_phone VARCHAR(50),
                pain_point TEXT,
                status VARCHAR(50) DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mission_id) REFERENCES missions (id)
            );
            
            CREATE TABLE IF NOT EXISTS conversations (
                id VARCHAR(255) PRIMARY KEY,
                lead_id VARCHAR(255) NOT NULL,
                subject TEXT,
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            );
            
            CREATE TABLE IF NOT EXISTS messages (
                id VARCHAR(255) PRIMARY KEY,
                conversation_id VARCHAR(255) NOT NULL,
                sender VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                message_type VARCHAR(50) DEFAULT 'email',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            );
            """
    
    def get_content_table_schema(self) -> str:
        """Get content table schema"""
        if self.db_manager.config.db_type.lower() == "sqlite":
            return """
            CREATE TABLE IF NOT EXISTS content (
                id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content_type TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                scheduled_date TIMESTAMP,
                published_date TIMESTAMP,
                platform TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mission_id) REFERENCES missions (id)
            );
            """
        else:  # PostgreSQL
            return """
            CREATE TABLE IF NOT EXISTS content (
                id VARCHAR(255) PRIMARY KEY,
                mission_id VARCHAR(255) NOT NULL,
                title VARCHAR(500) NOT NULL,
                content_type VARCHAR(100) NOT NULL,
                content TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'draft',
                scheduled_date TIMESTAMP,
                published_date TIMESTAMP,
                platform VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mission_id) REFERENCES missions (id)
            );
            """
    
    def get_fulfillment_table_schema(self) -> str:
        """Get fulfillment projects table schema"""
        if self.db_manager.config.db_type.lower() == "sqlite":
            return """
            CREATE TABLE IF NOT EXISTS fulfillment_projects (
                id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL,
                project_type TEXT NOT NULL,
                description TEXT,
                requirements TEXT,
                status TEXT DEFAULT 'pending',
                assigned_to TEXT,
                deliverable_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            );
            """
        else:  # PostgreSQL
            return """
            CREATE TABLE IF NOT EXISTS fulfillment_projects (
                id VARCHAR(255) PRIMARY KEY,
                lead_id VARCHAR(255) NOT NULL,
                project_type VARCHAR(100) NOT NULL,
                description TEXT,
                requirements TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                assigned_to VARCHAR(255),
                deliverable_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            );
            """


# Convenience functions for Project Chimera
def get_database_manager() -> DatabaseManager:
    """Get configured database manager"""
    return DatabaseManager()


def initialize_database():
    """Initialize database with latest schema"""
    db_manager = get_database_manager()
    migration_manager = MigrationManager(db_manager)
    migration_manager.migrate_to_latest()
    logging.info("Database initialized successfully")
