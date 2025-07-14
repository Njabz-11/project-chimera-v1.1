"""
Project Chimera - Database Manager
SQLite database management for the Autonomous Business Operations Platform
"""

import sqlite3
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import aiosqlite

class DatabaseManager:
    """Manages SQLite database operations for Project Chimera"""
    
    def __init__(self, db_path: str = "data/chimera_local.db"):
        self.db_path = db_path
        self.db_dir = Path(db_path).parent
        self.connection: Optional[aiosqlite.Connection] = None
        
    async def initialize(self):
        """Initialize database and create tables"""
        # Create data directory if it doesn't exist
        self.db_dir.mkdir(exist_ok=True)
        
        # Connect to database
        self.connection = await aiosqlite.connect(self.db_path)

        # Enable foreign keys and row factory
        await self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.row_factory = aiosqlite.Row
        
        # Create tables
        await self._create_tables()
        await self.connection.commit()
        
    async def _create_tables(self):
        """Create all necessary tables"""

        # Users table for authentication
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT,
                hashed_password TEXT NOT NULL,
                role TEXT DEFAULT 'client',
                status TEXT DEFAULT 'active',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                last_login TIMESTAMP,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP
            )
        """)

        # API Keys table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                key_hash TEXT NOT NULL,
                key_preview TEXT NOT NULL,
                scopes TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                last_used TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # Sessions table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # Tenants table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                domain TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'trial',
                plan TEXT DEFAULT 'trial',
                max_users INTEGER DEFAULT 5,
                max_missions INTEGER DEFAULT 10,
                max_leads INTEGER DEFAULT 1000,
                settings TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                expires_at TIMESTAMP,
                last_activity TIMESTAMP
            )
        """)

        # Tenant usage tracking
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS tenant_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                users_count INTEGER DEFAULT 0,
                missions_count INTEGER DEFAULT 0,
                leads_count INTEGER DEFAULT 0,
                conversations_count INTEGER DEFAULT 0,
                api_calls_count INTEGER DEFAULT 0,
                storage_used_mb REAL DEFAULT 0.0,
                bandwidth_used_mb REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
            )
        """)

        # Update users table to include tenant_id
        await self.connection.execute("""
            ALTER TABLE users ADD COLUMN tenant_id INTEGER REFERENCES tenants(id)
        """)

        # Mission Briefings table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS mission_briefings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_goal TEXT NOT NULL,
                target_audience TEXT NOT NULL,
                brand_voice TEXT NOT NULL,
                service_offerings TEXT NOT NULL,
                contact_info TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                tenant_id INTEGER NOT NULL,
                created_by INTEGER,
                created_by_username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Leads table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id INTEGER,
                company_name TEXT NOT NULL,
                website_url TEXT,
                contact_email TEXT,
                contact_name TEXT,
                phone_number TEXT,
                industry TEXT,
                company_size TEXT,
                pain_points TEXT,
                lead_source TEXT,
                qualification_score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'new',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mission_id) REFERENCES mission_briefings (id)
            )
        """)
        
        # Agent Activities table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS agent_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                execution_time_ms INTEGER,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Conversations table for email tracking
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                email_id TEXT,
                thread_id TEXT,
                subject TEXT,
                sender_email TEXT,
                recipient_email TEXT,
                message_type TEXT NOT NULL, -- 'incoming' or 'outgoing'
                body_preview TEXT,
                full_body TEXT,
                status TEXT DEFAULT 'unread', -- 'unread', 'read', 'replied', 'draft'
                draft_id TEXT,
                sent_at TIMESTAMP,
                received_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            )
        """)

        # Content table for content calendar and generated content
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id INTEGER,
                title TEXT NOT NULL,
                content_type TEXT NOT NULL, -- 'blog_post', 'social_media', 'video_script', 'email_newsletter'
                topic TEXT NOT NULL,
                target_audience TEXT,
                content_body TEXT,
                meta_description TEXT,
                tags TEXT, -- JSON array of tags
                status TEXT DEFAULT 'draft', -- 'draft', 'approved', 'published', 'scheduled'
                scheduled_date TIMESTAMP,
                published_date TIMESTAMP,
                platform TEXT, -- 'linkedin', 'twitter', 'blog', 'facebook', etc.
                engagement_metrics TEXT, -- JSON object for likes, shares, comments
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mission_id) REFERENCES mission_briefings (id)
            )
        """)

        # Fulfillment projects table for tracking deliverables
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS fulfillment_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                mission_id INTEGER,
                project_type TEXT NOT NULL, -- 'internal', 'external'
                project_title TEXT NOT NULL,
                project_description TEXT,
                requirements TEXT, -- JSON object with detailed requirements
                deliverable_type TEXT, -- 'pdf_report', 'python_script', 'marketing_plan', 'freelancer_brief'
                deliverable_path TEXT, -- File path to generated deliverable
                freelancer_brief TEXT, -- Generated job posting for external projects
                status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'delivered'
                estimated_completion TIMESTAMP,
                actual_completion TIMESTAMP,
                quality_score INTEGER, -- 1-10 rating
                client_feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id),
                FOREIGN KEY (mission_id) REFERENCES mission_briefings (id)
            )
        """)
        
    async def create_mission(self, briefing_data: Dict[str, Any]) -> int:
        """Create a new mission briefing"""
        cursor = await self.connection.execute("""
            INSERT INTO mission_briefings 
            (business_goal, target_audience, brand_voice, service_offerings, contact_info)
            VALUES (?, ?, ?, ?, ?)
        """, (
            briefing_data["business_goal"],
            briefing_data["target_audience"],
            briefing_data["brand_voice"],
            json.dumps(briefing_data["service_offerings"]),
            json.dumps(briefing_data["contact_info"])
        ))
        await self.connection.commit()
        return cursor.lastrowid
    
    async def get_all_missions(self) -> List[Dict[str, Any]]:
        """Get all mission briefings"""
        cursor = await self.connection.execute("""
            SELECT * FROM mission_briefings ORDER BY created_at DESC
        """)
        rows = await cursor.fetchall()
        
        missions = []
        for row in rows:
            mission = dict(row)
            mission["service_offerings"] = json.loads(mission["service_offerings"])
            mission["contact_info"] = json.loads(mission["contact_info"])
            missions.append(mission)
        
        return missions
    
    async def create_lead(self, lead_data: Dict[str, Any]) -> int:
        """Create a new lead"""
        cursor = await self.connection.execute("""
            INSERT INTO leads 
            (mission_id, company_name, website_url, contact_email, contact_name, 
             phone_number, industry, company_size, pain_points, lead_source, 
             qualification_score, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead_data.get("mission_id"),
            lead_data["company_name"],
            lead_data.get("website_url"),
            lead_data.get("contact_email"),
            lead_data.get("contact_name"),
            lead_data.get("phone_number"),
            lead_data.get("industry"),
            lead_data.get("company_size"),
            json.dumps(lead_data.get("pain_points", [])),
            lead_data.get("lead_source"),
            lead_data.get("qualification_score", 0),
            lead_data.get("status", "new"),
            lead_data.get("notes")
        ))
        await self.connection.commit()
        return cursor.lastrowid
    
    async def get_all_leads(self) -> List[Dict[str, Any]]:
        """Get all leads"""
        cursor = await self.connection.execute("""
            SELECT l.*, m.business_goal 
            FROM leads l 
            LEFT JOIN mission_briefings m ON l.mission_id = m.id 
            ORDER BY l.created_at DESC
        """)
        rows = await cursor.fetchall()
        
        leads = []
        for row in rows:
            lead = dict(row)
            lead["pain_points"] = json.loads(lead["pain_points"]) if lead["pain_points"] else []
            leads.append(lead)
        
        return leads

    async def get_lead_by_id(self, lead_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific lead by ID"""
        cursor = await self.connection.execute("""
            SELECT * FROM leads WHERE id = ?
        """, (lead_id,))

        row = await cursor.fetchone()
        if row:
            lead = dict(row)
            # Parse JSON fields
            lead["pain_points"] = json.loads(lead["pain_points"]) if lead["pain_points"] else []
            return lead
        return None

    async def get_mission_by_id(self, mission_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific mission by ID"""
        cursor = await self.connection.execute("""
            SELECT * FROM mission_briefings WHERE id = ?
        """, (mission_id,))

        row = await cursor.fetchone()
        return dict(row) if row else None

    async def update_lead_status(self, lead_id: int, status: str, notes: str = None):
        """Update lead status"""
        if notes:
            await self.connection.execute("""
                UPDATE leads SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (status, notes, lead_id))
        else:
            await self.connection.execute("""
                UPDATE leads SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (status, lead_id))
        await self.connection.commit()
    
    async def log_agent_activity(self, agent_name: str, activity_type: str, description: str, 
                                status: str, input_data: Dict = None, output_data: Dict = None,
                                execution_time_ms: int = None, error_message: str = None):
        """Log agent activity"""
        await self.connection.execute("""
            INSERT INTO agent_activities 
            (agent_name, activity_type, description, status, input_data, output_data, 
             execution_time_ms, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_name,
            activity_type,
            description,
            status,
            json.dumps(input_data) if input_data else None,
            json.dumps(output_data) if output_data else None,
            execution_time_ms,
            error_message
        ))
        await self.connection.commit()
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        stats = {}
        
        # Total leads
        cursor = await self.connection.execute("SELECT COUNT(*) FROM leads")
        stats["total_leads"] = (await cursor.fetchone())[0]
        
        # Active missions
        cursor = await self.connection.execute("SELECT COUNT(*) FROM mission_briefings WHERE status = 'active'")
        stats["active_missions"] = (await cursor.fetchone())[0]
        
        # System uptime (placeholder)
        stats["uptime"] = "Running"
        
        return stats
    
    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            self.connection = None

    # Conversation Management Methods
    async def create_conversation(self, conversation_data: Dict[str, Any]) -> int:
        """Create a new conversation record"""
        cursor = await self.connection.execute("""
            INSERT INTO conversations
            (lead_id, email_id, thread_id, subject, sender_email, recipient_email,
             message_type, body_preview, full_body, status, draft_id, sent_at, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conversation_data.get('lead_id'),
            conversation_data.get('email_id'),
            conversation_data.get('thread_id'),
            conversation_data.get('subject'),
            conversation_data.get('sender_email'),
            conversation_data.get('recipient_email'),
            conversation_data.get('message_type'),
            conversation_data.get('body_preview'),
            conversation_data.get('full_body'),
            conversation_data.get('status', 'unread'),
            conversation_data.get('draft_id'),
            conversation_data.get('sent_at'),
            conversation_data.get('received_at')
        ))

        await self.connection.commit()
        return cursor.lastrowid

    async def get_conversations_by_lead(self, lead_id: int) -> List[Dict[str, Any]]:
        """Get all conversations for a specific lead"""
        cursor = await self.connection.execute("""
            SELECT * FROM conversations
            WHERE lead_id = ?
            ORDER BY created_at ASC
        """, (lead_id,))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def update_conversation_status(self, conversation_id: int, status: str) -> bool:
        """Update conversation status"""
        cursor = await self.connection.execute("""
            UPDATE conversations
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, conversation_id))

        await self.connection.commit()
        return cursor.rowcount > 0

    async def get_unread_conversations(self) -> List[Dict[str, Any]]:
        """Get all unread conversations"""
        cursor = await self.connection.execute("""
            SELECT c.*, l.company_name, l.contact_email
            FROM conversations c
            JOIN leads l ON c.lead_id = l.id
            WHERE c.status = 'unread' AND c.message_type = 'incoming'
            ORDER BY c.received_at DESC
        """)

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def find_lead_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find lead by email address"""
        cursor = await self.connection.execute("""
            SELECT * FROM leads WHERE contact_email = ?
        """, (email,))

        row = await cursor.fetchone()
        return dict(row) if row else None

    # Content Management Methods
    async def create_content(self, content_data: Dict[str, Any]) -> int:
        """Create a new content item"""
        cursor = await self.connection.execute("""
            INSERT INTO content
            (mission_id, title, content_type, topic, target_audience, content_body,
             meta_description, tags, status, scheduled_date, platform)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            content_data.get("mission_id"),
            content_data["title"],
            content_data["content_type"],
            content_data["topic"],
            content_data.get("target_audience"),
            content_data.get("content_body"),
            content_data.get("meta_description"),
            json.dumps(content_data.get("tags", [])),
            content_data.get("status", "draft"),
            content_data.get("scheduled_date"),
            content_data.get("platform")
        ))
        await self.connection.commit()
        return cursor.lastrowid

    async def get_content_calendar(self, mission_id: int = None, status: str = None) -> List[Dict[str, Any]]:
        """Get content calendar items"""
        query = "SELECT * FROM content WHERE 1=1"
        params = []

        if mission_id:
            query += " AND mission_id = ?"
            params.append(mission_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY scheduled_date ASC, created_at DESC"

        cursor = await self.connection.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def update_content_status(self, content_id: int, status: str, published_date: str = None) -> bool:
        """Update content status and optionally set published date"""
        try:
            update_query = "UPDATE content SET status = ?, updated_at = CURRENT_TIMESTAMP"
            params = [status]

            if published_date:
                update_query += ", published_date = ?"
                params.append(published_date)

            update_query += " WHERE id = ?"
            params.append(content_id)

            await self.connection.execute(update_query, params)
            await self.connection.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to update content status: {e}")
            return False

    # Fulfillment Project Methods
    async def create_fulfillment_project(self, project_data: Dict[str, Any]) -> int:
        """Create a new fulfillment project"""
        cursor = await self.connection.execute("""
            INSERT INTO fulfillment_projects
            (lead_id, mission_id, project_type, project_title, project_description,
             requirements, deliverable_type, freelancer_brief, status, estimated_completion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_data["lead_id"],
            project_data.get("mission_id"),
            project_data["project_type"],
            project_data["project_title"],
            project_data.get("project_description"),
            json.dumps(project_data.get("requirements", {})),
            project_data.get("deliverable_type"),
            project_data.get("freelancer_brief"),
            project_data.get("status", "pending"),
            project_data.get("estimated_completion")
        ))
        await self.connection.commit()
        return cursor.lastrowid

    async def get_fulfillment_projects(self, lead_id: int = None, status: str = None) -> List[Dict[str, Any]]:
        """Get fulfillment projects"""
        query = """
            SELECT fp.*, l.company_name, l.contact_name, m.business_goal
            FROM fulfillment_projects fp
            LEFT JOIN leads l ON fp.lead_id = l.id
            LEFT JOIN mission_briefings m ON fp.mission_id = m.id
            WHERE 1=1
        """
        params = []

        if lead_id:
            query += " AND fp.lead_id = ?"
            params.append(lead_id)

        if status:
            query += " AND fp.status = ?"
            params.append(status)

        query += " ORDER BY fp.created_at DESC"

        cursor = await self.connection.execute(query, params)
        rows = await cursor.fetchall()

        projects = []
        for row in rows:
            project = dict(row)
            project["requirements"] = json.loads(project["requirements"]) if project["requirements"] else {}
            projects.append(project)

        return projects

    async def update_fulfillment_project(self, project_id: int, update_data: Dict[str, Any]) -> bool:
        """Update fulfillment project"""
        try:
            set_clauses = []
            params = []

            for field, value in update_data.items():
                if field in ['status', 'deliverable_path', 'actual_completion', 'quality_score', 'client_feedback']:
                    set_clauses.append(f"{field} = ?")
                    params.append(value)

            if not set_clauses:
                return False

            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            params.append(project_id)

            query = f"UPDATE fulfillment_projects SET {', '.join(set_clauses)} WHERE id = ?"

            await self.connection.execute(query, params)
            await self.connection.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to update fulfillment project: {e}")
            return False

    # =============================================================================
    # USER MANAGEMENT METHODS
    # =============================================================================

    async def create_user(self, user_data: Dict[str, Any]) -> int:
        """Create a new user"""
        try:
            cursor = await self.connection.execute("""
                INSERT INTO users (
                    username, email, full_name, hashed_password, role, status, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_data["username"],
                user_data["email"],
                user_data.get("full_name"),
                user_data["hashed_password"],
                user_data.get("role", "client"),
                user_data.get("status", "active"),
                user_data.get("is_active", True)
            ))
            await self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Failed to create user: {e}")
            raise

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Failed to get user by ID: {e}")
            return None

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Failed to get user by username: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Failed to get user by email: {e}")
            return None

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all users with pagination"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, skip)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get all users: {e}")
            return []

    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user information"""
        try:
            set_clauses = []
            params = []

            for field, value in update_data.items():
                if field in ["email", "full_name", "role", "status", "is_active"]:
                    set_clauses.append(f"{field} = ?")
                    params.append(value)

            if set_clauses:
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                params.append(user_id)

                query = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?"
                await self.connection.execute(query, params)
                await self.connection.commit()

            return await self.get_user_by_id(user_id)
        except Exception as e:
            self.logger.error(f"Failed to update user: {e}")
            raise

    async def update_user_password(self, user_id: int, hashed_password: str):
        """Update user password"""
        try:
            await self.connection.execute(
                "UPDATE users SET hashed_password = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (hashed_password, user_id)
            )
            await self.connection.commit()
        except Exception as e:
            self.logger.error(f"Failed to update user password: {e}")
            raise

    async def increment_failed_login_attempts(self, user_id: int):
        """Increment failed login attempts"""
        try:
            await self.connection.execute("""
                UPDATE users
                SET failed_login_attempts = failed_login_attempts + 1,
                    locked_until = CASE
                        WHEN failed_login_attempts >= 4 THEN datetime('now', '+15 minutes')
                        ELSE locked_until
                    END
                WHERE id = ?
            """, (user_id,))
            await self.connection.commit()
        except Exception as e:
            self.logger.error(f"Failed to increment failed login attempts: {e}")

    async def reset_failed_login_attempts(self, user_id: int):
        """Reset failed login attempts"""
        try:
            await self.connection.execute(
                "UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = ?",
                (user_id,)
            )
            await self.connection.commit()
        except Exception as e:
            self.logger.error(f"Failed to reset failed login attempts: {e}")

    async def update_last_login(self, user_id: int):
        """Update last login timestamp"""
        try:
            await self.connection.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,)
            )
            await self.connection.commit()
        except Exception as e:
            self.logger.error(f"Failed to update last login: {e}")

    async def get_missions_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Get missions created by a specific user"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM mission_briefings WHERE created_by = ? ORDER BY created_at DESC",
                (user_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get missions by user: {e}")
            return []

    async def get_leads_by_user(self, user_id: int, mission_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get leads for missions created by a specific user"""
        try:
            if mission_id:
                # Check if user owns this mission
                mission = await self.get_mission_by_id(mission_id)
                if not mission or mission.get("created_by") != user_id:
                    return []

                cursor = await self.connection.execute(
                    "SELECT * FROM leads WHERE mission_id = ? ORDER BY created_at DESC",
                    (mission_id,)
                )
            else:
                # Get all leads for user's missions
                cursor = await self.connection.execute("""
                    SELECT l.* FROM leads l
                    JOIN mission_briefings m ON l.mission_id = m.id
                    WHERE m.created_by = ?
                    ORDER BY l.created_at DESC
                """, (user_id,))

            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get leads by user: {e}")
            return []

    # =============================================================================
    # TENANT MANAGEMENT METHODS
    # =============================================================================

    async def create_tenant(self, tenant_data: Dict[str, Any]) -> int:
        """Create a new tenant"""
        try:
            cursor = await self.connection.execute("""
                INSERT INTO tenants (
                    name, domain, status, plan, max_users, max_missions, max_leads,
                    settings, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tenant_data["name"],
                tenant_data["domain"],
                tenant_data.get("status", "trial"),
                tenant_data.get("plan", "trial"),
                tenant_data.get("max_users", 5),
                tenant_data.get("max_missions", 10),
                tenant_data.get("max_leads", 1000),
                tenant_data.get("settings", "{}"),
                tenant_data.get("created_at"),
                tenant_data.get("expires_at")
            ))
            await self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Failed to create tenant: {e}")
            raise

    async def get_tenant_by_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Get tenant by ID"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM tenants WHERE id = ?", (tenant_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Failed to get tenant by ID: {e}")
            return None

    async def get_tenant_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get tenant by domain"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM tenants WHERE domain = ?", (domain.lower(),)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Failed to get tenant by domain: {e}")
            return None

    async def update_tenant(self, tenant_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update tenant information"""
        try:
            set_clauses = []
            params = []

            for field, value in update_data.items():
                if field in ["name", "status", "plan", "max_users", "max_missions", "max_leads", "settings"]:
                    set_clauses.append(f"{field} = ?")
                    params.append(value)

            if set_clauses:
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                params.append(tenant_id)

                query = f"UPDATE tenants SET {', '.join(set_clauses)} WHERE id = ?"
                await self.connection.execute(query, params)
                await self.connection.commit()

            return await self.get_tenant_by_id(tenant_id)
        except Exception as e:
            self.logger.error(f"Failed to update tenant: {e}")
            raise

    async def get_all_tenants(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all tenants with pagination"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM tenants ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, skip)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get all tenants: {e}")
            return []

    async def update_tenant_usage(self, tenant_id: int, usage_data: Dict[str, Any]):
        """Update tenant usage statistics"""
        try:
            await self.connection.execute("""
                INSERT OR REPLACE INTO tenant_usage (
                    tenant_id, users_count, missions_count, leads_count,
                    conversations_count, api_calls_count, storage_used_mb,
                    bandwidth_used_mb, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                tenant_id,
                usage_data.get("users_count", 0),
                usage_data.get("missions_count", 0),
                usage_data.get("leads_count", 0),
                usage_data.get("conversations_count", 0),
                usage_data.get("api_calls_count", 0),
                usage_data.get("storage_used_mb", 0.0),
                usage_data.get("bandwidth_used_mb", 0.0)
            ))
            await self.connection.commit()
        except Exception as e:
            self.logger.error(f"Failed to update tenant usage: {e}")

    async def get_tenant_usage(self, tenant_id: int) -> Dict[str, Any]:
        """Get tenant usage statistics"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM tenant_usage WHERE tenant_id = ?", (tenant_id,)
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            else:
                # Return default usage if not found
                return {
                    "tenant_id": tenant_id,
                    "users_count": 0,
                    "missions_count": 0,
                    "leads_count": 0,
                    "conversations_count": 0,
                    "api_calls_count": 0,
                    "storage_used_mb": 0.0,
                    "bandwidth_used_mb": 0.0,
                    "last_updated": None
                }
        except Exception as e:
            self.logger.error(f"Failed to get tenant usage: {e}")
            return {
                "tenant_id": tenant_id,
                "users_count": 0,
                "missions_count": 0,
                "leads_count": 0,
                "conversations_count": 0,
                "api_calls_count": 0,
                "storage_used_mb": 0.0,
                "bandwidth_used_mb": 0.0,
                "last_updated": None
            }
