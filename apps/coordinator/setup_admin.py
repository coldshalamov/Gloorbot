"""
Quick setup script for Gloorbot Admin Interface.
Run this to initialize the admin system and verify everything is working.
"""
import sys
from pathlib import Path

# Add the coordinator app to the path
sys.path.insert(0, str(Path(__file__).parent))

from coordinator_app.admin_auth import ADMIN_EMAIL, ADMIN_PASSWORD, verify_credentials, create_session
from coordinator_app.store_config import get_store_config_manager


def main():
    print("=" * 70)
    print("Gloorbot Admin Interface Setup")
    print("=" * 70)
    print()

    # Test authentication
    print("1. Testing Admin Authentication...")
    test_email = ADMIN_EMAIL
    test_password = ADMIN_PASSWORD
    
    if verify_credentials(test_email, test_password):
        print("   ✅ Admin credentials verified")
        token = create_session(test_email)
        print(f"   ✅ Session token created: {token[:20]}...")
    else:
        print("   ❌ Admin credentials failed")
        return
    
    print()

    # Test store configuration
    print("2. Testing Store Configuration Manager...")
    config_manager = get_store_config_manager()
    
    enabled_states = config_manager.get_enabled_states()
    print(f"   ✅ Enabled states: {', '.join(enabled_states)}")
    
    enabled_stores = config_manager.get_enabled_stores()
    print(f"   ✅ Enabled stores: {len(enabled_stores)} stores")
    
    all_stores = config_manager.get_all_stores_by_state()
    total_stores = sum(len(stores) for stores in all_stores.values())
    print(f"   ✅ Total available stores: {total_stores}")
    
    print()

    # Show store breakdown
    print("3. Store Breakdown by State:")
    for state, stores in sorted(all_stores.items()):
        print(f"   {state}: {len(stores)} stores")
    
    print()

    # Generate sample urls.txt
    print("4. Generating sample urls.txt...")
    urls_content = config_manager.generate_urls_txt()
    lines = urls_content.split('\n')
    print(f"   ✅ Generated {len(lines)} lines")
    print(f"   ✅ Store URLs: {sum(1 for line in lines if '/store/' in line)}")
    print(f"   ✅ Category URLs: {sum(1 for line in lines if '/pl/' in line)}")
    
    print()

    # Show configuration file location
    print("5. Configuration Files:")
    print(f"   Config: {config_manager.config_file}")
    print(f"   Exists: {config_manager.config_file.exists()}")
    
    print()

    # Success message
    print("=" * 70)
    print("✅ Setup Complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Start the coordinator:")
    print("   cd apps/coordinator")
    print("   uvicorn coordinator_app.main:app --reload")
    print()
    print("2. Open admin interface:")
    print("   http://localhost:8000/admin/login")
    print()
    print("3. Login with:")
    print(f"   Email: {test_email}")
    print("   Password: (set via GLOORBOT_ADMIN_PASSWORD)")
    print()


if __name__ == "__main__":
    main()
