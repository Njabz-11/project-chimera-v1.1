#!/usr/bin/env python3
"""
Setup Initial Admin User for Project Chimera Enterprise
This script creates the first admin user for the system
"""

import asyncio
import getpass
import sys
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

from database.db_manager import DatabaseManager
from auth.security import get_security_manager
from utils.logger import ChimeraLogger

logger = ChimeraLogger.get_logger(__name__)

async def create_admin_user():
    """Create the initial admin user"""
    print("🔐 Project Chimera Enterprise - Admin User Setup")
    print("=" * 60)
    
    # Initialize database
    db_manager = DatabaseManager("data/chimera_enterprise.db")
    await db_manager.initialize()
    
    security_manager = get_security_manager()
    
    # Check if admin user already exists
    existing_admin = await db_manager.get_user_by_username("admin")
    if existing_admin:
        print("⚠️  Admin user already exists!")
        print(f"   Username: {existing_admin['username']}")
        print(f"   Email: {existing_admin['email']}")
        print(f"   Created: {existing_admin['created_at']}")
        
        response = input("\nDo you want to create a different admin user? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            await db_manager.close()
            return
    
    print("\n👤 Enter admin user details:")
    
    # Get username
    while True:
        username = input("Username (default: admin): ").strip()
        if not username:
            username = "admin"
        
        if len(username) < 3:
            print("❌ Username must be at least 3 characters long")
            continue
        
        # Check if username exists
        existing_user = await db_manager.get_user_by_username(username)
        if existing_user:
            print(f"❌ Username '{username}' already exists")
            continue
        
        break
    
    # Get email
    while True:
        email = input("Email: ").strip()
        if not email or "@" not in email:
            print("❌ Please enter a valid email address")
            continue
        
        # Check if email exists
        existing_email = await db_manager.get_user_by_email(email)
        if existing_email:
            print(f"❌ Email '{email}' already exists")
            continue
        
        break
    
    # Get full name
    full_name = input("Full Name (optional): ").strip()
    if not full_name:
        full_name = None
    
    # Get password
    while True:
        password = getpass.getpass("Password: ")
        if len(password) < 8:
            print("❌ Password must be at least 8 characters long")
            continue
        
        # Validate password strength
        validation = security_manager.validate_password_strength(password)
        if not validation["is_valid"]:
            print("❌ Password does not meet requirements:")
            for error in validation["errors"]:
                print(f"   • {error}")
            continue
        
        confirm_password = getpass.getpass("Confirm Password: ")
        if password != confirm_password:
            print("❌ Passwords do not match")
            continue
        
        break
    
    # Create user
    try:
        print("\n🔧 Creating admin user...")
        
        hashed_password = security_manager.get_password_hash(password)
        
        user_data = {
            "username": username,
            "email": email,
            "full_name": full_name,
            "hashed_password": hashed_password,
            "role": "admin",
            "status": "active",
            "is_active": True
        }
        
        user_id = await db_manager.create_user(user_data)
        
        print("✅ Admin user created successfully!")
        print(f"   User ID: {user_id}")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Role: admin")
        
        print("\n🚀 You can now start the server and login with these credentials:")
        print("   python main.py")
        print("   Then visit: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"❌ Failed to create admin user: {e}")
        logger.error(f"Admin user creation failed: {e}")
    
    finally:
        await db_manager.close()

def main():
    """Main function"""
    try:
        asyncio.run(create_admin_user())
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
