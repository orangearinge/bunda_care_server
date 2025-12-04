"""
Test script untuk Google OAuth endpoint
Jalankan dengan: python test_google_oauth.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.user import User

def test_google_oauth_endpoint():
    """Test apakah endpoint Google OAuth sudah terdaftar"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("GOOGLE OAUTH CONFIGURATION CHECK")
        print("=" * 60)
        
        # Check environment variables
        print("\n1. Environment Variables:")
        google_client_id = app.config.get('GOOGLE_CLIENT_ID')
        google_client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
        
        if google_client_id:
            print(f"   ✓ GOOGLE_CLIENT_ID: {google_client_id[:20]}...")
        else:
            print("   ✗ GOOGLE_CLIENT_ID: NOT SET")
            
        if google_client_secret:
            print(f"   ✓ GOOGLE_CLIENT_SECRET: {google_client_secret[:10]}...")
        else:
            print("   ✗ GOOGLE_CLIENT_SECRET: NOT SET")
        
        # Check routes
        print("\n2. Registered Routes:")
        auth_routes = [rule for rule in app.url_map.iter_rules() if 'auth' in rule.rule]
        for rule in auth_routes:
            methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
            print(f"   {methods:10} {rule.rule}")
        
        # Check if /api/auth/google exists
        google_route = any('/google' in rule.rule for rule in auth_routes)
        if google_route:
            print("\n   ✓ Google OAuth endpoint registered")
        else:
            print("\n   ✗ Google OAuth endpoint NOT found")
        
        # Check database schema
        print("\n3. Database Schema (users table):")
        try:
            inspector = db.inspect(db.engine)
            if inspector.has_table('users'):
                columns = inspector.get_columns('users')
                required_cols = ['google_id', 'avatar', 'email', 'password']
                
                for col_name in required_cols:
                    col = next((c for c in columns if c['name'] == col_name), None)
                    if col:
                        nullable = "nullable" if col['nullable'] else "NOT NULL"
                        print(f"   ✓ {col_name:15} ({col['type']}, {nullable})")
                    else:
                        print(f"   ✗ {col_name:15} NOT FOUND")
            else:
                print("   ✗ Table 'users' does not exist")
        except Exception as e:
            print(f"   ✗ Error checking database: {e}")
        
        # Check dependencies
        print("\n4. Required Dependencies:")
        try:
            import google.auth
            print("   ✓ google-auth installed")
        except ImportError:
            print("   ✗ google-auth NOT installed")
        
        try:
            import requests
            print("   ✓ requests installed")
        except ImportError:
            print("   ✗ requests NOT installed")
        
        # Summary
        print("\n" + "=" * 60)
        print("SETUP STATUS")
        print("=" * 60)
        
        all_good = (
            google_client_id and 
            google_client_secret and 
            google_route
        )
        
        if all_good:
            print("✓ Google OAuth is configured and ready to use!")
            print("\nNext steps:")
            print("1. Make sure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env are correct")
            print("2. Test the endpoint with a real Google ID token")
            print("3. See GOOGLE_OAUTH_SETUP.md for integration guide")
        else:
            print("✗ Google OAuth setup incomplete")
            print("\nPlease check:")
            if not google_client_id or not google_client_secret:
                print("- Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env")
            if not google_route:
                print("- Ensure auth_routes.py is properly registered")
        
        print("=" * 60)

if __name__ == "__main__":
    test_google_oauth_endpoint()
