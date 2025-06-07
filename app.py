import streamlit as st
import os
import json
import tempfile
from typing import Optional, Dict, Any
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supported file types by Azure Document Intelligence
SUPPORTED_EXTENSIONS = {
    'pdf': 'application/pdf',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg', 
    'png': 'image/png',
    'bmp': 'image/bmp',
    'tiff': 'image/tiff',
    'heif': 'image/heif',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'html': 'text/html'
}

class DocumentIntelligenceProcessor:
    """
    Azure Document Intelligence processor using the Layout model.
    Implements secure authentication with managed identity and proper error handling.
    """
    
    def __init__(self, endpoint: str, credential_type: str = "managed_identity"):
        """
        Initialize the Document Intelligence client.
        
        Args:
            endpoint: Azure Document Intelligence endpoint
            credential_type: Authentication method ('managed_identity' or 'key')
        """
        self.endpoint = endpoint
        self.credential_type = credential_type
        self.client = self._create_client()
    
    def _create_client(self) -> DocumentIntelligenceClient:
        """
        Create Document Intelligence client with appropriate authentication.
        
        Returns:
            Configured DocumentIntelligenceClient
        """
        try:
            if self.credential_type == "managed_identity":
                # Use DefaultAzureCredential for managed identity (recommended)
                credential = DefaultAzureCredential()
                logger.info("Using managed identity authentication")
            else:
                # Fallback to key-based authentication (for development only)
                api_key = os.getenv("DOCUMENT_INTELLIGENCE_KEY")
                if not api_key:
                    raise ValueError("DOCUMENT_INTELLIGENCE_KEY environment variable not set")
                credential = AzureKeyCredential(api_key)
                logger.info("Using key-based authentication")
            
            return DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=credential
            )
        except Exception as e:
            logger.error(f"Failed to create Document Intelligence client: {str(e)}")
            raise
    
    def analyze_document(self, file_content: bytes, content_type: str) -> Dict[str, Any]:
        """
        Analyze document using Layout model with retry logic and error handling.
        
        Args:
            file_content: Binary content of the file
            content_type: MIME type of the file
            
        Returns:
            Dictionary containing the analysis results
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Starting document analysis (attempt {retry_count + 1})")
                  # Start the analysis operation
                poller = self.client.begin_analyze_document(
                    model_id="prebuilt-layout",
                    body=file_content,
                    content_type=content_type
                )
                
                # Wait for completion
                result = poller.result()
                
                logger.info("Document analysis completed successfully")
                
                # Convert result to dictionary for JSON serialization
                return self._convert_result_to_dict(result)
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"Analysis attempt {retry_count} failed: {str(e)}")
                
                if retry_count >= max_retries:
                    logger.error(f"All retry attempts failed. Final error: {str(e)}")
                    raise
                
                # Exponential backoff
                import time
                time.sleep(2 ** retry_count)
    
    def _convert_result_to_dict(self, result) -> Dict[str, Any]:
        """
        Convert Azure Document Intelligence result to a JSON-serializable dictionary.
        
        Args:
            result: AnalyzeResult object from Azure Document Intelligence
            
        Returns:
            Dictionary representation of the result
        """
        try:
            # Extract key information from the result
            output = {
                "model_id": result.model_id if hasattr(result, 'model_id') else None,
                "api_version": result.api_version if hasattr(result, 'api_version') else None,
                "content": result.content if hasattr(result, 'content') else None,
                "pages": [],
                "tables": [],
                "paragraphs": [],
                "styles": []
            }
            
            # Extract pages information
            if hasattr(result, 'pages') and result.pages:
                for page in result.pages:
                    page_info = {
                        "page_number": page.page_number if hasattr(page, 'page_number') else None,
                        "width": page.width if hasattr(page, 'width') else None,
                        "height": page.height if hasattr(page, 'height') else None,
                        "unit": page.unit if hasattr(page, 'unit') else None,
                        "lines": []
                    }
                    
                    # Extract lines from page
                    if hasattr(page, 'lines') and page.lines:
                        for line in page.lines:
                            line_info = {
                                "content": line.content if hasattr(line, 'content') else None,
                                "bounding_regions": []
                            }
                            
                            # Extract bounding regions
                            if hasattr(line, 'bounding_regions') and line.bounding_regions:
                                for region in line.bounding_regions:
                                    region_info = {
                                        "page_number": region.page_number if hasattr(region, 'page_number') else None,
                                        "polygon": [{"x": point.x, "y": point.y} for point in region.polygon] if hasattr(region, 'polygon') else []
                                    }
                                    line_info["bounding_regions"].append(region_info)
                            
                            page_info["lines"].append(line_info)
                    
                    output["pages"].append(page_info)
            
            # Extract tables information
            if hasattr(result, 'tables') and result.tables:
                for table in result.tables:
                    table_info = {
                        "row_count": table.row_count if hasattr(table, 'row_count') else None,
                        "column_count": table.column_count if hasattr(table, 'column_count') else None,
                        "cells": []
                    }
                    
                    # Extract table cells
                    if hasattr(table, 'cells') and table.cells:
                        for cell in table.cells:
                            cell_info = {
                                "content": cell.content if hasattr(cell, 'content') else None,
                                "row_index": cell.row_index if hasattr(cell, 'row_index') else None,
                                "column_index": cell.column_index if hasattr(cell, 'column_index') else None,
                                "row_span": cell.row_span if hasattr(cell, 'row_span') else 1,
                                "column_span": cell.column_span if hasattr(cell, 'column_span') else 1
                            }
                            table_info["cells"].append(cell_info)
                    
                    output["tables"].append(table_info)
            
            # Extract paragraphs information
            if hasattr(result, 'paragraphs') and result.paragraphs:
                for paragraph in result.paragraphs:
                    paragraph_info = {
                        "content": paragraph.content if hasattr(paragraph, 'content') else None,
                        "role": paragraph.role if hasattr(paragraph, 'role') else None
                    }
                    output["paragraphs"].append(paragraph_info)
            
            return output
            
        except Exception as e:
            logger.error(f"Error converting result to dictionary: {str(e)}")
            # Return basic structure with error information
            return {
                "error": f"Failed to process result: {str(e)}",
                "raw_content": str(result) if result else None
            }

def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="Azure Document Intelligence - Layout Model",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 Azure Document Intelligence - Layout Model")
    st.markdown("Upload documents to extract structured information using Azure AI Document Intelligence Layout model")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Azure Document Intelligence endpoint
        endpoint = st.text_input(
            "Azure Document Intelligence Endpoint",
            value=os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT", ""),
            help="Your Azure Document Intelligence service endpoint URL"
        )
        
        # Authentication method selection
        auth_method = st.selectbox(
            "Authentication Method",
            ["managed_identity", "key"],
            help="Choose authentication method. Managed Identity is recommended for production."
        )
        
        if auth_method == "key":
            st.warning("⚠️ Key-based authentication should only be used for development. Use environment variable DOCUMENT_INTELLIGENCE_KEY.")
        
        st.markdown("---")
        st.markdown("### Supported File Types")
        st.markdown("- **Documents**: PDF")
        st.markdown("- **Images**: JPG, PNG, BMP, TIFF, HEIF")
        st.markdown("- **Office**: DOCX, XLSX, PPTX")
        st.markdown("- **Web**: HTML")
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📤 Upload Document")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=list(SUPPORTED_EXTENSIONS.keys()),
            help="Upload a document supported by Azure Document Intelligence"
        )
        
        if uploaded_file is not None:
            # Display file information
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            st.info(f"📊 File size: {len(uploaded_file.getvalue())} bytes")
            
            # Get file extension and content type
            file_extension = uploaded_file.name.split('.')[-1].lower()
            content_type = SUPPORTED_EXTENSIONS.get(file_extension)
            
            if content_type:
                st.info(f"🔍 Content type: {content_type}")
                
                # Process button
                if st.button("🚀 Analyze Document", type="primary"):
                    if not endpoint:
                        st.error("❌ Please provide the Azure Document Intelligence endpoint in the sidebar")
                        return
                    
                    try:
                        # Show progress
                        with st.spinner("🔄 Analyzing document with Azure Document Intelligence..."):
                            # Initialize processor
                            processor = DocumentIntelligenceProcessor(
                                endpoint=endpoint,
                                credential_type=auth_method
                            )
                            
                            # Analyze document
                            file_content = uploaded_file.getvalue()
                            result = processor.analyze_document(file_content, content_type)
                            
                            # Store result in session state
                            st.session_state.analysis_result = result
                            st.session_state.filename = uploaded_file.name
                        
                        st.success("✅ Document analysis completed!")
                        
                    except Exception as e:
                        st.error(f"❌ Error analyzing document: {str(e)}")
                        logger.error(f"Document analysis failed: {str(e)}")
            else:
                st.error(f"❌ Unsupported file type: {file_extension}")
    
    with col2:
        st.header("📋 Analysis Results")
        
        # Display results if available
        if hasattr(st.session_state, 'analysis_result'):
            result = st.session_state.analysis_result
            filename = st.session_state.filename
            
            # Results summary
            st.subheader("📊 Summary")
            
            # Count extracted elements
            pages_count = len(result.get('pages', []))
            tables_count = len(result.get('tables', []))
            paragraphs_count = len(result.get('paragraphs', []))
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Pages", pages_count)
            with col_b:
                st.metric("Tables", tables_count)
            with col_c:
                st.metric("Paragraphs", paragraphs_count)
            
            # Display extracted content preview
            if result.get('content'):
                st.subheader("📄 Extracted Text (Preview)")
                preview_text = result['content'][:500] + "..." if len(result['content']) > 500 else result['content']
                st.text_area("Content Preview", preview_text, height=150, disabled=True)
            
            # JSON download
            st.subheader("💾 Download Results")
            
            # Format JSON for download
            json_str = json.dumps(result, indent=2, ensure_ascii=False)
            
            st.download_button(
                label="📥 Download JSON Results",
                data=json_str,
                file_name=f"{filename}_analysis_result.json",
                mime="application/json",
                type="primary"
            )
            
            # Display JSON in expandable section
            with st.expander("🔍 View Full JSON Results", expanded=False):
                st.json(result)
        
        else:
            st.info("👈 Upload and analyze a document to see results here")

if __name__ == "__main__":
    main()