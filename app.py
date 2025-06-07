import streamlit as st
import json
from utils import extract_data, DocumentIntelligenceError

st.title("📄 Azure AI Document Intelligence Analyzer")
st.markdown("Upload a PDF document to extract comprehensive information using Azure AI Document Intelligence.")

# Configuration section
with st.sidebar:
    st.header("⚙️ Configuration")
    st.markdown("### Azure Document Intelligence Settings")
    
    endpoint = st.text_input(
        "Document Intelligence Endpoint",
        help="Your Azure Document Intelligence endpoint URL",
        placeholder="https://your-resource.cognitiveservices.azure.com/"
    )
    
    use_key_auth = st.checkbox(
        "Use API Key Authentication", 
        help="Check this if you want to use API key instead of managed identity"
    )
    
    api_key = None
    if use_key_auth:
        api_key = st.text_input(
            "API Key", 
            type="password",
            help="Your Azure Document Intelligence API key"
        )

# Main content area
uploaded_file = st.file_uploader(
    "Upload a PDF document", 
    type=['pdf'],
    help="Select a PDF file to analyze with Azure AI Document Intelligence"
)

if uploaded_file is not None:
    st.success(f"✅ File uploaded: {uploaded_file.name}")
    
    # File information
    file_size = len(uploaded_file.getvalue())
    st.info(f"📊 File size: {file_size / 1024:.1f} KB")
    
    if st.button("🚀 Analyze Document", type="primary"):
        try:
            with st.spinner("🔍 Analyzing document with Azure AI Document Intelligence..."):
                # Extract data using the utils function
                result = extract_data(
                    uploaded_file=uploaded_file,
                    endpoint=endpoint if endpoint else None,
                    use_key_credential=use_key_auth,
                    api_key=api_key if use_key_auth else None
                )
            
            st.success("✅ Document analysis completed!")
            
            # Display results in organized tabs
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "📋 Summary", "📝 Content", "🧮 Formulas", "📊 Tables", "🗂️ Structure", "📐 Technical Details"
            ])
            
            with tab1:
                st.header("📋 Document Summary")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Pages", result['document_metadata']['total_pages'])
                with col2:
                    st.metric("Paragraphs", len(result['paragraphs']))
                with col3:
                    st.metric("Formulas", len(result['formulas']))
                with col4:
                    st.metric("Tables", len(result['tables']))
                
                # Confidence scores
                if result['confidence_scores']['average_paragraph_confidence']:
                    st.subheader("🎯 Confidence Scores")
                    conf_col1, conf_col2, conf_col3 = st.columns(3)
                    with conf_col1:
                        avg_para_conf = result['confidence_scores']['average_paragraph_confidence']
                        st.metric("Avg Paragraph Confidence", f"{avg_para_conf:.2%}")
                    with conf_col2:
                        if result['confidence_scores']['average_table_confidence']:
                            avg_table_conf = result['confidence_scores']['average_table_confidence']
                            st.metric("Avg Table Confidence", f"{avg_table_conf:.2%}")
                    with conf_col3:
                        if result['confidence_scores']['average_formula_confidence']:
                            avg_formula_conf = result['confidence_scores']['average_formula_confidence']
                            st.metric("Avg Formula Confidence", f"{avg_formula_conf:.2%}")
            
            with tab2:
                st.header("📝 Document Content")
                
                # Headers by level
                if result['headers']:
                    st.subheader("🏷️ Headers Structure")
                    for level, headers in result['headers'].items():
                        with st.expander(f"{level.upper()} Headers ({len(headers)} found)"):
                            for i, header in enumerate(headers, 1):
                                confidence_text = f" (Confidence: {header['confidence']:.2%})" if header['confidence'] else ""
                                st.write(f"**{i}.** {header['content']}{confidence_text}")
                
                # Paragraphs
                if result['paragraphs']:
                    st.subheader("📄 Paragraphs")
                    for i, para in enumerate(result['paragraphs'][:10], 1):  # Show first 10
                        role_text = f" *[{para['role']}]*" if para['role'] else ""
                        confidence_text = f" (Confidence: {para['confidence']:.2%})" if para['confidence'] else ""
                        st.write(f"**Paragraph {i}**{role_text}{confidence_text}")
                        st.write(para['content'])
                        st.divider()
                    
                    if len(result['paragraphs']) > 10:
                        st.info(f"Showing first 10 paragraphs. Total: {len(result['paragraphs'])}")
            
            with tab3:
                st.header("🧮 Mathematical Formulas")
                
                if result['formulas']:
                    for i, formula in enumerate(result['formulas'], 1):
                        confidence_text = f" (Confidence: {formula['confidence']:.2%})" if formula['confidence'] else ""
                        kind_text = f" *[{formula['kind']}]*" if formula['kind'] else ""
                        st.write(f"**Formula {i}**{kind_text}{confidence_text}")
                        st.code(formula['content'])
                        if formula['bounding_regions']:
                            pages = [str(region['page_number']) for region in formula['bounding_regions']]
                            st.caption(f"Found on page(s): {', '.join(pages)}")
                        st.divider()
                else:
                    st.info("No formulas detected in the document.")
            
            with tab4:
                st.header("📊 Tables")
                
                if result['tables']:
                    for i, table in enumerate(result['tables'], 1):
                        confidence_text = f" (Confidence: {table['confidence']:.2%})" if table['confidence'] else ""
                        st.write(f"**Table {i}**{confidence_text}")
                        st.write(f"Dimensions: {table['row_count']} rows × {table['column_count']} columns")
                        
                        # Create a displayable table from cells
                        if table['cells']:
                            # Initialize table matrix
                            table_matrix = [["" for _ in range(table['column_count'])] for _ in range(table['row_count'])]
                            
                            # Fill the matrix with cell content
                            for cell in table['cells']:
                                if cell['row_index'] < table['row_count'] and cell['column_index'] < table['column_count']:
                                    table_matrix[cell['row_index']][cell['column_index']] = cell['content']
                            
                            # Display the table
                            st.table(table_matrix)
                        
                        st.divider()
                else:
                    st.info("No tables detected in the document.")
            
            with tab5:
                st.header("🗂️ Document Structure")
                
                # Key-value pairs
                if result['key_value_pairs']:
                    st.subheader("🔑 Key-Value Pairs")
                    for kv in result['key_value_pairs'][:20]:  # Show first 20
                        confidence_text = f" (Confidence: {kv['confidence']:.2%})" if kv['confidence'] else ""
                        st.write(f"**{kv['key']}:** {kv['value']}{confidence_text}")
                    
                    if len(result['key_value_pairs']) > 20:
                        st.info(f"Showing first 20 key-value pairs. Total: {len(result['key_value_pairs'])}")
                
                # Page information
                if result['pages']:
                    st.subheader("📄 Page Details")
                    for page in result['pages']:
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric(f"Page {page['page_number']} - Width", f"{page['width']:.1f}")
                        with col2:
                            st.metric("Height", f"{page['height']:.1f}")
                        with col3:
                            st.metric("Lines", page['lines_count'])
                        with col4:
                            st.metric("Words", page['words_count'])
            
            with tab6:
                st.header("📐 Technical Details")
                
                # Document metadata
                st.subheader("📊 Document Metadata")
                metadata = result['document_metadata']
                st.json({
                    "Model ID": metadata['model_id'],
                    "File Name": metadata['file_name'],
                    "File Size (bytes)": metadata['file_size_bytes'],
                    "Total Pages": metadata['total_pages'],
                    "Content Length": metadata['content_length']
                })
                
                # Bounding boxes summary
                if result['bounding_boxes']:
                    st.subheader("📦 Bounding Boxes Summary")
                    st.write(f"Total bounding boxes detected: {len(result['bounding_boxes'])}")
                    
                    # Show sample bounding boxes
                    with st.expander("View Sample Bounding Boxes"):
                        for i, bbox in enumerate(result['bounding_boxes'][:5], 1):
                            st.write(f"**Element {i}** ({bbox['element_type']})")
                            st.write(f"Page: {bbox['page_number']}, Content: {bbox['content'][:100]}...")
                
                # Raw data download
                st.subheader("💾 Download Raw Data")
                st.download_button(
                    label="📥 Download Full Analysis Results (JSON)",
                    data=json.dumps(result, indent=2, default=str),
                    file_name=f"analysis_{uploaded_file.name.replace('.pdf', '')}.json",
                    mime="application/json"
                )
                
        except DocumentIntelligenceError as e:
            st.error(f"❌ Document Intelligence Error: {str(e)}")
            st.info("💡 Please check your Azure configuration and try again.")
        
        except Exception as e:
            st.error(f"❌ Unexpected Error: {str(e)}")
            st.info("💡 Please check your configuration and try again.")

