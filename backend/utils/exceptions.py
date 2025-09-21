"""
Custom exceptions for the PDF to CSV converter.
"""


class PDFConverterError(Exception):
    """Base exception for PDF converter errors"""

    def __init__(self, message: str, code: str = None, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class PDFProcessingError(PDFConverterError):
    """Raised when PDF processing fails"""
    pass


class BankDetectionError(PDFConverterError):
    """Raised when bank detection fails"""
    pass


class TransactionParsingError(PDFConverterError):
    """Raised when transaction parsing fails"""
    pass


class DataValidationError(PDFConverterError):
    """Raised when data validation fails"""
    pass


class FileValidationError(PDFConverterError):
    """Raised when file validation fails"""
    pass


class UnsupportedBankError(PDFConverterError):
    """Raised when an unsupported bank format is detected"""
    pass


class ConfigurationError(PDFConverterError):
    """Raised when there are configuration issues"""
    pass


# Error codes for client-side handling
ERROR_CODES = {
    'INVALID_FILE_TYPE': 'INVALID_FILE_TYPE',
    'FILE_TOO_LARGE': 'FILE_TOO_LARGE',
    'CORRUPTED_PDF': 'CORRUPTED_PDF',
    'NO_TEXT_EXTRACTED': 'NO_TEXT_EXTRACTED',
    'BANK_NOT_DETECTED': 'BANK_NOT_DETECTED',
    'UNSUPPORTED_BANK': 'UNSUPPORTED_BANK',
    'NO_TRANSACTIONS_FOUND': 'NO_TRANSACTIONS_FOUND',
    'PARSING_FAILED': 'PARSING_FAILED',
    'DATA_VALIDATION_FAILED': 'DATA_VALIDATION_FAILED',
    'PROCESSING_TIMEOUT': 'PROCESSING_TIMEOUT',
    'INTERNAL_ERROR': 'INTERNAL_ERROR'
}


def create_error_response(error: PDFConverterError) -> dict:
    """
    Create a standardized error response from a custom exception.

    Args:
        error: Custom exception instance

    Returns:
        Dictionary with error details
    """
    return {
        'success': False,
        'message': error.message,
        'code': error.code,
        'details': error.details,
        'errors': [error.message]
    }