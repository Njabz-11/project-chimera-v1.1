"""
Vector Database Infrastructure for Project Chimera
Supports both ChromaDB and LanceDB for vector storage and retrieval
"""

import os
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

# Vector database imports
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("ChromaDB not available")

try:
    import lancedb
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False
    logging.warning("LanceDB not available")

# Embedding imports
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("SentenceTransformers not available")


class VectorDBInterface(ABC):
    """Abstract interface for vector database operations"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the vector database"""
        pass
    
    @abstractmethod
    def create_collection(self, name: str) -> bool:
        """Create a new collection"""
        pass
    
    @abstractmethod
    def add_documents(self, collection_name: str, documents: List[str], 
                     metadata: List[Dict[str, Any]] = None) -> bool:
        """Add documents to a collection"""
        pass
    
    @abstractmethod
    def search(self, collection_name: str, query: str, 
               limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        pass
    
    @abstractmethod
    def delete_collection(self, name: str) -> bool:
        """Delete a collection"""
        pass


class ChromaDBManager(VectorDBInterface):
    """ChromaDB implementation for vector storage"""
    
    def __init__(self, persist_directory: str = "./data/chromadb"):
        self.persist_directory = persist_directory
        self.client = None
        self.embedding_model = None
        
    def initialize(self) -> bool:
        """Initialize ChromaDB client"""
        if not CHROMADB_AVAILABLE:
            logging.error("ChromaDB is not available")
            return False
            
        try:
            # Create persist directory if it doesn't exist
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Initialize embedding model (lightweight default)
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            logging.info(f"ChromaDB initialized at {self.persist_directory}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize ChromaDB: {e}")
            return False
    
    def create_collection(self, name: str) -> bool:
        """Create a new ChromaDB collection"""
        try:
            if self.client is None:
                return False
                
            # Delete existing collection if it exists
            try:
                self.client.delete_collection(name)
            except:
                pass  # Collection doesn't exist
                
            # Create new collection
            collection = self.client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
            
            logging.info(f"ChromaDB collection '{name}' created")
            return True
            
        except Exception as e:
            logging.error(f"Failed to create ChromaDB collection '{name}': {e}")
            return False
    
    def add_documents(self, collection_name: str, documents: List[str], 
                     metadata: List[Dict[str, Any]] = None) -> bool:
        """Add documents to ChromaDB collection"""
        try:
            if self.client is None:
                return False
                
            collection = self.client.get_collection(collection_name)
            
            # Generate embeddings if model is available
            embeddings = None
            if self.embedding_model:
                embeddings = self.embedding_model.encode(documents).tolist()
            
            # Prepare IDs
            ids = [f"doc_{i}" for i in range(len(documents))]
            
            # Add documents
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadata or [{}] * len(documents),
                ids=ids
            )
            
            logging.info(f"Added {len(documents)} documents to ChromaDB collection '{collection_name}'")
            return True
            
        except Exception as e:
            logging.error(f"Failed to add documents to ChromaDB collection '{collection_name}': {e}")
            return False
    
    def search(self, collection_name: str, query: str, 
               limit: int = 10) -> List[Dict[str, Any]]:
        """Search ChromaDB collection"""
        try:
            if self.client is None:
                return []
                
            collection = self.client.get_collection(collection_name)
            
            # Generate query embedding if model is available
            query_embedding = None
            if self.embedding_model:
                query_embedding = self.embedding_model.encode([query]).tolist()
            
            # Search
            results = collection.query(
                query_embeddings=query_embedding,
                query_texts=[query] if query_embedding is None else None,
                n_results=limit
            )
            
            # Format results
            formatted_results = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'document': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0.0
                    })
            
            return formatted_results
            
        except Exception as e:
            logging.error(f"Failed to search ChromaDB collection '{collection_name}': {e}")
            return []
    
    def delete_collection(self, name: str) -> bool:
        """Delete ChromaDB collection"""
        try:
            if self.client is None:
                return False
                
            self.client.delete_collection(name)
            logging.info(f"ChromaDB collection '{name}' deleted")
            return True
            
        except Exception as e:
            logging.error(f"Failed to delete ChromaDB collection '{name}': {e}")
            return False


