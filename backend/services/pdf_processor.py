"""
Core PDF processing service for credit card statements.
"""
import pdfplumber
import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from io import BytesIO
from datetime import datetime

try:
    from ..models import (
        ProcessedStatement,
        ProcessingResult,
        StatementMetadata,
        BankType,
        ParsingConfig
    )
    from .bank_detection import BankDetector
    from .bank_parsers import get_parser_for_bank
except ImportError:
    # Fallback for when running as script
    from models.statement_data import (
        ProcessedStatement,
        ProcessingResult,
        StatementMetadata,
        BankType,
        ParsingConfig
    )
    from services.bank_detection import BankDetector
    from services.bank_parsers import get_parser_for_bank

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFProcessingError(Exception):
    """Custom exception for PDF processing errors"""
    pass


class PDFProcessor:
    """Main PDF processor for credit card statements"""

    def __init__(self):
        self.bank_detector = BankDetector()
        self.config = ParsingConfig()

    async def process_pdf(self, pdf_content: bytes, filename: str = None) -> ProcessingResult:
        """
        Process a PDF file and extract credit card statement data.

        Args:
            pdf_content: Raw PDF bytes
            filename: Original filename for context

        Returns:
            ProcessingResult containing success/failure status and data
        """
        try:
            # Extract text from PDF
            extracted_text, page_count = await self._extract_text_from_pdf(pdf_content)

            if not extracted_text.strip():
                return ProcessingResult.error_response(
                    "Unable to extract text from PDF",
                    ["PDF appears to be empty or contains only images"]
                )

            # Detect bank type
            bank_type = self.bank_detector.detect_bank(extracted_text)
            logger.info(f"Detected bank type: {bank_type}")

            # Get appropriate parser
            parser = get_parser_for_bank(bank_type)
            if not parser:
                return ProcessingResult.error_response(
                    f"No parser available for bank type: {bank_type}",
                    ["Unsupported bank format detected"]
                )

            # Parse the statement
            statement = parser.parse_statement(extracted_text, filename)

            if not statement.transactions:
                return ProcessingResult.error_response(
                    "No transactions found in the statement",
                    ["Statement may be in an unsupported format or corrupted"]
                )

            # Update metadata
            statement.metadata.total_transactions = len(statement.transactions)
            statement.raw_text = extracted_text

            logger.info(f"Successfully processed {len(statement.transactions)} transactions")

            return ProcessingResult.success_response(statement)

        except PDFProcessingError as e:
            logger.error(f"PDF processing error: {str(e)}")
            return ProcessingResult.error_response(
                "Failed to process PDF",
                [str(e)]
            )
        except Exception as e:
            logger.error(f"Unexpected error processing PDF: {str(e)}")
            return ProcessingResult.error_response(
                "An unexpected error occurred while processing the PDF",
                [f"Internal error: {type(e).__name__}"]
            )

    async def _extract_text_from_pdf(self, pdf_content: bytes) -> Tuple[str, int]:
        """
        Extract text from PDF using pdfplumber.

        Args:
            pdf_content: Raw PDF bytes

        Returns:
            Tuple of (extracted_text, page_count)
        """
        try:
            pdf_file = BytesIO(pdf_content)
            extracted_text = ""
            page_count = 0

            with pdfplumber.open(pdf_file) as pdf:
                page_count = len(pdf.pages)

                if page_count == 0:
                    raise PDFProcessingError("PDF contains no pages")

                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += f"--- Page {page_num} ---\n{page_text}\n\n"
                        else:
                            # Try extracting from tables if regular text extraction fails
                            tables = page.extract_tables()
                            if tables:
                                for table in tables:
                                    for row in table:
                                        if row and any(cell for cell in row if cell):
                                            extracted_text += " | ".join(str(cell) if cell else "" for cell in row) + "\n"
                                extracted_text += "\n"
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {str(e)}")
                        continue

            if not extracted_text.strip():
                raise PDFProcessingError("No text could be extracted from the PDF")

            return extracted_text, page_count

        except Exception as e:
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Failed to process PDF file: {str(e)}")

    def validate_pdf_content(self, content: bytes, max_size_mb: int = 50) -> Tuple[bool, Optional[str]]:
        """
        Validate PDF content before processing.

        Args:
            content: PDF content bytes
            max_size_mb: Maximum allowed file size in MB

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        size_mb = len(content) / (1024 * 1024)
        if size_mb > max_size_mb:
            return False, f"File size ({size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb}MB)"

        # Check for PDF signature
        if not content.startswith(b'%PDF-'):
            return False, "File does not appear to be a valid PDF"

        # Check minimum size
        if len(content) < 1024:  # 1KB minimum
            return False, "PDF file appears to be too small or corrupted"

        return True, None

    async def get_processing_stats(self, result: ProcessingResult) -> Dict[str, Any]:
        """
        Get processing statistics from result.

        Args:
            result: Processing result

        Returns:
            Dictionary with processing statistics
        """
        if not result.success or not result.data:
            return {
                "success": False,
                "transactions_processed": 0,
                "processing_time": None
            }

        metadata = result.data.get("metadata", {})
        return {
            "success": True,
            "transactions_processed": metadata.get("totalTransactions", 0),
            "bank_detected": metadata.get("bankName", "Unknown"),
            "statement_period": metadata.get("statementPeriod", "Unknown"),
            "balance": metadata.get("balance", "Unknown")
        }