"""
Demo script for Azure Document Intelligence Streamlit App

This script demonstrates how to use the Streamlit app programmatically
for testing and automation purposes.
"""

import json
import os
from app import DocumentIntelligenceProcessor

def demo_document_analysis():
    """
    Demo function showing how to use the DocumentIntelligenceProcessor
    """
    
    # Configuration
    endpoint = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")
    if not endpoint:
        print("❌ Please set DOCUMENT_INTELLIGENCE_ENDPOINT environment variable")
        return
    
    # Initialize processor with managed identity (recommended)
    processor = DocumentIntelligenceProcessor(
        endpoint=endpoint,
        credential_type="managed_identity"  # or "key" for development
    )
    
    # Example: Analyze a sample document
    # You would replace this with actual file content
    print("📄 Document Intelligence Demo")
    print("=" * 50)
    print(f"Endpoint: {endpoint}")
    print(f"Authentication: Managed Identity")
    print("\nSupported file types:")
    
    from app import SUPPORTED_EXTENSIONS
    for ext, mime_type in SUPPORTED_EXTENSIONS.items():
        print(f"  • {ext.upper()}: {mime_type}")
    
    print("\n🚀 To use the app:")
    print("1. Set your Document Intelligence endpoint:")
    print("   $env:DOCUMENT_INTELLIGENCE_ENDPOINT = 'https://your-resource.cognitiveservices.azure.com/'")
    print("\n2. Run the Streamlit app:")
    print("   streamlit run app.py")
    print("\n3. Upload a supported file and click 'Analyze Document'")
    print("\n4. Download the JSON results or view them in the browser")

if __name__ == "__main__":
    demo_document_analysis()
