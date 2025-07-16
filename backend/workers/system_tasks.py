"""
Project Chimera - System Task Handlers
Celery tasks for system-level operations and periodic tasks
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from workers.celery_app import celery_app
from database.db_manager import DatabaseManager
from tools.email_service import EmailService
from utils.logger import ChimeraLogger

logger = ChimeraLogger.get_logger("workers.system_tasks")

@celery_app.task
def email_polling() -> Dict[str, Any]:
    """Periodic task to check for new emails"""
    try:
        logger.info("📧 Starting email polling task")
        result = asyncio.run(_email_polling_async())
        logger.info(f"📧 Email polling completed: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Email polling failed: {e}")
        return {"status": "error", "error": str(e)}

async def _email_polling_async() -> Dict[str, Any]:
    """Async email polling implementation"""
    db_manager = None
    email_service = None
    
    try:
        # Initialize services
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        email_service = EmailService()
        email_initialized = await email_service.initialize()
        
        if not email_initialized:
            return {"status": "skipped", "reason": "Email service not initialized"}
        
        # Get new messages
        new_messages = await email_service.list_new_messages(
            query="is:unread", max_results=20
        )
        
        if not new_messages:
            return {"status": "success", "new_messages": 0}
        
        processed_count = 0
        for message in new_messages:
            try:
                await _process_incoming_email(message, db_manager)
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process email: {e}")
        
        return {
            "status": "success",
            "new_messages": len(new_messages),
            "processed": processed_count
        }
        
    finally:
        if db_manager:
            await db_manager.close()

async def _process_incoming_email(email_data: Dict[str, Any], db_manager: DatabaseManager):
    """Process a single incoming email"""
    from workers.agent_tasks import execute_agent_job
    
    sender_email = _extract_email_from_sender(email_data.get('sender', ''))
    
    # Check if this email is from a known lead
    lead = await db_manager.find_lead_by_email(sender_email)
    
    if lead:
        # Submit job to Closer Agent for processing
        execute_agent_job.delay(
            agent_name="DIPLOMAT",
            job_data={
                "type": "process_reply",
                "email_data": email_data,
                "priority": 3
            }
        )
        logger.info(f"📧 Queued email processing job for lead {lead['id']}")
    else:
        logger.info(f"📧 Received email from unknown sender: {sender_email}")

def _extract_email_from_sender(sender_string: str) -> str:
    """Extract email address from sender string"""
    import re
    email_pattern = r'<([^>]+)>|([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    match = re.search(email_pattern, sender_string)
    
    if match:
        return match.group(1) or match.group(2)
    
    return sender_string.strip()

@celery_app.task
def trigger_outreach_for_new_leads() -> Dict[str, Any]:
    """Periodic task to trigger outreach for new leads"""
    try:
        logger.info("📤 Starting outreach trigger task")
        result = asyncio.run(_trigger_outreach_async())
        logger.info(f"📤 Outreach trigger completed: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Outreach trigger failed: {e}")
        return {"status": "error", "error": str(e)}

async def _trigger_outreach_async() -> Dict[str, Any]:
    """Async outreach trigger implementation"""
    from workers.agent_tasks import execute_agent_job
    
    db_manager = None
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Get all leads with status 'new'
        cursor = await db_manager.connection.execute("""
            SELECT * FROM leads WHERE status = 'new'
        """)
        
        new_leads = await cursor.fetchall()
        triggered_count = 0
        
        for lead_row in new_leads:
            lead = dict(lead_row)
            
            # Submit job to Communicator Agent
            execute_agent_job.delay(
                agent_name="HERALD",
                job_data={
                    "type": "draft_outreach",
                    "lead_id": lead['id'],
                    "priority": 4
                }
            )
            triggered_count += 1
            logger.info(f"📤 Queued outreach for lead {lead['id']}")
        
        return {
            "status": "success",
            "leads_processed": triggered_count
        }
        
    finally:
        if db_manager:
            await db_manager.close()

@celery_app.task
def trigger_fulfillment_for_closed_deals() -> Dict[str, Any]:
    """Periodic task to trigger fulfillment for closed deals"""
    try:
        logger.info("🎯 Starting fulfillment trigger task")
        result = asyncio.run(_trigger_fulfillment_async())
        logger.info(f"🎯 Fulfillment trigger completed: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Fulfillment trigger failed: {e}")
        return {"status": "error", "error": str(e)}

async def _trigger_fulfillment_async() -> Dict[str, Any]:
    """Async fulfillment trigger implementation"""
    from workers.agent_tasks import execute_agent_job
    
    db_manager = None
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Get all leads with status 'deal_closed'
        cursor = await db_manager.connection.execute("""
            SELECT * FROM leads WHERE status = 'deal_closed'
        """)
        
        closed_deals = await cursor.fetchall()
        triggered_count = 0
        
        for lead_row in closed_deals:
            lead = dict(lead_row)
            
            # Check if fulfillment project already exists
            existing_projects = await db_manager.get_fulfillment_projects(lead_id=lead['id'])
            if existing_projects:
                continue  # Skip if already has fulfillment project
            
            # Default to internal fulfillment
            fulfillment_type = "internal"
            
            if fulfillment_type == "internal":
                execute_agent_job.delay(
                    agent_name="ARTIFICER",
                    job_data={
                        "type": "fulfill_internal",
                        "lead_id": lead['id'],
                        "project_requirements": {
                            "deliverable_type": "pdf_report",
                            "urgency": "standard"
                        },
                        "priority": 3
                    }
                )
            else:
                execute_agent_job.delay(
                    agent_name="QUARTERMASTER",
                    job_data={
                        "type": "fulfill_external",
                        "lead_id": lead['id'],
                        "project_requirements": {
                            "project_type": "consulting",
                            "timeline": "2 weeks"
                        },
                        "priority": 3
                    }
                )
            
            triggered_count += 1
            # Update lead status
            await db_manager.update_lead_status(lead['id'], "fulfillment_in_progress")
            logger.info(f"🎯 Queued fulfillment for lead {lead['id']}")
        
        return {
            "status": "success",
            "deals_processed": triggered_count
        }
        
    finally:
        if db_manager:
            await db_manager.close()

@celery_app.task
def system_maintenance() -> Dict[str, Any]:
    """Periodic system maintenance task"""
    try:
        logger.info("🔧 Starting system maintenance")
        result = asyncio.run(_system_maintenance_async())
        logger.info(f"🔧 System maintenance completed: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ System maintenance failed: {e}")
        return {"status": "error", "error": str(e)}

async def _system_maintenance_async() -> Dict[str, Any]:
    """Async system maintenance implementation"""
    db_manager = None
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Clean up old logs (older than 30 days)
        cursor = await db_manager.connection.execute("""
            DELETE FROM agent_activities 
            WHERE created_at < datetime('now', '-30 days')
        """)
        
        deleted_logs = cursor.rowcount
        await db_manager.connection.commit()
        
        return {
            "status": "success",
            "deleted_logs": deleted_logs,
            "timestamp": datetime.now().isoformat()
        }
        
    finally:
        if db_manager:
            await db_manager.close()
