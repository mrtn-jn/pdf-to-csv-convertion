"""
Base parser class for credit card statement processing.
"""
import re
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Optional, Dict, Tuple, Any
import logging

try:
    from ...models import (
        ProcessedStatement,
        Transaction,
        TransactionType,
        StatementMetadata,
        BankType,
        ParsingConfig
    )
except ImportError:
    # Fallback for when running as script
    from models.statement_data import (
        ProcessedStatement,
        Transaction,
        TransactionType,
        StatementMetadata,
        BankType,
        ParsingConfig
    )

logger = logging.getLogger(__name__)


class BaseStatementParser(ABC):
    """Abstract base class for credit card statement parsers"""

    def __init__(self, bank_type: BankType):
        self.bank_type = bank_type
        self.config = ParsingConfig(bank_type=bank_type)

        # Common regex patterns
        self.date_patterns = [
            re.compile(r'(\d{1,2})/(\d{1,2})/(\d{2,4})'),  # MM/DD/YYYY or MM/DD/YY
            re.compile(r'(\d{1,2})-(\d{1,2})-(\d{2,4})'),  # MM-DD-YYYY
            re.compile(r'(\d{2,4})-(\d{1,2})-(\d{1,2})'),  # YYYY-MM-DD
            re.compile(r'([A-Za-z]{3})\s+(\d{1,2}),?\s+(\d{2,4})'),  # Jan 15, 2024
        ]

        # Common amount patterns with optional currency symbols
        self.amount_patterns = [
            re.compile(r'\$?\s*([0-9,]+\.?\d{0,2})\s*(?:CR|DB)?', re.IGNORECASE),
            re.compile(r'([0-9,]+\.?\d{0,2})\s*\$?', re.IGNORECASE),
            re.compile(r'\$\s*([0-9,]+\.?\d{0,2})', re.IGNORECASE),
        ]

        # Transaction type patterns
        self.transaction_type_patterns = {
            TransactionType.PAYMENT: [
                re.compile(r'payment\s+thank\s+you', re.IGNORECASE),
                re.compile(r'autopay', re.IGNORECASE),
                re.compile(r'online\s+payment', re.IGNORECASE),
                re.compile(r'payment\s+received', re.IGNORECASE),
            ],
            TransactionType.FEE: [
                re.compile(r'fee', re.IGNORECASE),
                re.compile(r'charge', re.IGNORECASE),
                re.compile(r'annual\s+fee', re.IGNORECASE),
                re.compile(r'late\s+fee', re.IGNORECASE),
                re.compile(r'foreign\s+transaction', re.IGNORECASE),
            ],
            TransactionType.INTEREST: [
                re.compile(r'interest', re.IGNORECASE),
                re.compile(r'finance\s+charge', re.IGNORECASE),
                re.compile(r'apr', re.IGNORECASE),
            ],
            TransactionType.CASH_ADVANCE: [
                re.compile(r'cash\s+advance', re.IGNORECASE),
                re.compile(r'atm', re.IGNORECASE),
                re.compile(r'cash\s+withdrawal', re.IGNORECASE),
            ],
            TransactionType.CREDIT: [
                re.compile(r'credit', re.IGNORECASE),
                re.compile(r'refund', re.IGNORECASE),
                re.compile(r'return', re.IGNORECASE),
            ]
        }

    @abstractmethod
    def parse_statement(self, text: str, filename: str = None) -> ProcessedStatement:
        """
        Parse statement text and return structured data.

        Args:
            text: Raw PDF text
            filename: Original filename for context

        Returns:
            ProcessedStatement with transactions and metadata
        """
        pass

    @abstractmethod
    def extract_metadata(self, text: str) -> StatementMetadata:
        """
        Extract statement metadata from text.

        Args:
            text: Raw PDF text

        Returns:
            StatementMetadata object
        """
        pass

    def extract_transactions(self, text: str) -> List[Transaction]:
        """
        Extract transactions from text using common patterns.
        Override in subclasses for bank-specific logic.

        Args:
            text: Raw PDF text

        Returns:
            List of Transaction objects
        """
        transactions = []
        lines = text.split('\n')

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or self._should_ignore_line(line):
                continue

            transaction = self._parse_transaction_line(line, line_num)
            if transaction:
                transactions.append(transaction)

        return transactions

    def _parse_transaction_line(self, line: str, line_num: int) -> Optional[Transaction]:
        """
        Parse a single line for transaction data.

        Args:
            line: Text line to parse
            line_num: Line number for debugging

        Returns:
            Transaction object or None if no valid transaction found
        """
        # Look for date pattern
        transaction_date = self._extract_date(line)
        if not transaction_date:
            return None

        # Look for amount
        amount, is_credit = self._extract_amount(line)
        if amount is None:
            return None

        # Extract description (remove date and amount from line)
        description = self._extract_description(line, transaction_date, amount)

        if not description.strip():
            return None

        # Determine transaction type
        transaction_type = self._classify_transaction_type(description)

        # Handle credit/debit logic
        if is_credit or transaction_type in [TransactionType.PAYMENT, TransactionType.CREDIT]:
            amount = -abs(amount)  # Credits are negative
        else:
            amount = abs(amount)   # Debits are positive

        return Transaction(
            date=transaction_date,
            description=description,
            amount=amount,
            transaction_type=transaction_type
        )

    def _extract_date(self, line: str) -> Optional[date]:
        """Extract date from line using common patterns"""
        for pattern in self.date_patterns:
            match = pattern.search(line)
            if match:
                try:
                    if len(match.groups()) == 3:
                        if pattern.pattern.startswith(r'([A-Za-z]{3})'):
                            # Month name format
                            month_str, day_str, year_str = match.groups()
                            month_names = {
                                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                                'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                                'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                            }
                            month = month_names.get(month_str.lower()[:3])
                            if month:
                                day = int(day_str)
                                year = int(year_str)
                                if year < 100:
                                    year += 2000
                                return date(year, month, day)
                        else:
                            # Numeric format
                            parts = [int(g) for g in match.groups()]
                            if pattern.pattern.startswith(r'(\d{2,4})'):
                                # YYYY-MM-DD format
                                year, month, day = parts
                            else:
                                # MM/DD/YYYY format
                                month, day, year = parts

                            if year < 100:
                                year += 2000

                            return date(year, month, day)
                except (ValueError, TypeError):
                    continue
        return None

    def _extract_amount(self, line: str) -> Tuple[Optional[float], bool]:
        """
        Extract amount from line and determine if it's a credit.

        Returns:
            Tuple of (amount, is_credit)
        """
        is_credit = 'CR' in line.upper() or line.count('-') > 0

        for pattern in self.amount_patterns:
            matches = pattern.findall(line)
            if matches:
                try:
                    # Take the last amount found (usually the transaction amount)
                    amount_str = matches[-1]
                    # Remove commas and convert
                    amount = float(amount_str.replace(',', ''))
                    return amount, is_credit
                except (ValueError, IndexError):
                    continue

        return None, False

    def _extract_description(self, line: str, transaction_date: date, amount: float) -> str:
        """Extract transaction description by removing date and amount"""
        description = line

        # Remove date patterns
        for pattern in self.date_patterns:
            description = pattern.sub('', description)

        # Remove amount patterns
        for pattern in self.amount_patterns:
            description = pattern.sub('', description)

        # Remove common noise
        description = re.sub(r'\s*CR\s*', '', description, flags=re.IGNORECASE)
        description = re.sub(r'\s*DB\s*', '', description, flags=re.IGNORECASE)
        description = re.sub(r'\$', '', description)
        description = re.sub(r'\s+', ' ', description)

        return description.strip()

    def _classify_transaction_type(self, description: str) -> TransactionType:
        """Classify transaction type based on description"""
        for trans_type, patterns in self.transaction_type_patterns.items():
            for pattern in patterns:
                if pattern.search(description):
                    return trans_type

        return TransactionType.PURCHASE  # Default to purchase

    def _should_ignore_line(self, line: str) -> bool:
        """Check if line should be ignored during parsing"""
        ignore_patterns = [
            r'^Page\s+\d+',
            r'^Statement\s+Date',
            r'^Account\s+Number',
            r'^Total\s+',
            r'^Balance\s+',
            r'^Previous\s+Balance',
            r'^New\s+Balance',
            r'^\s*$',
            r'^-+\s*$',
            r'^=+\s*$',
        ]

        for pattern in ignore_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True

        return False

    def _parse_date_string(self, date_str: str) -> Optional[date]:
        """Parse date string using various formats"""
        if not date_str:
            return None

        for fmt in self.config.date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        return None

    def _clean_amount_string(self, amount_str: str) -> str:
        """Clean amount string for parsing"""
        if not amount_str:
            return ""

        # Remove currency symbols and extra spaces
        cleaned = re.sub(r'[$\s]', '', amount_str)
        # Remove commas
        cleaned = cleaned.replace(',', '')

        return cleaned

    def validate_parsed_data(self, statement: ProcessedStatement) -> List[str]:
        """
        Validate parsed statement data and return list of warnings.

        Args:
            statement: Parsed statement data

        Returns:
            List of validation warnings
        """
        warnings = []

        if not statement.transactions:
            warnings.append("No transactions found in statement")

        if not statement.metadata.statement_period:
            warnings.append("Statement period not found")

        if not statement.metadata.balance:
            warnings.append("Account balance not found")

        # Check for suspicious patterns
        zero_amount_count = sum(1 for t in statement.transactions if t.amount == 0)
        if zero_amount_count > len(statement.transactions) * 0.1:  # More than 10%
            warnings.append(f"High number of zero-amount transactions ({zero_amount_count})")

        # Check date consistency
        dates = [t.date for t in statement.transactions if t.date]
        if dates:
            date_range = max(dates) - min(dates)
            if date_range.days > 35:  # More than ~1 month
                warnings.append(f"Transaction date range seems large ({date_range.days} days)")

        return warnings