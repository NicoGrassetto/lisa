"""
Azure AI Document Intelligence utilities for extracting comprehensive document information.

This module provides functions to extract detailed information from PDF documents using
Azure AI Document Intelligence service with high-resolution analysis and formula detection.
"""

import logging
import io
from typing import Dict, List, Any, Optional, Union
import streamlit as st
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError, ServiceRequestError
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentIntelligenceError(Exception):
    """Custom exception for Document Intelligence operations."""
    pass


def _get_credential():
    """
    Get Azure credential using best practices.
    
    Returns:
        Azure credential object
        
    Raises:
        DocumentIntelligenceError: If credential acquisition fails
    """
    try:
        # Try DefaultAzureCredential first (works with managed identity, Azure CLI, etc.)
        credential = DefaultAzureCredential()
        return credential
    except Exception as e:
        logger.warning(f"DefaultAzureCredential failed: {e}")
        try:
            # Fallback to interactive browser credential for local development
            credential = InteractiveBrowserCredential()
            return credential
        except Exception as e:
            logger.error(f"All credential methods failed: {e}")
            raise DocumentIntelligenceError(
                "Failed to acquire Azure credentials. Ensure you're authenticated with Azure CLI "
                "or have proper managed identity configured."
            )


def _validate_pdf_file(uploaded_file) -> bool:
    """
    Validate that the uploaded file is a PDF.
    
    Args:
        uploaded_file: Streamlit uploaded file object
        
    Returns:
        bool: True if file is a valid PDF
        
    Raises:
        DocumentIntelligenceError: If file is not a PDF or validation fails
    """
    if uploaded_file is None:
        raise DocumentIntelligenceError("No file provided")
    
    # Check file extension
    if not uploaded_file.name.lower().endswith('.pdf'):
        raise DocumentIntelligenceError(
            f"Invalid file type. Expected PDF, got: {uploaded_file.name}"
        )
    
    # Check MIME type if available
    if hasattr(uploaded_file, 'type') and uploaded_file.type:
        if not uploaded_file.type.lower() in ['application/pdf', 'application/x-pdf']:
            raise DocumentIntelligenceError(
                f"Invalid MIME type. Expected PDF, got: {uploaded_file.type}"
            )
    
    # Basic file size check (adjust as needed)
    file_size = len(uploaded_file.getvalue())
    if file_size == 0:
        raise DocumentIntelligenceError("File is empty")
    
    if file_size > 500 * 1024 * 1024:  # 500MB limit
        raise DocumentIntelligenceError(
            f"File too large ({file_size / (1024*1024):.1f}MB). Maximum size is 500MB"
        )
    
    logger.info(f"PDF validation successful: {uploaded_file.name} ({file_size / 1024:.1f}KB)")
    return True


def _extract_bounding_boxes(elements: List[Any]) -> List[Dict[str, Any]]:
    """
    Extract bounding box information from document elements.
    
    Args:
        elements: List of document elements
        
    Returns:
        List of bounding box dictionaries
    """
    bounding_boxes = []
    
    for element in elements:
        if hasattr(element, 'bounding_regions') and element.bounding_regions:
            for region in element.bounding_regions:
                if hasattr(region, 'polygon') and region.polygon:
                    bbox = {
                        'page_number': getattr(region, 'page_number', None),
                        'polygon': [(point.x, point.y) for point in region.polygon],
                        'content': getattr(element, 'content', ''),
                        'element_type': type(element).__name__,
                        'confidence': getattr(element, 'confidence', None)
                    }
                    bounding_boxes.append(bbox)
    
    return bounding_boxes


