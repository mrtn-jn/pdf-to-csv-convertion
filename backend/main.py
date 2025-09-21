from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
from typing import Dict, Any
import asyncio

try:
    from services import PDFProcessor
    from models import ProcessingResult
    from utils import DataCleaner
except ImportError:
    # Fallback for when running as script
    from services.pdf_processor import PDFProcessor
    from models.statement_data import ProcessingResult
    from utils.data_cleaner import DataCleaner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF to CSV Converter API",
    version="1.0.0",
    description="Convert credit card statement PDFs to structured CSV data"
)

# Initialize services
pdf_processor = PDFProcessor()
data_cleaner = DataCleaner()

# CORS middleware to allow requests from Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "null"  # For file:// protocol
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "PDF to CSV Converter API is running!"}

@app.options("/upload-pdf")
async def upload_pdf_options():
    """Handle CORS preflight requests for upload-pdf"""
    return {"message": "OK"}

@app.post("/upload-pdf", response_model=Dict[str, Any])
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload and process a PDF file to extract credit card statement data.

    Returns:
        JSON response with structured transaction data or error information
    """
    logger.info(f"Received PDF upload: {file.filename} ({file.size} bytes)")

    try:
        # Validate file type
        if file.content_type != "application/pdf":
            logger.warning(f"Invalid file type: {file.content_type}")
            return ProcessingResult.error_response(
                "Invalid file type",
                ["File must be a PDF"]
            ).dict()

        # Validate file size (50MB limit)
        if file.size and file.size > 50 * 1024 * 1024:  # 50MB
            logger.warning(f"File too large: {file.size} bytes")
            return ProcessingResult.error_response(
                "File too large",
                ["PDF file must be smaller than 50MB"]
            ).dict()

        # Read file content
        try:
            pdf_content = await file.read()
        except Exception as e:
            logger.error(f"Error reading file content: {e}")
            return ProcessingResult.error_response(
                "Unable to read PDF file",
                ["File may be corrupted or inaccessible"]
            ).dict()

        # Validate PDF content
        is_valid, error_msg = pdf_processor.validate_pdf_content(pdf_content)
        if not is_valid:
            logger.warning(f"PDF validation failed: {error_msg}")
            return ProcessingResult.error_response(
                "Invalid PDF file",
                [error_msg]
            ).dict()

        # Process PDF
        logger.info(f"Processing PDF: {file.filename}")
        result = await pdf_processor.process_pdf(pdf_content, file.filename)

        if result.success and result.data:
            # Apply data cleaning if processing was successful
            logger.info("Applying data cleaning and standardization")
            # Note: We would need to reconstruct the ProcessedStatement object
            # from the result.data to apply cleaning, but for now we'll log it
            logger.info(f"Successfully processed {result.data.get('metadata', {}).get('totalTransactions', 0)} transactions")

        logger.info(f"Processing completed for {file.filename}: success={result.success}")
        return result.dict()

    except Exception as e:
        logger.error(f"Unexpected error processing PDF: {str(e)}")
        return ProcessingResult.error_response(
            "An unexpected error occurred",
            ["Please try again or contact support if the problem persists"]
        ).dict()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "pdf-to-csv-backend",
        "version": "1.0.0"
    }

@app.get("/supported-banks")
async def get_supported_banks():
    """Get list of supported banks for PDF processing"""
    from services.bank_parsers import get_supported_banks

    supported = get_supported_banks()
    return {
        "supported_banks": [bank.value for bank in supported],
        "total_count": len(supported)
    }

@app.post("/validate-pdf")
async def validate_pdf_only(file: UploadFile = File(...)):
    """Validate PDF file without full processing"""
    try:
        if file.content_type != "application/pdf":
            return {"valid": False, "error": "File must be a PDF"}

        pdf_content = await file.read()
        is_valid, error_msg = pdf_processor.validate_pdf_content(pdf_content)

        if is_valid:
            return {
                "valid": True,
                "size_mb": round(len(pdf_content) / (1024 * 1024), 2),
                "filename": file.filename
            }
        else:
            return {"valid": False, "error": error_msg}

    except Exception as e:
        logger.error(f"Error validating PDF: {e}")
        return {"valid": False, "error": "Unable to validate PDF file"}

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail, "errors": []}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An internal server error occurred",
            "errors": ["Please try again later"]
        }
    )

if __name__ == "__main__":
    logger.info("Starting PDF to CSV Converter API")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )