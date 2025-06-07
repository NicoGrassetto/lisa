# Azure Document Intelligence - Layout Model Streamlit App

This Streamlit application allows you to upload documents and extract structured information using Azure AI Document Intelligence Layout model. The app outputs the analysis results as JSON.

## Supported File Types

- **PDF documents**
- **Images**: JPEG, PNG, BMP, TIFF, HEIF
- **Microsoft Office**: DOCX, XLSX, PPTX
- **HTML files**

## Features

- 📤 File upload with support for all Azure Document Intelligence compatible formats
- 🔍 Document analysis using the prebuilt Layout model
- 📊 Summary of extracted elements (pages, tables, paragraphs)
- 📄 Text content preview
- 💾 JSON download of complete analysis results
- 🔐 Secure authentication with Managed Identity (recommended) or API key

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Azure Document Intelligence Setup

1. Create an Azure Document Intelligence resource in the Azure portal
2. Get your endpoint URL from the resource overview page

### 3. Authentication

#### Option A: Managed Identity (Recommended for Production)
- Deploy to Azure with a managed identity assigned
- Grant the managed identity "Cognitive Services User" role on the Document Intelligence resource

#### Option B: API Key (Development Only)
Set the environment variable:
```bash
$env:DOCUMENT_INTELLIGENCE_KEY = "your-api-key"
```

### 4. Set Endpoint
Set the environment variable:
```bash
$env:DOCUMENT_INTELLIGENCE_ENDPOINT = "https://your-resource.cognitiveservices.azure.com/"
```

## Running the App

```bash
streamlit run app.py
```

## Usage

1. **Configure**: Enter your Azure Document Intelligence endpoint in the sidebar
2. **Upload**: Choose a supported file type and upload your document
3. **Analyze**: Click "Analyze Document" to process the file
4. **Results**: View the summary and download the complete JSON results

## Output

The app extracts and provides:
- Complete text content
- Page-by-page layout information
- Table structures with cell data
- Paragraph organization
- Bounding box coordinates for all elements
- Comprehensive JSON output for further processing

## Security Features

- ✅ Managed Identity authentication (recommended)
- ✅ Secure credential handling
- ✅ No hardcoded secrets
- ✅ Proper error handling and logging
- ✅ Retry logic with exponential backoff

## References

- [Azure Document Intelligence Documentation](https://docs.microsoft.com/en-us/azure/applied-ai-services/form-recognizer/)
- [Layout Model Overview](https://docs.microsoft.com/en-us/azure/applied-ai-services/form-recognizer/concept-layout)
- [Python SDK Reference](https://docs.microsoft.com/en-us/python/api/azure-ai-documentintelligence/)
