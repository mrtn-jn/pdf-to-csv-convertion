"""
Generic credit card statement parser for unknown/unsupported banks.
"""
import re
from datetime import date
from typing import List, Optional

try:
    from .base_parser import BaseStatementParser
    from ...models import ProcessedStatement, StatementMetadata, BankType, Transaction, TransactionType
except ImportError:
    from services.bank_parsers.base_parser import BaseStatementParser
    from models.statement_data import ProcessedStatement, StatementMetadata, BankType, Transaction, TransactionType


class GenericParser(BaseStatementParser):
    """Generic parser for unknown credit card statements"""

    def __init__(self):
        super().__init__(BankType.GENERIC)

        # Generic patterns that work across multiple banks
        self.balance_patterns = [
            re.compile(r'(?:new|current|total|outstanding)\s+balance:?\s*\$?([0-9,]+\.?\d{0,2})', re.IGNORECASE),
            re.compile(r'balance:?\s*\$?([0-9,]+\.?\d{0,2})', re.IGNORECASE),
            re.compile(r'\$([0-9,]+\.?\d{0,2})\s+(?:balance|total)', re.IGNORECASE),
        ]

        self.due_date_patterns = [
            re.compile(r'(?:payment\s+)?due\s+date:?\s*(\d{1,2}/\d{1,2}/\d{2,4})', re.IGNORECASE),
            re.compile(r'(?:payment\s+)?due\s+date:?\s*([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})', re.IGNORECASE),
            re.compile(r'due:?\s*(\d{1,2}/\d{1,2}/\d{2,4})', re.IGNORECASE),
        ]

        self.statement_date_patterns = [
            re.compile(r'statement\s+date:?\s*(\d{1,2}/\d{1,2}/\d{2,4})', re.IGNORECASE),
            re.compile(r'statement\s+date:?\s*([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})', re.IGNORECASE),
            re.compile(r'closing\s+date:?\s*(\d{1,2}/\d{1,2}/\d{2,4})', re.IGNORECASE),
        ]

        # Transaction line patterns - most flexible
        self.transaction_line_patterns = [
            # Date at start, amount at end with dollar sign
            re.compile(r'^(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s+(.+?)\s+\$([0-9,]+\.?\d{0,2})(?:\s*(CR|DB))?$'),
            # Date at start, amount at end without dollar sign
            re.compile(r'^(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s+(.+?)\s+([0-9,]+\.?\d{0,2})(?:\s*(CR|DB))?$'),
            # Month name date format
            re.compile(r'^([A-Za-z]{3}\s+\d{1,2})\s+(.+?)\s+\$?([0-9,]+\.?\d{0,2})(?:\s*(CR|DB))?$'),
        ]

    def parse_statement(self, text: str, filename: str = None) -> ProcessedStatement:
        """Parse generic credit card statement"""
        metadata = self.extract_metadata(text)
        transactions = self.extract_transactions(text)

        notes = [f"Parsed {len(transactions)} transactions using generic parser"]
        if filename:
            notes.append(f"Source file: {filename}")

        # Add warning about generic parsing
        notes.append("Used generic parser - results may be less accurate than bank-specific parsing")

        return ProcessedStatement(
            transactions=transactions,
            metadata=metadata,
            raw_text=text,
            processing_notes=notes
        )

    def extract_metadata(self, text: str) -> StatementMetadata:
        """Extract generic metadata from statement"""
        bank_name = self._detect_bank_name(text)
        statement_period = self._extract_statement_period(text)
        due_date = self._extract_due_date(text)
        balance = self._extract_balance(text)
        account_number = self._extract_account_number(text)

        return StatementMetadata(
            bank_name=bank_name,
            bank_type=BankType.GENERIC,
            account_number=account_number,
            statement_period=statement_period or "Unknown",
            due_date=due_date,
            balance=balance or "0.00"
        )

    def extract_transactions(self, text: str) -> List[Transaction]:
        """Extract transactions using generic patterns"""
        transactions = []
        lines = text.split('\n')
        current_year = self._detect_year(text)

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or self._should_ignore_line(line):
                continue

            transaction = self._parse_generic_transaction(line, current_year, line_num)
            if transaction:
                transactions.append(transaction)

        return transactions

    def _parse_generic_transaction(self, line: str, year: int, line_num: int) -> Optional[Transaction]:
        """Parse a generic transaction line"""
        for pattern in self.transaction_line_patterns:
            match = pattern.match(line)
            if match:
                try:
                    groups = match.groups()
                    date_str = groups[0]
                    description = groups[1].strip()
                    amount_str = groups[2]
                    credit_indicator = groups[3] if len(groups) > 3 else None

                    # Parse date
                    transaction_date = self._parse_generic_date(date_str, year)
                    if not transaction_date:
                        continue

                    # Parse amount
                    amount = float(amount_str.replace(',', ''))

                    # Determine if it's a credit
                    is_credit = (credit_indicator == 'CR' or
                               description.upper().startswith('PAYMENT') or
                               'CREDIT' in description.upper() or
                               'REFUND' in description.upper())

                    if is_credit:
                        amount = -abs(amount)

                    # Classify transaction type
                    transaction_type = self._classify_generic_transaction(description)

                    return Transaction(
                        date=transaction_date,
                        description=description,
                        amount=amount,
                        transaction_type=transaction_type
                    )

                except (ValueError, IndexError):
                    continue

        # Fallback to base parser logic
        return super()._parse_transaction_line(line, line_num)

    def _parse_generic_date(self, date_str: str, year: int) -> Optional[date]:
        """Parse date in various formats"""
        try:
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) == 2:
                    month, day = int(parts[0]), int(parts[1])
                    return date(year, month, day)
                elif len(parts) == 3:
                    month, day, year_part = int(parts[0]), int(parts[1]), int(parts[2])
                    if year_part < 100:
                        year_part += 2000
                    return date(year_part, month, day)
            else:
                # Try month name format
                month_names = {
                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                    'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                    'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                }

                parts = date_str.split()
                if len(parts) == 2:
                    month_str, day_str = parts
                    month = month_names.get(month_str.lower()[:3])
                    if month:
                        day = int(day_str)
                        return date(year, month, day)
        except (ValueError, IndexError):
            pass
        return None

    def _classify_generic_transaction(self, description: str) -> TransactionType:
        """Generic transaction classification"""
        desc_upper = description.upper()

        # Generic patterns that work across banks
        if any(keyword in desc_upper for keyword in ['PAYMENT', 'PAY', 'AUTOPAY', 'THANK YOU']):
            return TransactionType.PAYMENT
        elif any(keyword in desc_upper for keyword in ['FEE', 'CHARGE', 'ANNUAL', 'LATE']):
            return TransactionType.FEE
        elif any(keyword in desc_upper for keyword in ['INTEREST', 'FINANCE', 'APR']):
            return TransactionType.INTEREST
        elif any(keyword in desc_upper for keyword in ['CASH ADVANCE', 'ATM', 'WITHDRAWAL']):
            return TransactionType.CASH_ADVANCE
        elif any(keyword in desc_upper for keyword in ['CREDIT', 'REFUND', 'RETURN', 'ADJUSTMENT']):
            return TransactionType.CREDIT
        else:
            return TransactionType.PURCHASE

    def _detect_bank_name(self, text: str) -> str:
        """Try to detect bank name from text"""
        bank_indicators = [
            (r'chase', 'Chase'),
            (r'american\s+express|amex', 'American Express'),
            (r'citibank|citi', 'Citibank'),
            (r'bank\s+of\s+america', 'Bank of America'),
            (r'capital\s+one', 'Capital One'),
            (r'wells\s+fargo', 'Wells Fargo'),
            (r'discover', 'Discover'),
            (r'synchrony', 'Synchrony Bank'),
            (r'barclays', 'Barclays'),
        ]

        text_lower = text.lower()
        for pattern, name in bank_indicators:
            if re.search(pattern, text_lower):
                return name

        return "Unknown Bank"

    def _detect_year(self, text: str) -> int:
        """Try to detect the statement year"""
        year_matches = re.findall(r'20\d{2}', text)
        if year_matches:
            # Return the most common year
            from collections import Counter
            most_common_year = Counter(year_matches).most_common(1)[0][0]
            return int(most_common_year)
        return 2024  # Default fallback

    def _extract_statement_period(self, text: str) -> Optional[str]:
        """Extract statement period using generic patterns"""
        for pattern in self.statement_date_patterns:
            match = pattern.search(text)
            if match:
                return f"Statement Date: {match.group(1)}"
        return None

    def _extract_due_date(self, text: str) -> Optional[str]:
        """Extract due date using generic patterns"""
        for pattern in self.due_date_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1)
        return None

    def _extract_balance(self, text: str) -> Optional[str]:
        """Extract balance using generic patterns"""
        for pattern in self.balance_patterns:
            match = pattern.search(text)
            if match:
                return f"${match.group(1)}"
        return None

    def _extract_account_number(self, text: str) -> Optional[str]:
        """Extract account number using generic patterns"""
        account_patterns = [
            re.compile(r'account\s+(?:number|#):?\s*[*\-x]*(\d{4,5})', re.IGNORECASE),
            re.compile(r'acct\s+(?:number|#):?\s*[*\-x]*(\d{4,5})', re.IGNORECASE),
            re.compile(r'ending\s+in:?\s*(\d{4,5})', re.IGNORECASE),
        ]

        for pattern in account_patterns:
            match = pattern.search(text)
            if match:
                return f"****{match.group(1)}"
        return None

    def _should_ignore_line(self, line: str) -> bool:
        """Generic line filtering"""
        generic_ignore_patterns = [
            r'^Page\s+\d+',
            r'^Statement\s+Date',
            r'^Account\s+Number',
            r'^Payment\s+Due',
            r'^Previous\s+Balance',
            r'^New\s+Balance',
            r'^Total\s+',
            r'^Summary',
            r'^Customer\s+Service',
            r'^Questions\?',
            r'^Visit\s+us',
            r'^Call\s+us',
            r'^www\.',
            r'^http',
            r'^\d+\s*$',  # Just numbers
            r'^-+\s*$',   # Just dashes
            r'^=+\s*$',   # Just equals
            r'^\s*$',     # Empty lines
        ]

        for pattern in generic_ignore_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True

        return super()._should_ignore_line(line)