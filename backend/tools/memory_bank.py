"""
Project Chimera - Memory Bank
Vector database for conversation storage and retrieval using ChromaDB
"""

import os
import json
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.config import Settings

from utils.logger import ChimeraLogger

class MemoryBank:
    """Manages conversation memory using ChromaDB vector database"""
    
    def __init__(self, persist_directory: str = "data/memory_bank"):
        self.logger = ChimeraLogger.get_logger(__name__)
        self.persist_directory = persist_directory
        self.client = None
        self.collections = {}
        
    async def initialize(self):
        """Initialize ChromaDB client and setup"""
        try:
            # Create persist directory
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Initialize ChromaDB client with persistence
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            self.logger.info("✅ Memory Bank initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Memory Bank: {e}")
            raise
    
    async def create_lead_collection(self, lead_id: int) -> bool:
        """Create a new collection for a lead's conversation history"""
        try:
            collection_name = f"lead_{lead_id}_conversations"
            
            # Check if collection already exists
            if collection_name in self.collections:
                self.logger.info(f"📚 Collection for lead {lead_id} already exists")
                return True
            
            # Create new collection
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"lead_id": lead_id, "created_at": datetime.now().isoformat()}
            )
            
            self.collections[collection_name] = collection
            self.logger.info(f"📚 Created conversation collection for lead {lead_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create collection for lead {lead_id}: {e}")
            return False
    
    async def get_lead_collection(self, lead_id: int):
        """Get or create collection for a lead"""
        collection_name = f"lead_{lead_id}_conversations"
        
        if collection_name not in self.collections:
            try:
                # Try to get existing collection
                collection = self.client.get_collection(collection_name)
                self.collections[collection_name] = collection
            except Exception:
                # Create new collection if it doesn't exist
                await self.create_lead_collection(lead_id)
                collection = self.collections[collection_name]
        
        return self.collections[collection_name]
    
    async def store_message(self, lead_id: int, message_data: Dict[str, Any]) -> str:
        """Store a message in the lead's conversation collection"""
        try:
            collection = await self.get_lead_collection(lead_id)
            
            # Generate unique ID for this message
            message_id = str(uuid.uuid4())
            
            # Prepare message content for embedding
            content = self._prepare_message_content(message_data)
            
            # Prepare metadata
            metadata = {
                "lead_id": lead_id,
                "message_type": message_data.get("type", "unknown"),  # incoming/outgoing
                "sender": message_data.get("sender", ""),
                "subject": message_data.get("subject", ""),
                "timestamp": message_data.get("timestamp", datetime.now().isoformat()),
                "email_id": message_data.get("email_id", ""),
                "thread_id": message_data.get("thread_id", "")
            }
            
            # Add to collection
            collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[message_id]
            )
            
            self.logger.info(f"💾 Stored message {message_id} for lead {lead_id}")
            return message_id
            
        except Exception as e:
            self.logger.error(f"❌ Failed to store message for lead {lead_id}: {e}")
            return ""
    
    async def retrieve_conversation_history(self, lead_id: int, 
                                          query: Optional[str] = None,
                                          limit: int = 10) -> List[Dict]:
        """Retrieve conversation history for a lead"""
        try:
            collection = await self.get_lead_collection(lead_id)
            
            if query:
                # Semantic search based on query
                results = collection.query(
                    query_texts=[query],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"]
                )
            else:
                # Get all messages, sorted by timestamp
                results = collection.get(
                    include=["documents", "metadatas"],
                    limit=limit
                )
            
            # Format results
            messages = []
            if query and results['documents']:
                # Query results format
                for i, doc in enumerate(results['documents'][0]):
                    messages.append({
                        "content": doc,
                        "metadata": results['metadatas'][0][i],
                        "relevance_score": 1 - results['distances'][0][i] if 'distances' in results else 1.0
                    })
            elif not query and results['documents']:
                # Get all results format
                for i, doc in enumerate(results['documents']):
                    messages.append({
                        "content": doc,
                        "metadata": results['metadatas'][i],
                        "relevance_score": 1.0
                    })
            
            # Sort by timestamp if no query (chronological order)
            if not query:
                messages.sort(key=lambda x: x['metadata'].get('timestamp', ''))
            
            self.logger.info(f"🔍 Retrieved {len(messages)} messages for lead {lead_id}")
            return messages
            
        except Exception as e:
            self.logger.error(f"❌ Failed to retrieve conversation history for lead {lead_id}: {e}")
            return []
    
    async def search_conversations(self, lead_id: int, query: str, limit: int = 5) -> List[Dict]:
        """Search conversations for specific content"""
        try:
            collection = await self.get_lead_collection(lead_id)
            
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            search_results = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    search_results.append({
                        "content": doc,
                        "metadata": results['metadatas'][0][i],
                        "relevance_score": 1 - results['distances'][0][i]
                    })
            
            self.logger.info(f"🔍 Found {len(search_results)} relevant messages for query: {query}")
            return search_results
            
        except Exception as e:
            self.logger.error(f"❌ Failed to search conversations for lead {lead_id}: {e}")
            return []
    
    async def get_conversation_summary(self, lead_id: int) -> Dict[str, Any]:
        """Get summary statistics for a lead's conversation"""
        try:
            collection = await self.get_lead_collection(lead_id)
            
            # Get all messages
            results = collection.get(include=["metadatas"])
            
            if not results['metadatas']:
                return {
                    "total_messages": 0,
                    "incoming_messages": 0,
                    "outgoing_messages": 0,
                    "first_contact": None,
                    "last_activity": None
                }
            
            # Analyze metadata
            total_messages = len(results['metadatas'])
            incoming_count = sum(1 for m in results['metadatas'] if m.get('message_type') == 'incoming')
            outgoing_count = sum(1 for m in results['metadatas'] if m.get('message_type') == 'outgoing')
            
            # Get timestamps
            timestamps = [m.get('timestamp') for m in results['metadatas'] if m.get('timestamp')]
            timestamps.sort()
            
            summary = {
                "total_messages": total_messages,
                "incoming_messages": incoming_count,
                "outgoing_messages": outgoing_count,
                "first_contact": timestamps[0] if timestamps else None,
                "last_activity": timestamps[-1] if timestamps else None
            }
            
            self.logger.info(f"📊 Generated conversation summary for lead {lead_id}")
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get conversation summary for lead {lead_id}: {e}")
            return {}
    
    def _prepare_message_content(self, message_data: Dict[str, Any]) -> str:
        """Prepare message content for embedding"""
        content_parts = []
        
        # Add subject if available
        if message_data.get("subject"):
            content_parts.append(f"Subject: {message_data['subject']}")
        
        # Add sender information
        if message_data.get("sender"):
            content_parts.append(f"From: {message_data['sender']}")
        
        # Add main body content
        if message_data.get("body"):
            content_parts.append(f"Content: {message_data['body']}")
        
        # Add any additional context
        if message_data.get("context"):
            content_parts.append(f"Context: {message_data['context']}")
        
        return "\n".join(content_parts)
    
    async def delete_lead_collection(self, lead_id: int) -> bool:
        """Delete all conversation data for a lead"""
        try:
            collection_name = f"lead_{lead_id}_conversations"
            
            # Remove from client
            self.client.delete_collection(collection_name)
            
            # Remove from local cache
            if collection_name in self.collections:
                del self.collections[collection_name]
            
            self.logger.info(f"🗑️ Deleted conversation collection for lead {lead_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to delete collection for lead {lead_id}: {e}")
            return False
    
    async def list_all_collections(self) -> List[Dict[str, Any]]:
        """List all conversation collections"""
        try:
            collections = self.client.list_collections()
            
            collection_info = []
            for collection in collections:
                # Extract lead_id from collection name
                if collection.name.startswith("lead_") and "_conversations" in collection.name:
                    lead_id = collection.name.split("_")[1]
                    
                    # Get collection stats
                    count = collection.count()
                    
                    collection_info.append({
                        "lead_id": int(lead_id),
                        "collection_name": collection.name,
                        "message_count": count,
                        "metadata": collection.metadata
                    })
            
            self.logger.info(f"📋 Found {len(collection_info)} conversation collections")
            return collection_info
            
        except Exception as e:
            self.logger.error(f"❌ Failed to list collections: {e}")
            return []
