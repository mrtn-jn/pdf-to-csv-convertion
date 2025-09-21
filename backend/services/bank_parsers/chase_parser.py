"""
Chase Credit Card statement parser.
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


class ChaseParser(BaseStatementParser):
    """Parser for Chase credit card statements"""

    def __init__(self):
        super().__init__(BankType.CHASE)

        # Chase-specific patterns
        self.statement_date_pattern = re.compile(
            r'Statement\s+Date:?\s*(\d{1,2}/\d{1,2}/\d{2,4})',
            re.IGNORECASE
        )

        self.payment_due_pattern = re.compile(
            r'Payment\s+Due\s+Date:?\s*(\d{1,2}/\d{1,2}/\d{2,4})',
            re.IGNORECASE
        )

        self.balance_pattern = re.compile(
            r'New\s+Balance:?\s*\$?([0-9,]+\.?\d{0,2})',
            re.IGNORECASE
        )

        self.account_pattern = re.compile(
            r'Account\s+Number:?\s*[*\-x]*(\d{4})',
            re.IGNORECASE
        )

        # Chase transaction line patterns
        self.transaction_patterns = [
            # Format: MM/DD Description Amount
            re.compile(r'^(\d{1,2}/\d{1,2})\s+(.+?)\s+([0-9,]+\.?\d{0,2})$'),
            # Format: MM/DD Description $Amount
            re.compile(r'^(\d{1,2}/\d{1,2})\s+(.+?)\s+\$([0-9,]+\.?\d{0,2})$'),
            # Format: MM/DD/YY Description Amount
            re.compile(r'^(\d{1,2}/\d{1,2}/\d{2})\s+(.+?)\s+([0-9,]+\.?\d{0,2})$'),
        ]

    def parse_statement(self, text: str, filename: str = None) -> ProcessedStatement:
        """Parse Chase credit card statement"""
        # Extract metadata
        metadata = self.extract_metadata(text)

        # Extract transactions
        transactions = self.extract_transactions(text)

        # Create processing notes
        notes = [f"Parsed {len(transactions)} transactions from Chase statement"]
        if filename:
            notes.append(f"Source file: {filename}")

        return ProcessedStatement(
            transactions=transactions,
            metadata=metadata,
            raw_text=text,
            processing_notes=notes
        )

    def extract_metadata(self, text: str) -> StatementMetadata:
        """Extract Chase-specific metadata"""
        statement_period = self._extract_statement_period(text)
        due_date = self._extract_due_date(text)
        balance = self._extract_balance(text)
        account_number = self._extract_account_number(text)

        return StatementMetadata(
            bank_name="Chase",
            bank_type=BankType.CHASE,
            account_number=account_number,
            statement_period=statement_period or "Unknown",
            due_date=due_date,
            balance=balance or "0.00"
        )

    def extract_transactions(self, text: str) -> List[Transaction]:
        """Extract transactions with Chase-specific logic"""
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
            current_year = 2024  # Default fallback

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or self._should_ignore_line(line):
                continue

            transaction = self._parse_chase_transaction(line, current_year, line_num)
            if transaction:
                transactions.append(transaction)

        return transactions

    def _parse_chase_transaction(self, line: str, year: int, line_num: int) -> Optional[Transaction]:
        """Parse a Chase-specific transaction line"""
        # Try each transaction pattern
        for pattern in self.transaction_patterns:
            match = pattern.match(line)
            if match:
                try:
                    date_str = match.group(1)
                    description = match.group(2).strip()
                    amount_str = match.group(3)

                    # Parse date
                    transaction_date = self._parse_chase_date(date_str, year)
                    if not transaction_date:
                        continue

                    # Parse amount
                    amount = float(amount_str.replace(',', ''))

                    # Determine if it's a credit (Chase shows credits as negative)
                    is_credit = description.upper().startswith('PAYMENT') or 'CREDIT' in description.upper()

                    if is_credit:
                        amount = -abs(amount)

                    # Classify transaction type
                    transaction_type = self._classify_chase_transaction(description)

                    return Transaction(
                        date=transaction_date,
                        description=description,
                        amount=amount,
                        transaction_type=transaction_type
                    )

                except (ValueError, IndexError) as e:
                    continue

        # Fallback to base parser logic
        return super()._parse_transaction_line(line, line_num)

    def _parse_chase_date(self, date_str: str, year: int) -> Optional[date]:
        """Parse Chase date format (MM/DD or MM/DD/YY)"""
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
        except (ValueError, IndexError):
            pass
        return None

    def _classify_chase_transaction(self, description: str) -> TransactionType:
        """Classify Chase transaction types"""
        desc_upper = description.upper()

        # Chase-specific patterns
        if any(keyword in desc_upper for keyword in ['PAYMENT', 'AUTOPAY', 'THANK YOU']):
            return TransactionType.PAYMENT
        elif any(keyword in desc_upper for keyword in ['ANNUAL FEE', 'LATE FEE', 'OVERLIMIT']):
            return TransactionType.FEE
        elif any(keyword in desc_upper for keyword in ['INTEREST', 'FINANCE CHARGE']):
            return TransactionType.INTEREST
        elif any(keyword in desc_upper for keyword in ['CASH ADVANCE', 'ATM WITHDRAWAL']):
            return TransactionType.CASH_ADVANCE
        elif any(keyword in desc_upper for keyword in ['CREDIT', 'REFUND', 'RETURN']):
            return TransactionType.CREDIT
        else:
            return TransactionType.PURCHASE

    def _extract_statement_period(self, text: str) -> Optional[str]:
        """Extract statement period from Chase text"""
        # Look for statement date pattern
        match = self.statement_date_pattern.search(text)
        if match:
            return f"Statement Date: {match.group(1)}"

        # Alternative patterns
        period_patterns = [
            r'Statement\s+Period:?\s*([^\n]+)',
            r'Billing\s+Period:?\s*([^\n]+)',
        ]

        for pattern in period_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_due_date(self, text: str) -> Optional[str]:
        """Extract payment due date"""
        match = self.payment_due_pattern.search(text)
        if match:
            return match.group(1)
        return None

    def _extract_balance(self, text: str) -> Optional[str]:
        """Extract account balance"""
        match = self.balance_pattern.search(text)
        if match:
            return f"${match.group(1)}"
        return None

    def _extract_account_number(self, text: str) -> Optional[str]:
        """Extract last 4 digits of account number"""
        match = self.account_pattern.search(text)
        if match:
            return f"****{match.group(1)}"
        return None

    def _should_ignore_line(self, line: str) -> bool:
        """Chase-specific line filtering"""
        chase_ignore_patterns = [
            r'^CHASE',
            r'^Customer Service',
            r'^Account Summary',
            r'^Previous Balance',
            r'^Payments and Credits',
            r'^Purchases',
            r'^Fees',
            r'^Interest Charged',
            r'^Page \d+',
        ]

        for pattern in chase_ignore_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True

        return super()._should_ignore_line(line)