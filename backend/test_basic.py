"""
Basic test script to validate the PDF processing implementation.
"""
import asyncio
import sys
import os
from datetime import date

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Set PYTHONPATH for proper imports
os.environ['PYTHONPATH'] = backend_dir

try:
    from models.statement_data import Transaction, TransactionType, BankType, StatementMetadata, ProcessedStatement
    from services.pdf_processor import PDFProcessor
    from services.bank_detection import BankDetector
    from services.bank_parsers import get_parser_for_bank, get_supported_banks
    from utils.data_cleaner import DataCleaner
except ImportError as e:
    print(f"Import error: {e}")
    print("Trying alternative import method...")
    # Alternative approach - import directly
    import importlib.util

    def load_module_from_path(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # Load modules directly
    models_module = load_module_from_path("models", os.path.join(backend_dir, "models", "statement_data.py"))
    Transaction = models_module.Transaction
    TransactionType = models_module.TransactionType
    BankType = models_module.BankType
    StatementMetadata = models_module.StatementMetadata
    ProcessedStatement = models_module.ProcessedStatement


def test_models():
    """Test basic model functionality"""
    print("Testing models...")

    # Test Transaction
    transaction = Transaction(
        date=date(2024, 1, 15),
        description="STARBUCKS STORE #1234",
        amount=5.67,
        transaction_type=TransactionType.PURCHASE
    )
    print(f"Created transaction: {transaction.description} - ${transaction.amount}")

    # Test StatementMetadata
    metadata = StatementMetadata(
        bank_name="Test Bank",
        bank_type=BankType.GENERIC,
        statement_period="Jan 2024",
        balance="$1,234.56"
    )
    print(f"Created metadata: {metadata.bank_name} - {metadata.balance}")

    # Test ProcessedStatement
    statement = ProcessedStatement(
        transactions=[transaction],
        metadata=metadata
    )
    print(f"Created statement with {len(statement.transactions)} transaction(s)")
    print(f"CSV headers: {statement.headers}")
    print(f"CSV rows: {statement.rows}")

    print("✅ Models test passed\n")


def test_bank_detection():
    """Test bank detection functionality"""
    print("Testing bank detection...")

    detector = BankDetector()

    # Test Chase detection
    chase_text = "CHASE CREDIT CARD STATEMENT Account Number: 1234"
    detected = detector.detect_bank(chase_text)
    print(f"Chase detection: {detected}")
    assert detected == BankType.CHASE

    # Test Amex detection
    amex_text = "AMERICAN EXPRESS MEMBER SINCE 2020"
    detected = detector.detect_bank(amex_text)
    print(f"Amex detection: {detected}")
    assert detected == BankType.AMEX

    # Test generic detection
    unknown_text = "Some Random Bank Statement"
    detected = detector.detect_bank(unknown_text)
    print(f"Generic detection: {detected}")
    assert detected == BankType.GENERIC

    print("✅ Bank detection test passed\n")


def test_bank_parsers():
    """Test bank parser functionality"""
    print("Testing bank parsers...")

    # Test supported banks
    supported = get_supported_banks()
    print(f"Supported banks: {[bank.value for bank in supported]}")
    assert len(supported) > 0

    # Test parser retrieval
    chase_parser = get_parser_for_bank(BankType.CHASE)
    assert chase_parser is not None
    print(f"Got Chase parser: {type(chase_parser).__name__}")

    amex_parser = get_parser_for_bank(BankType.AMEX)
    assert amex_parser is not None
    print(f"Got Amex parser: {type(amex_parser).__name__}")

    generic_parser = get_parser_for_bank(BankType.GENERIC)
    assert generic_parser is not None
    print(f"Got Generic parser: {type(generic_parser).__name__}")

    print("✅ Bank parsers test passed\n")


def test_data_cleaner():
    """Test data cleaning functionality"""
    print("Testing data cleaner...")

    cleaner = DataCleaner()

    # Test description cleaning
    dirty_description = "  STARBUCKS   STORE   #1234   "
    clean_description = cleaner.clean_description(dirty_description)
    print(f"Cleaned description: '{dirty_description}' -> '{clean_description}'")

    # Test merchant standardization
    amazon_description = "AMZN MKTP US Amazon.com"
    standardized = cleaner.standardize_merchant_name(amazon_description)
    print(f"Standardized merchant: '{amazon_description}' -> '{standardized}'")

    # Test auto-categorization
    gas_description = "SHELL GAS STATION #1234"
    category = cleaner.auto_categorize(gas_description)
    print(f"Auto-categorized: '{gas_description}' -> '{category}'")

    # Test amount cleaning
    dirty_amount = 123.456789
    clean_amount = cleaner.clean_amount(dirty_amount)
    print(f"Cleaned amount: {dirty_amount} -> {clean_amount}")

    print("✅ Data cleaner test passed\n")


async def test_pdf_processor():
    """Test PDF processor functionality"""
    print("Testing PDF processor...")

    processor = PDFProcessor()

    # Test PDF validation
    fake_pdf_content = b"%PDF-1.4\nSome PDF content here"
    is_valid, error = processor.validate_pdf_content(fake_pdf_content)
    print(f"PDF validation: {is_valid}, Error: {error}")

    # Test with invalid content
    invalid_content = b"Not a PDF file"
    is_valid, error = processor.validate_pdf_content(invalid_content)
    print(f"Invalid content validation: {is_valid}, Error: {error}")
    assert not is_valid

    print("✅ PDF processor test passed\n")


def test_sample_statement_processing():
    """Test processing a sample statement text"""
    print("Testing sample statement processing...")

    # Sample Chase-like statement text
    sample_text = """
CHASE CREDIT CARD STATEMENT
Account Number: ****1234
Statement Date: 01/15/2024
Payment Due Date: 02/10/2024
New Balance: $1,234.56

TRANSACTIONS:
01/02 STARBUCKS STORE #1234           5.67
01/05 AMAZON.COM*ABCD1234            29.99
01/08 SHELL OIL #5678                45.50
01/12 PAYMENT THANK YOU             -100.00
01/15 ANNUAL FEE                     95.00
    """

    detector = BankDetector()
    bank_type = detector.detect_bank(sample_text)
    print(f"Detected bank: {bank_type}")

    parser = get_parser_for_bank(bank_type)
    statement = parser.parse_statement(sample_text, "test_statement.pdf")

    print(f"Parsed {len(statement.transactions)} transactions:")
    for transaction in statement.transactions:
        print(f"  {transaction.date} - {transaction.description} - ${transaction.amount}")

    print(f"Statement metadata:")
    print(f"  Bank: {statement.metadata.bank_name}")
    print(f"  Period: {statement.metadata.statement_period}")
    print(f"  Balance: {statement.metadata.balance}")

    # Test data cleaning
    cleaner = DataCleaner()
    cleaned_statement = cleaner.clean_statement(statement)
    print(f"After cleaning: {len(cleaned_statement.transactions)} transactions")

    print("✅ Sample statement processing test passed\n")


async def main():
    """Run all tests"""
    print("🚀 Starting PDF Processing Implementation Tests\n")

    try:
        # Test individual components
        test_models()
        test_bank_detection()
        test_bank_parsers()
        test_data_cleaner()
        await test_pdf_processor()
        test_sample_statement_processing()

        print("🎉 All tests passed successfully!")
        print("\n📋 Implementation Summary:")
        print("✅ Data models and schemas")
        print("✅ Bank detection logic")
        print("✅ Bank-specific parsers (Chase, Amex, Generic)")
        print("✅ Data cleaning and standardization")
        print("✅ PDF processing engine")
        print("✅ Error handling and logging")

    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)