else:
    st.info("👆 Please upload a PDF document to begin analysis.")
    
    # Help section
    with st.expander("ℹ️ How to use this application"):
        st.markdown("""
        ### Setup Instructions:
        1. **Azure Document Intelligence Resource**: Create an Azure Document Intelligence resource in the Azure portal
        2. **Get Endpoint**: Copy the endpoint URL from your resource
        3. **Authentication**: Choose between:
           - **Managed Identity** (recommended for production): Ensure you're authenticated with Azure CLI
           - **API Key**: Get the key from your Azure resource and enter it in the sidebar
        
        ### What this application extracts:
        - 📝 **Paragraphs**: All text content with role classification
        - 🏷️ **Headers**: Organized by hierarchy levels (H1, H2, etc.)
        - 🧮 **Formulas**: Mathematical expressions and equations
        - 📊 **Tables**: Structured data with rows and columns
        - 🔑 **Key-Value Pairs**: Detected form fields
        - 📦 **Bounding Boxes**: Coordinate information for all elements
        - 📄 **Page Information**: Dimensions and content statistics
        
        ### Supported Features:
        - ✅ High-resolution analysis
        - ✅ Formula detection
        - ✅ Multi-page documents
        - ✅ PDF validation
        - ✅ Comprehensive error handling
        """)