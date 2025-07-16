#!/usr/bin/env python3
"""
Test script for vector database infrastructure
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from infrastructure.vector_db import MemoryBank, VectorDBFactory

def test_chromadb():
    """Test ChromaDB functionality"""
    print("Testing ChromaDB...")
    
    try:
        mb = MemoryBank('chromadb')
        result = mb.initialize()
        print(f"ChromaDB initialization: {'SUCCESS' if result else 'FAILED'}")
        
        if result:
            # Test storing a conversation
            test_result = mb.store_conversation(
                "test_conv_1", 
                ["Hello", "How can I help you?", "I need information about your services"],
                {"lead_id": "lead_123", "timestamp": "2024-01-01"}
            )
            print(f"Store conversation: {'SUCCESS' if test_result else 'FAILED'}")
            
            # Test retrieval
            results = mb.retrieve_similar_conversations("services information", limit=3)
            print(f"Retrieve conversations: {'SUCCESS' if results else 'FAILED'}")
            print(f"Found {len(results)} similar conversations")
            
    except Exception as e:
        print(f"ChromaDB test failed: {e}")

def test_lancedb():
    """Test LanceDB functionality"""
    print("\nTesting LanceDB...")
    
    try:
        mb = MemoryBank('lancedb')
        result = mb.initialize()
        print(f"LanceDB initialization: {'SUCCESS' if result else 'FAILED'}")
        
        if result:
            # Test storing a conversation
            test_result = mb.store_conversation(
                "test_conv_2", 
                ["Hi there", "What services do you offer?", "I'm interested in your AI solutions"],
                {"lead_id": "lead_456", "timestamp": "2024-01-02"}
            )
            print(f"Store conversation: {'SUCCESS' if test_result else 'FAILED'}")
            
            # Test retrieval
            results = mb.retrieve_similar_conversations("AI solutions", limit=3)
            print(f"Retrieve conversations: {'SUCCESS' if results else 'FAILED'}")
            print(f"Found {len(results)} similar conversations")
            
    except Exception as e:
        print(f"LanceDB test failed: {e}")

def test_dependencies():
    """Test if all dependencies are available"""
    print("Testing dependencies...")
    
    try:
        import chromadb
        print("✅ ChromaDB available")
    except ImportError:
        print("❌ ChromaDB not available")
    
    try:
        import lancedb
        print("✅ LanceDB available")
    except ImportError:
        print("❌ LanceDB not available")
    
    try:
        from sentence_transformers import SentenceTransformer
        print("✅ SentenceTransformers available")
    except ImportError:
        print("❌ SentenceTransformers not available")

if __name__ == "__main__":
    print("=== Project Chimera Vector Database Infrastructure Test ===")
    
    test_dependencies()
    test_chromadb()
    test_lancedb()
    
    print("\n=== Test Complete ===")