def _organize_headers_by_level(paragraphs: List[Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Organize headers and sub-headers by hierarchy level.
    
    Args:
        paragraphs: List of paragraph elements from Document Intelligence
        
    Returns:
        Dictionary with headers organized by level
    """
    headers_by_level = {}
    
    for paragraph in paragraphs:
        if hasattr(paragraph, 'role') and paragraph.role:
            role = paragraph.role
            if 'title' in role.lower() or 'heading' in role.lower():
                # Extract heading level (h1, h2, etc.)
                level = 'h1'  # default
                if hasattr(paragraph, 'role'):
                    role_lower = paragraph.role.lower()
                    if 'h1' in role_lower or 'title' in role_lower:
                        level = 'h1'
                    elif 'h2' in role_lower:
                        level = 'h2'
                    elif 'h3' in role_lower:
                        level = 'h3'
                    elif 'h4' in role_lower:
                        level = 'h4'
                    elif 'h5' in role_lower:
                        level = 'h5'
                    elif 'h6' in role_lower:
                        level = 'h6'
                
                if level not in headers_by_level:
                    headers_by_level[level] = []
                
                header_info = {
                    'content': paragraph.content,
                    'confidence': getattr(paragraph, 'confidence', None),
                    'bounding_regions': []
                }
                
                # Add bounding box information
                if hasattr(paragraph, 'bounding_regions'):
                    for region in paragraph.bounding_regions:
                        if hasattr(region, 'polygon'):
                            header_info['bounding_regions'].append({
                                'page_number': getattr(region, 'page_number', None),
                                'polygon': [(point.x, point.y) for point in region.polygon]
                            })
                
                headers_by_level[level].append(header_info)
    
    return headers_by_level

@st.cache_data(ttl=3600)  # Cache results for 1 hour
def extract_data(uploaded_file, endpoint: Optional[str] = None, 
                use_key_credential: bool = False, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract comprehensive information from a PDF document using Azure AI Document Intelligence.
    
    This function uses Azure AI Document Intelligence with high-resolution analysis and formula
    detection to extract detailed information including paragraphs, headers, formulas, tables,
    and bounding boxes for all detected entities across multiple pages.
    
    Args:
        uploaded_file: Streamlit uploaded file object (must be PDF)
        endpoint (str, optional): Azure Document Intelligence endpoint URL.
                                If not provided, will try to get from environment variable
                                AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
        use_key_credential (bool): Whether to use API key authentication instead of managed identity
        api_key (str, optional): API key for authentication (only if use_key_credential=True)
    
    Returns:
        Dict[str, Any]: Comprehensive dictionary containing:
            - 'paragraphs': List of all paragraph content with metadata
            - 'headers': Dictionary organized by heading levels (h1, h2, etc.)
            - 'formulas': List of detected mathematical formulas
            - 'tables': List of extracted tables with structure
            - 'key_value_pairs': List of detected key-value pairs
            - 'bounding_boxes': List of bounding box coordinates for all elements
            - 'pages': List of page-level information
            - 'document_metadata': Overall document information
            - 'confidence_scores': Analysis confidence metrics
    
    Raises:
        DocumentIntelligenceError: For validation, authentication, or processing errors
        
    Examples:
        >>> with open('document.pdf', 'rb') as f:
        ...     result = extract_data(f)
        >>> print(f"Found {len(result['paragraphs'])} paragraphs")
        >>> print(f"Headers: {list(result['headers'].keys())}")
    """
    try:
        # Validate input file
        _validate_pdf_file(uploaded_file)
        
        # Get endpoint from parameter or environment
        if not endpoint:
            endpoint = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
            if not endpoint:
                raise DocumentIntelligenceError(
                    "Document Intelligence endpoint not provided. Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT "
                    "environment variable or pass endpoint parameter."
                )
        
        # Initialize Document Intelligence client with proper authentication
        if use_key_credential:
            if not api_key:
                api_key = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')
                if not api_key:
                    raise DocumentIntelligenceError(
                        "API key not provided. Set AZURE_DOCUMENT_INTELLIGENCE_KEY environment variable "
                        "or pass api_key parameter when use_key_credential=True."
                    )
            credential = AzureKeyCredential(api_key)
            logger.info("Using API key authentication")
        else:
            credential = _get_credential()
            logger.info("Using managed identity/interactive authentication")
        
        client = DocumentAnalysisClient(endpoint=endpoint, credential=credential)
        
        # Prepare document for analysis
        file_content = uploaded_file.getvalue()
        file_stream = io.BytesIO(file_content)
        
        logger.info(f"Starting document analysis for: {uploaded_file.name}")
        
        # Analyze document with prebuilt-layout model for comprehensive extraction
        # This model supports high-resolution analysis and formula detection
        poller = client.begin_analyze_document(
            model_id="prebuilt-layout",
            document=file_stream,
            features=["formulas"]  # Enable formula detection
        )
        
        # Wait for analysis to complete
        result = poller.result()
        
        logger.info("Document analysis completed successfully")
        
        # Initialize result dictionary
        extracted_data = {
            'paragraphs': [],
            'headers': {},
            'formulas': [],
            'tables': [],
            'key_value_pairs': [],
            'bounding_boxes': [],
            'pages': [],
            'document_metadata': {},
            'confidence_scores': {}
        }
        
        # Extract paragraphs with detailed information
        if result.paragraphs:
            for paragraph in result.paragraphs:
                para_data = {
                    'content': paragraph.content,
                    'role': getattr(paragraph, 'role', None),
                    'confidence': getattr(paragraph, 'confidence', None),
                    'bounding_regions': []
                }
                
                # Add bounding box information
                if hasattr(paragraph, 'bounding_regions'):
                    for region in paragraph.bounding_regions:
                        if hasattr(region, 'polygon'):
                            para_data['bounding_regions'].append({
                                'page_number': getattr(region, 'page_number', None),
                                'polygon': [(point.x, point.y) for point in region.polygon]
                            })
                
                extracted_data['paragraphs'].append(para_data)
            
            # Organize headers by level
            extracted_data['headers'] = _organize_headers_by_level(result.paragraphs)
        
        # Extract formulas
        if hasattr(result, 'formulas') and result.formulas:
            for formula in result.formulas:
                formula_data = {
                    'content': getattr(formula, 'value', ''),
                    'confidence': getattr(formula, 'confidence', None),
                    'kind': getattr(formula, 'kind', None),
                    'bounding_regions': []
                }
                
                # Add bounding box information for formulas
                if hasattr(formula, 'bounding_regions'):
                    for region in formula.bounding_regions:
                        if hasattr(region, 'polygon'):
                            formula_data['bounding_regions'].append({
                                'page_number': getattr(region, 'page_number', None),
                                'polygon': [(point.x, point.y) for point in region.polygon]
                            })
                
                extracted_data['formulas'].append(formula_data)
        
        # Extract tables with structure
        if result.tables:
            for table in result.tables:
                table_data = {
                    'row_count': table.row_count,
                    'column_count': table.column_count,
                    'cells': [],
                    'confidence': getattr(table, 'confidence', None),
                    'bounding_regions': []
                }
                
                # Extract table cells
                for cell in table.cells:
                    cell_data = {
                        'content': cell.content,
                        'row_index': cell.row_index,
                        'column_index': cell.column_index,
                        'row_span': getattr(cell, 'row_span', 1),
                        'column_span': getattr(cell, 'column_span', 1),
                        'confidence': getattr(cell, 'confidence', None),
                        'kind': getattr(cell, 'kind', None)
                    }
                    table_data['cells'].append(cell_data)
                
                # Add table bounding box information
                if hasattr(table, 'bounding_regions'):
                    for region in table.bounding_regions:
                        if hasattr(region, 'polygon'):
                            table_data['bounding_regions'].append({
                                'page_number': getattr(region, 'page_number', None),
                                'polygon': [(point.x, point.y) for point in region.polygon]
                            })
                
                extracted_data['tables'].append(table_data)
        
        # Extract key-value pairs
        if result.key_value_pairs:
            for kv_pair in result.key_value_pairs:
                kv_data = {
                    'key': kv_pair.key.content if kv_pair.key else None,
                    'value': kv_pair.value.content if kv_pair.value else None,
                    'confidence': getattr(kv_pair, 'confidence', None)
                }
                extracted_data['key_value_pairs'].append(kv_data)
        
        # Extract comprehensive bounding boxes
        all_elements = []
        if result.paragraphs:
            all_elements.extend(result.paragraphs)
        if result.tables:
            all_elements.extend(result.tables)
        if hasattr(result, 'formulas') and result.formulas:
            all_elements.extend(result.formulas)
        
        extracted_data['bounding_boxes'] = _extract_bounding_boxes(all_elements)
        
        # Extract page information
        if result.pages:
            for page in result.pages:
                page_data = {
                    'page_number': page.page_number,
                    'width': page.width,
                    'height': page.height,
                    'unit': getattr(page, 'unit', None),
                    'angle': getattr(page, 'angle', None),
                    'lines_count': len(page.lines) if page.lines else 0,
                    'words_count': len(page.words) if page.words else 0
                }
                extracted_data['pages'].append(page_data)
        
        # Document metadata
        extracted_data['document_metadata'] = {
            'model_id': result.model_id,
            'total_pages': len(result.pages) if result.pages else 0,
            'file_name': uploaded_file.name,
            'file_size_bytes': len(file_content),
            'content_length': len(result.content) if hasattr(result, 'content') else 0
        }
        
        # Confidence scores summary
        paragraph_confidences = [p.get('confidence') for p in extracted_data['paragraphs'] 
                               if p.get('confidence') is not None]
        table_confidences = [t.get('confidence') for t in extracted_data['tables'] 
                           if t.get('confidence') is not None]
        formula_confidences = [f.get('confidence') for f in extracted_data['formulas'] 
                             if f.get('confidence') is not None]
        
        extracted_data['confidence_scores'] = {
            'average_paragraph_confidence': sum(paragraph_confidences) / len(paragraph_confidences) 
                                           if paragraph_confidences else None,
            'average_table_confidence': sum(table_confidences) / len(table_confidences) 
                                      if table_confidences else None,
            'average_formula_confidence': sum(formula_confidences) / len(formula_confidences) 
                                        if formula_confidences else None,
            'min_confidence': min(paragraph_confidences + table_confidences + formula_confidences) 
                            if (paragraph_confidences or table_confidences or formula_confidences) else None,
            'max_confidence': max(paragraph_confidences + table_confidences + formula_confidences) 
                            if (paragraph_confidences or table_confidences or formula_confidences) else None
        }
        
        logger.info(f"Successfully extracted data from {uploaded_file.name}: "
                   f"{len(extracted_data['paragraphs'])} paragraphs, "
                   f"{len(extracted_data['formulas'])} formulas, "
                   f"{len(extracted_data['tables'])} tables")
        
        return extracted_data
        
    except HttpResponseError as e:
        error_msg = f"Azure Document Intelligence HTTP error: {e.message}"
        logger.error(error_msg)
        raise DocumentIntelligenceError(error_msg)
    
    except ServiceRequestError as e:
        error_msg = f"Azure Document Intelligence service error: {str(e)}"
        logger.error(error_msg)
        raise DocumentIntelligenceError(error_msg)
    
    except Exception as e:
        error_msg = f"Unexpected error during document analysis: {str(e)}"
        logger.error(error_msg)
        raise DocumentIntelligenceError(error_msg)