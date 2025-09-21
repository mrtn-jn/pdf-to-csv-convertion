"""
Data cleaning and standardization utilities for credit card statements.
"""
import re
from datetime import datetime, date
from typing import List, Optional, Tuple, Dict, Any
from decimal import Decimal, InvalidOperation
import logging

try:
    from ..models import Transaction, ProcessedStatement
except ImportError:
    from models.statement_data import Transaction, ProcessedStatement

logger = logging.getLogger(__name__)


class DataCleaner:
    """Utility class for cleaning and standardizing transaction data"""

    def __init__(self):
        # Common merchant name standardizations
        self.merchant_standardizations = {
            # Gas stations
            r'shell\s*\d*': 'Shell',
            r'exxon\s*mobil\s*\d*': 'ExxonMobil',
            r'bp\s*\d*': 'BP',
            r'chevron\s*\d*': 'Chevron',
            r'texaco\s*\d*': 'Texaco',

            # Grocery stores
            r'walmart\s*supercenter\s*\d*': 'Walmart',
            r'target\s*\d*': 'Target',
            r'kroger\s*\d*': 'Kroger',
            r'safeway\s*\d*': 'Safeway',
            r'whole\s*foods\s*\d*': 'Whole Foods',

            # Restaurants
            r'mcdonald\'?s\s*\d*': "McDonald's",
            r'starbucks\s*\d*': 'Starbucks',
            r'subway\s*\d*': 'Subway',
            r'taco\s*bell\s*\d*': 'Taco Bell',
            r'pizza\s*hut\s*\d*': 'Pizza Hut',

            # Online services
            r'amazon\.com\*?\w*': 'Amazon',
            r'amzn\s*mktp\s*us': 'Amazon',
            r'paypal\s*\*?\w*': 'PayPal',
            r'netflix\.com': 'Netflix',
            r'spotify\s*\w*': 'Spotify',

            # Utilities
            r'electric\s*company\s*\d*': 'Electric Company',
            r'gas\s*company\s*\d*': 'Gas Company',
            r'water\s*dept\s*\d*': 'Water Department',
        }

        # Compile regex patterns for better performance
        self.merchant_patterns = {
            re.compile(pattern, re.IGNORECASE): replacement
            for pattern, replacement in self.merchant_standardizations.items()
        }

        # Category mapping based on merchant patterns
        self.category_patterns = {
            'Gas': [
                re.compile(r'shell|exxon|bp|chevron|texaco|gas\s*station', re.IGNORECASE),
                re.compile(r'fuel|gasoline', re.IGNORECASE)
            ],
            'Groceries': [
                re.compile(r'walmart|target|kroger|safeway|whole\s*foods|grocery', re.IGNORECASE),
                re.compile(r'supermarket|food\s*store', re.IGNORECASE)
            ],
            'Restaurants': [
                re.compile(r'mcdonald|starbucks|subway|taco\s*bell|pizza|restaurant', re.IGNORECASE),
                re.compile(r'food|dining|cafe|bistro', re.IGNORECASE)
            ],
            'Online Shopping': [
                re.compile(r'amazon|ebay|etsy|online', re.IGNORECASE),
                re.compile(r'amzn\s*mktp', re.IGNORECASE)
            ],
            'Entertainment': [
                re.compile(r'netflix|spotify|hulu|disney|movie|theater', re.IGNORECASE),
                re.compile(r'entertainment|streaming', re.IGNORECASE)
            ],
            'Utilities': [
                re.compile(r'electric|gas\s*company|water|utility|power', re.IGNORECASE),
                re.compile(r'phone|internet|cable', re.IGNORECASE)
            ],
            'Transportation': [
                re.compile(r'uber|lyft|taxi|bus|metro|transit', re.IGNORECASE),
                re.compile(r'parking|toll', re.IGNORECASE)
            ],
            'Healthcare': [
                re.compile(r'pharmacy|cvs|walgreens|hospital|medical', re.IGNORECASE),
                re.compile(r'doctor|dentist|clinic', re.IGNORECASE)
            ]
        }

    def clean_statement(self, statement: ProcessedStatement) -> ProcessedStatement:
        """
        Clean and standardize an entire statement.

        Args:
            statement: Raw processed statement

        Returns:
            Cleaned statement with standardized data
        """
        cleaned_transactions = []

        for transaction in statement.transactions:
            cleaned_transaction = self.clean_transaction(transaction)
            if cleaned_transaction:  # Only include valid transactions
                cleaned_transactions.append(cleaned_transaction)

        # Update the statement with cleaned transactions
        statement.transactions = cleaned_transactions

        # Add processing note
        statement.processing_notes.append(
            f"Data cleaning applied: {len(cleaned_transactions)} transactions processed"
        )

        return statement

    def clean_transaction(self, transaction: Transaction) -> Optional[Transaction]:
        """
        Clean and standardize a single transaction.

        Args:
            transaction: Raw transaction data

        Returns:
            Cleaned transaction or None if invalid
        """
        try:
            # Clean description
            cleaned_description = self.clean_description(transaction.description)
            if not cleaned_description.strip():
                logger.warning(f"Transaction with empty description after cleaning: {transaction}")
                return None

            # Standardize merchant name
            standardized_description = self.standardize_merchant_name(cleaned_description)

            # Auto-categorize if category is not set
            category = transaction.category or self.auto_categorize(standardized_description)

            # Validate and clean amount
            cleaned_amount = self.clean_amount(transaction.amount)

            # Validate date
            if not self.is_valid_date(transaction.date):
                logger.warning(f"Invalid date in transaction: {transaction.date}")
                return None

            return Transaction(
                date=transaction.date,
                description=standardized_description,
                amount=cleaned_amount,
                transaction_type=transaction.transaction_type,
                category=category,
                reference=transaction.reference
            )

        except Exception as e:
            logger.error(f"Error cleaning transaction: {e}")
            return None

    def clean_description(self, description: str) -> str:
        """
        Clean transaction description.

        Args:
            description: Raw description

        Returns:
            Cleaned description
        """
        if not description:
            return ""

        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', description.strip())

        # Remove common noise patterns
        noise_patterns = [
            r'^\d{2}/\d{2}\s*',  # Remove date prefix
            r'\s*\d{4}\s*$',     # Remove trailing year
            r'[#*]+\d*',         # Remove reference numbers with # or *
            r'\s*\$\d+\.?\d*\s*', # Remove embedded amounts
            r'\s+$',             # Trailing spaces
            r'^\s+',             # Leading spaces
        ]

        for pattern in noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Normalize case - title case for most words, but preserve common abbreviations
        words = cleaned.split()
        normalized_words = []

        for word in words:
            # Preserve common abbreviations in uppercase
            if word.upper() in ['ATM', 'POS', 'ACH', 'API', 'LLC', 'INC', 'USA', 'US']:
                normalized_words.append(word.upper())
            # Preserve state abbreviations
            elif len(word) == 2 and word.upper() in self._get_state_abbreviations():
                normalized_words.append(word.upper())
            else:
                # Title case for regular words
                normalized_words.append(word.capitalize())

        return ' '.join(normalized_words)

    def standardize_merchant_name(self, description: str) -> str:
        """
        Standardize merchant names using common patterns.

        Args:
            description: Transaction description

        Returns:
            Description with standardized merchant name
        """
        for pattern, replacement in self.merchant_patterns.items():
            if pattern.search(description):
                return pattern.sub(replacement, description)

        return description

    def auto_categorize(self, description: str) -> Optional[str]:
        """
        Automatically categorize transaction based on description.

        Args:
            description: Transaction description

        Returns:
            Category name or None if no match
        """
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if pattern.search(description):
                    return category

        return None

    def clean_amount(self, amount: float) -> float:
        """
        Clean and validate transaction amount.

        Args:
            amount: Raw amount

        Returns:
            Cleaned amount rounded to 2 decimal places
        """
        try:
            # Use Decimal for precise arithmetic
            decimal_amount = Decimal(str(amount))
            # Round to 2 decimal places
            cleaned = float(decimal_amount.quantize(Decimal('0.01')))
            return cleaned
        except (InvalidOperation, ValueError):
            logger.warning(f"Invalid amount: {amount}, defaulting to 0.00")
            return 0.0

    def is_valid_date(self, transaction_date: date) -> bool:
        """
        Validate transaction date.

        Args:
            transaction_date: Transaction date

        Returns:
            True if date is valid and reasonable
        """
        if not transaction_date:
            return False

        # Check if date is reasonable (not too old or in future)
        today = date.today()
        min_date = date(today.year - 10, 1, 1)  # 10 years ago
        max_date = date(today.year + 1, 12, 31)  # 1 year in future

        return min_date <= transaction_date <= max_date

    def deduplicate_transactions(self, transactions: List[Transaction]) -> List[Transaction]:
        """
        Remove duplicate transactions based on date, description, and amount.

        Args:
            transactions: List of transactions

        Returns:
            Deduplicated list of transactions
        """
        seen = set()
        unique_transactions = []

        for transaction in transactions:
            # Create a hash key from key fields
            key = (
                transaction.date,
                transaction.description.strip().lower(),
                abs(transaction.amount)  # Use absolute value to catch amount sign variations
            )

            if key not in seen:
                seen.add(key)
                unique_transactions.append(transaction)
            else:
                logger.info(f"Duplicate transaction removed: {transaction.description}")

        return unique_transactions

    def validate_transaction_data(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """
        Validate transaction data and return statistics.

        Args:
            transactions: List of transactions to validate

        Returns:
            Dictionary with validation statistics
        """
        stats = {
            'total_transactions': len(transactions),
            'valid_transactions': 0,
            'invalid_dates': 0,
            'zero_amounts': 0,
            'empty_descriptions': 0,
            'warnings': []
        }

        for transaction in transactions:
            is_valid = True

            # Check date validity
            if not self.is_valid_date(transaction.date):
                stats['invalid_dates'] += 1
                is_valid = False

            # Check for zero amounts
            if transaction.amount == 0:
                stats['zero_amounts'] += 1

            # Check for empty descriptions
            if not transaction.description.strip():
                stats['empty_descriptions'] += 1
                is_valid = False

            if is_valid:
                stats['valid_transactions'] += 1

        # Generate warnings
        if stats['invalid_dates'] > 0:
            stats['warnings'].append(f"{stats['invalid_dates']} transactions have invalid dates")

        if stats['zero_amounts'] > stats['total_transactions'] * 0.05:  # More than 5%
            stats['warnings'].append(f"High number of zero-amount transactions: {stats['zero_amounts']}")

        if stats['empty_descriptions'] > 0:
            stats['warnings'].append(f"{stats['empty_descriptions']} transactions have empty descriptions")

        return stats

    def _get_state_abbreviations(self) -> set:
        """Get set of US state abbreviations"""
        return {
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
        }