"""
Configuration helper for Azure Document Intelligence Streamlit App
This script helps set up the required environment variables.
"""

import os

def setup_environment():
    """
    Interactive setup for environment variables
    """
    print("🔧 Azure Document Intelligence Configuration Setup")
    print("=" * 55)
    
    # Get endpoint
    current_endpoint = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT", "")
    if current_endpoint:
        print(f"Current endpoint: {current_endpoint}")
        use_current = input("Use current endpoint? (y/n): ").lower().strip()
        if use_current != 'y':
            current_endpoint = ""
    
    if not current_endpoint:
        endpoint = input("Enter your Azure Document Intelligence endpoint: ").strip()
        if endpoint:
            print(f"\nTo set the endpoint, run:")
            print(f'$env:DOCUMENT_INTELLIGENCE_ENDPOINT = "{endpoint}"')
    
    # Authentication info
    print("\n🔐 Authentication Options:")
    print("1. Managed Identity (Recommended for Azure deployment)")
    print("2. API Key (Development only)")
    
    auth_choice = input("\nChoose authentication method (1/2): ").strip()
    
    if auth_choice == "2":
        print("\n⚠️  API Key authentication should only be used for development!")
        print("To set your API key, run:")
        print('$env:DOCUMENT_INTELLIGENCE_KEY = "your-api-key-here"')
    else:
        print("\n✅ Managed Identity is the recommended authentication method.")
        print("Make sure your Azure resource has a managed identity enabled")
        print("and proper RBAC permissions to access Document Intelligence.")
    
    print("\n🚀 Ready to run!")
    print("Execute: streamlit run app.py")

if __name__ == "__main__":
    setup_environment()
