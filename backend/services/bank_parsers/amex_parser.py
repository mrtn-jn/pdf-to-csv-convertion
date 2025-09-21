"""
American Express credit card statement parser.
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


class AmexParser(BaseStatementParser):
    """Parser for American Express credit card statements"""

    def __init__(self):
        super().__init__(BankType.AMEX)

        # Amex-specific patterns
        self.statement_date_pattern = re.compile(
            r'Statement\s+Date:?\s*([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})',
            re.IGNORECASE
        )

        self.due_date_pattern = re.compile(
            r'Payment\s+Due\s+Date:?\s*([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})',
            re.IGNORECASE
        )

        self.balance_pattern = re.compile(
            r'New\s+Balance:?\s*\$?([0-9,]+\.?\d{0,2})',
            re.IGNORECASE
        )

        self.account_pattern = re.compile(
            r'Account\s+Ending\s+in:?\s*(\d{5})',
            re.IGNORECASE
        )

        # Amex transaction patterns
        self.transaction_patterns = [
            # Format: MMM DD Description Amount
            re.compile(r'^([A-Za-z]{3}\s+\d{1,2})\s+(.+?)\s+\$?([0-9,]+\.?\d{0,2})$'),
            # Format: MM/DD Description $Amount
            re.compile(r'^(\d{1,2}/\d{1,2})\s+(.+?)\s+\$([0-9,]+\.?\d{0,2})$'),
            # Format with reference number: MMM DD Description REF Amount
            re.compile(r'^([A-Za-z]{3}\s+\d{1,2})\s+(.+?)\s+([A-Z0-9]+)\s+\$?([0-9,]+\.?\d{0,2})$'),
        ]

    def parse_statement(self, text: str, filename: str = None) -> ProcessedStatement:
        """Parse American Express credit card statement"""
        metadata = self.extract_metadata(text)
        transactions = self.extract_transactions(text)

        notes = [f"Parsed {len(transactions)} transactions from Amex statement"]
        if filename:
            notes.append(f"Source file: {filename}")

        return ProcessedStatement(
            transactions=transactions,
            metadata=metadata,
            raw_text=text,
            processing_notes=notes
        )

    def extract_metadata(self, text: str) -> StatementMetadata:
        """Extract Amex-specific metadata"""
        statement_period = self._extract_statement_period(text)
        due_date = self._extract_due_date(text)
        balance = self._extract_balance(text)
        account_number = self._extract_account_number(text)

        return StatementMetadata(
            bank_name="American Express",
            bank_type=BankType.AMEX,
            account_number=account_number,
            statement_period=statement_period or "Unknown",
            due_date=due_date,
            balance=balance or "0.00"
        )

    def extract_transactions(self, text: str) -> List[Transaction]:
        """Extract transactions with Amex-specific logic"""
        transactions = []
        lines = text.split('\n')
        current_year = None

        # Try to determine the statement year
        for line in lines:
            year_match = re.search(r'20\d{2}', line)
            if year_match:
                current_year = int(year_match.group())
                break

        if not current_year:
            current_year = 2024

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or self._should_ignore_line(line):
                continue

            transaction = self._parse_amex_transaction(line, current_year, line_num)
            if transaction:
                transactions.append(transaction)

        return transactions

    def _parse_amex_transaction(self, line: str, year: int, line_num: int) -> Optional[Transaction]:
        """Parse an Amex-specific transaction line"""
        for pattern in self.transaction_patterns:
            match = pattern.match(line)
            if match:
                try:
                    groups = match.groups()
                    date_str = groups[0]
                    description = groups[1].strip()

                    # Handle patterns with reference numbers
                    if len(groups) == 4:  # Has reference number
                        reference = groups[2]
                        amount_str = groups[3]
                    else:
                        reference = None
                        amount_str = groups[2]

                    # Parse date
                    transaction_date = self._parse_amex_date(date_str, year)
                    if not transaction_date:
                        continue

                    # Parse amount
                    amount = float(amount_str.replace(',', ''))

                    # Determine if it's a credit
                    is_credit = (description.upper().startswith('PAYMENT') or
                               'CREDIT' in description.upper() or
                               amount < 0)

                    if is_credit:
                        amount = -abs(amount)

                    # Classify transaction type
                    transaction_type = self._classify_amex_transaction(description)

                    return Transaction(
                        date=transaction_date,
                        description=description,
                        amount=amount,
                        transaction_type=transaction_type,
                        reference=reference
                    )

                except (ValueError, IndexError):
                    continue

        # Fallback to base parser logic
        return super()._parse_transaction_line(line, line_num)

    def _parse_amex_date(self, date_str: str, year: int) -> Optional[date]:
        """Parse Amex date format (MMM DD or MM/DD)"""
        try:
            if '/' in date_str:
                # MM/DD format
                parts = date_str.split('/')
                if len(parts) == 2:
                    month, day = int(parts[0]), int(parts[1])
                    return date(year, month, day)
            else:
                # MMM DD format
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

    def _classify_amex_transaction(self, description: str) -> TransactionType:
        """Classify Amex transaction types"""
        desc_upper = description.upper()

        # Amex-specific patterns
        if any(keyword in desc_upper for keyword in ['PAYMENT', 'AUTOPAY', 'THANK YOU', 'ONLINE PMT']):
            return TransactionType.PAYMENT
        elif any(keyword in desc_upper for keyword in ['ANNUAL FEE', 'LATE FEE', 'RETURN FEE']):
            return TransactionType.FEE
        elif any(keyword in desc_upper for keyword in ['INTEREST', 'FINANCE CHARGE', 'PLAN FEES']):
            return TransactionType.INTEREST
        elif any(keyword in desc_upper for keyword in ['CASH ADVANCE', 'ATM']):
            return TransactionType.CASH_ADVANCE
        elif any(keyword in desc_upper for keyword in ['CREDIT', 'REFUND', 'ADJUSTMENT']):
            return TransactionType.CREDIT
        else:
            return TransactionType.PURCHASE

    def _extract_statement_period(self, text: str) -> Optional[str]:
        """Extract statement period from Amex text"""
        match = self.statement_date_pattern.search(text)
        if match:
            return f"Statement Date: {match.group(1)}"

        # Alternative patterns
        period_patterns = [
            r'Statement\s+Period:?\s*([^\n]+)',
            r'Billing\s+Period:?\s*([^\n]+)',
            r'Statement\s+Closing\s+Date:?\s*([^\n]+)',
        ]

        for pattern in period_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_due_date(self, text: str) -> Optional[str]:
        """Extract payment due date"""
        match = self.due_date_pattern.search(text)
        if match:
            return match.group(1)
        return None

    def _extract_balance(self, text: str) -> Optional[str]:
        """Extract account balance"""
        balance_patterns = [
            self.balance_pattern,
            re.compile(r'Total\s+Balance:?\s*\$?([0-9,]+\.?\d{0,2})', re.IGNORECASE),
            re.compile(r'Current\s+Balance:?\s*\$?([0-9,]+\.?\d{0,2})', re.IGNORECASE),
        ]

        for pattern in balance_patterns:
            match = pattern.search(text)
            if match:
                return f"${match.group(1)}"
        return None

    def _extract_account_number(self, text: str) -> Optional[str]:
        """Extract account number ending digits"""
        match = self.account_pattern.search(text)
        if match:
            return f"*****{match.group(1)}"

        # Alternative pattern
        alt_pattern = re.compile(r'Account\s+Number:?\s*[*\-x]*(\d{4,5})', re.IGNORECASE)
        match = alt_pattern.search(text)
        if match:
            return f"****{match.group(1)}"
        return None

    def _should_ignore_line(self, line: str) -> bool:
        """Amex-specific line filtering"""
        amex_ignore_patterns = [
            r'^AMERICAN EXPRESS',
            r'^Member\s+Since',
            r'^Account\s+Summary',
            r'^Previous\s+Balance',
            r'^Payments\s+and\s+Credits',
            r'^Purchases\s+and\s+Adjustments',
            r'^Fees',
            r'^Interest\s+and\s+Finance\s+Charges',
            r'^Page\s+\d+',
            r'^Statement\s+Date',
            r'^Payment\s+Due\s+Date',
            r'^Membership\s+Rewards',
        ]

        for pattern in amex_ignore_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True

        return super()._should_ignore_line(line)