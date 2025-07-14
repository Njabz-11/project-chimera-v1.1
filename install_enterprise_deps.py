#!/usr/bin/env python3
"""
Install Enterprise Dependencies for Project Chimera
This script installs the additional security and enterprise dependencies
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr.strip()}")
        return False

def main():
    """Main installation function"""
    print("🚀 Installing Project Chimera Enterprise Dependencies")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("requirements.txt").exists():
        print("❌ Error: requirements.txt not found. Please run this script from the Project-Chimera-Dev directory.")
        sys.exit(1)
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment not detected. It's recommended to use a virtual environment.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Installation cancelled.")
            sys.exit(1)
    
    # Install dependencies
    dependencies = [
        "python-jose[cryptography]==3.3.0",
        "passlib[bcrypt]==1.7.4", 
        "python-multipart==0.0.6",
        "pydantic[email]==2.5.0",
        "sqlalchemy==2.0.23",
        "alembic==1.13.1",
        "redis==5.0.1",
        "celery==5.3.4",
        "loguru==0.7.2"
    ]
    
    print(f"\n📦 Installing {len(dependencies)} enterprise dependencies...")
    
    failed_installs = []
    
    for dep in dependencies:
        if not run_command(f"pip install {dep}", f"Installing {dep}"):
            failed_installs.append(dep)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 INSTALLATION SUMMARY")
    print("=" * 60)
    
    if not failed_installs:
        print("✅ All enterprise dependencies installed successfully!")
        print("\n🔐 Enterprise Security Features Added:")
        print("   • JWT Authentication with python-jose")
        print("   • Password hashing with passlib/bcrypt")
        print("   • Form data handling with python-multipart")
        print("   • Enhanced Pydantic with email validation")
        print("   • SQLAlchemy ORM for advanced database operations")
        print("   • Alembic for database migrations")
        print("   • Redis for caching and session management")
        print("   • Celery for background task processing")
        print("   • Loguru for enhanced logging")
        
        print("\n🚀 Next Steps:")
        print("   1. Copy .env.template to .env and configure your settings")
        print("   2. Generate a secure SECRET_KEY for production")
        print("   3. Update ALLOWED_ORIGINS and ALLOWED_HOSTS for your environment")
        print("   4. Configure database connection (PostgreSQL recommended for production)")
        print("   5. Set up Redis if using production features")
        print("   6. Start the server: python main.py")
        
    else:
        print(f"❌ {len(failed_installs)} dependencies failed to install:")
        for dep in failed_installs:
            print(f"   • {dep}")
        print("\n🔧 Troubleshooting:")
        print("   • Make sure you have the latest pip: pip install --upgrade pip")
        print("   • Some packages require build tools (Visual Studio Build Tools on Windows)")
        print("   • Try installing failed packages individually for more detailed error messages")
        sys.exit(1)

if __name__ == "__main__":
    main()