class LanceDBManager(VectorDBInterface):
    """LanceDB implementation for vector storage"""
    
    def __init__(self, db_path: str = "./data/lancedb"):
        self.db_path = db_path
        self.db = None
        self.embedding_model = None
        
    def initialize(self) -> bool:
        """Initialize LanceDB"""
        if not LANCEDB_AVAILABLE:
            logging.error("LanceDB is not available")
            return False
            
        try:
            # Create database directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Initialize LanceDB
            self.db = lancedb.connect(self.db_path)
            
            # Initialize embedding model (lightweight default)
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            logging.info(f"LanceDB initialized at {self.db_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize LanceDB: {e}")
            return False
    
    def create_collection(self, name: str) -> bool:
        """Create a new LanceDB table"""
        try:
            if self.db is None:
                return False
                
            # Delete existing table if it exists
            try:
                self.db.drop_table(name)
            except:
                pass  # Table doesn't exist
                
            # Create sample data structure for table creation
            sample_data = [{
                "id": "sample",
                "document": "sample document",
                "vector": [0.0] * 384,  # Default embedding size for all-MiniLM-L6-v2
                "conversation_id": "sample",
                "lead_id": "sample",
                "type": "sample",
                "timestamp": "2024-01-01"
            }]
            
            # Create table
            table = self.db.create_table(name, sample_data)
            
            # Remove sample data
            table.delete("id = 'sample'")
            
            logging.info(f"LanceDB table '{name}' created")
            return True
            
        except Exception as e:
            logging.error(f"Failed to create LanceDB table '{name}': {e}")
            return False
    
    def add_documents(self, collection_name: str, documents: List[str], 
                     metadata: List[Dict[str, Any]] = None) -> bool:
        """Add documents to LanceDB table"""
        try:
            if self.db is None:
                return False
                
            table = self.db.open_table(collection_name)
            
            # Generate embeddings if model is available
            embeddings = []
            if self.embedding_model:
                embeddings = self.embedding_model.encode(documents).tolist()
            else:
                # Use zero vectors if no embedding model
                embeddings = [[0.0] * 384 for _ in documents]
            
            # Prepare data
            data = []
            for i, doc in enumerate(documents):
                meta = metadata[i] if metadata else {}
                data.append({
                    "id": f"doc_{i}",
                    "document": doc,
                    "vector": embeddings[i],
                    "conversation_id": meta.get("conversation_id", ""),
                    "lead_id": meta.get("lead_id", ""),
                    "type": meta.get("type", ""),
                    "timestamp": meta.get("timestamp", "")
                })
            
            # Add documents
            table.add(data)
            
            logging.info(f"Added {len(documents)} documents to LanceDB table '{collection_name}'")
            return True
            
        except Exception as e:
            logging.error(f"Failed to add documents to LanceDB table '{collection_name}': {e}")
            return False
    
    def search(self, collection_name: str, query: str, 
               limit: int = 10) -> List[Dict[str, Any]]:
        """Search LanceDB table"""
        try:
            if self.db is None:
                return []
                
            table = self.db.open_table(collection_name)
            
            # Generate query embedding if model is available
            if self.embedding_model:
                query_embedding = self.embedding_model.encode([query])[0].tolist()
                
                # Vector search
                results = table.search(query_embedding).limit(limit).to_list()
            else:
                # Fallback to text search if no embedding model
                results = table.search(query).limit(limit).to_list()
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'document': result.get('document', ''),
                    'metadata': result.get('metadata', {}),
                    'distance': result.get('_distance', 0.0)
                })
            
            return formatted_results
            
        except Exception as e:
            logging.error(f"Failed to search LanceDB table '{collection_name}': {e}")
            return []
    
    def delete_collection(self, name: str) -> bool:
        """Delete LanceDB table"""
        try:
            if self.db is None:
                return False
                
            self.db.drop_table(name)
            logging.info(f"LanceDB table '{name}' deleted")
            return True
            
        except Exception as e:
            logging.error(f"Failed to delete LanceDB table '{name}': {e}")
            return False


class VectorDBFactory:
    """Factory for creating vector database instances"""
    
    @staticmethod
    def create_vector_db(db_type: str = "chromadb", **kwargs) -> Optional[VectorDBInterface]:
        """Create a vector database instance"""
        if db_type.lower() == "chromadb":
            return ChromaDBManager(**kwargs)
        elif db_type.lower() == "lancedb":
            return LanceDBManager(**kwargs)
        else:
            logging.error(f"Unsupported vector database type: {db_type}")
            return None


# Memory Bank for Project Chimera
class MemoryBank:
    """High-level interface for Project Chimera's memory system"""
    
    def __init__(self, db_type: str = "chromadb"):
        self.vector_db = VectorDBFactory.create_vector_db(db_type)
        self.initialized = False
        
    def initialize(self) -> bool:
        """Initialize the memory bank"""
        if self.vector_db:
            self.initialized = self.vector_db.initialize()
            if self.initialized:
                # Create default collections for Project Chimera
                self.vector_db.create_collection("conversations")
                self.vector_db.create_collection("leads")
                self.vector_db.create_collection("content")
                logging.info("Memory Bank initialized successfully")
            return self.initialized
        return False
    
    def store_conversation(self, conversation_id: str, messages: List[str], 
                          metadata: Dict[str, Any] = None) -> bool:
        """Store conversation in memory bank"""
        if not self.initialized:
            return False
            
        conversation_text = "\n".join(messages)
        metadata = metadata or {}
        metadata["conversation_id"] = conversation_id
        metadata["type"] = "conversation"
        
        return self.vector_db.add_documents("conversations", [conversation_text], [metadata])
    
    def retrieve_similar_conversations(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve similar conversations from memory bank"""
        if not self.initialized:
            return []
            
        return self.vector_db.search("conversations", query, limit)
    
    def store_lead_context(self, lead_id: str, context: str, 
                          metadata: Dict[str, Any] = None) -> bool:
        """Store lead context in memory bank"""
        if not self.initialized:
            return False
            
        metadata = metadata or {}
        metadata["lead_id"] = lead_id
        metadata["type"] = "lead_context"
        
        return self.vector_db.add_documents("leads", [context], [metadata])
    
    def retrieve_lead_context(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve lead context from memory bank"""
        if not self.initialized:
            return []
            
        return self.vector_db.search("leads", query, limit)
