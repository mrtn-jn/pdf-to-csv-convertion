"""
Banco Nación Mastercard Gold credit card statement parser.
"""
import re
from datetime import date, datetime
from typing import List, Optional
import logging

try:
    from .base_parser import BaseStatementParser
    from ...models import ProcessedStatement, StatementMetadata, BankType, Transaction, TransactionType
except ImportError:
    from services.bank_parsers.base_parser import BaseStatementParser
    from models.statement_data import ProcessedStatement, StatementMetadata, BankType, Transaction, TransactionType

logger = logging.getLogger(__name__)


class BancoNacionParser(BaseStatementParser):
    """Parser for Banco Nación Mastercard Gold credit card statements"""

    def __init__(self):
        super().__init__(BankType.BANCO_NACION)

        # Banco Nación specific patterns
        self.transaction_pattern = re.compile(
            r'(\d{2}-[a-zA-Z]{3}\.?-\d{2})\s+(.+?)\s+(\d{5})\s+([\d.]+,\d{2})$',
            re.IGNORECASE
        )

        # Month name mapping for Spanish
        self.month_names = {
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'ago': 8,
            'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12,
            # Alternative forms
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }

        # Statement metadata patterns
        self.cardholder_pattern = re.compile(r'Titular:?\s*(.+?)(?:\n|Tarjeta)', re.IGNORECASE)
        self.balance_pattern = re.compile(r'(?:Saldo|Balance):?\s*\$?\s*([\d.,]+)', re.IGNORECASE)
        self.minimum_payment_pattern = re.compile(r'(?:Pago\s*M[íi]nimo|Minimum\s*Payment):?\s*\$?\s*([\d.,]+)', re.IGNORECASE)
        self.due_date_pattern = re.compile(r'(?:Vencimiento|Due\s*Date):?\s*(\d{2}[/-]\d{2}[/-]\d{2,4})', re.IGNORECASE)
        self.next_closing_pattern = re.compile(r'(?:Pr[oó]ximo\s*Cierre|Next\s*Closing):?\s*(\d{2}[/-]\d{2}[/-]\d{2,4})', re.IGNORECASE)
        self.statement_period_pattern = re.compile(r'Per[ií]odo:?\s*(\d{2}-[a-zA-Z]{3}-\d{2})\s*al?\s*(\d{2}-[a-zA-Z]{3}-\d{2})', re.IGNORECASE)

        # Section indicators
        self.transaction_section_start = re.compile(r'COMPRAS\s+DEL\s+MES', re.IGNORECASE)
        self.transaction_section_end = re.compile(r'(?:TOTAL\s+COMPRAS|RESUMEN\s+DE\s+CUENTA|DETALLE\s+DE\s+PAGOS)', re.IGNORECASE)

    def parse_statement(self, text: str, filename: str = None) -> ProcessedStatement:
        """Parse Banco Nación credit card statement"""
        metadata = self.extract_metadata(text)
        transactions = self.extract_transactions(text)

        notes = [f"Parsed {len(transactions)} transactions using Banco Nación parser"]
        if filename:
            notes.append(f"Source file: {filename}")

        return ProcessedStatement(
            transactions=transactions,
            metadata=metadata,
            raw_text=text,
            processing_notes=notes
        )

    def extract_metadata(self, text: str) -> StatementMetadata:
        """Extract metadata from Banco Nación statement"""
        cardholder = self._extract_cardholder(text)
        statement_period = self._extract_statement_period(text)
        due_date = self._extract_due_date(text)
        next_closing = self._extract_next_closing(text)
        balance = self._extract_balance(text)
        minimum_payment = self._extract_minimum_payment(text)

        return StatementMetadata(
            bank_name="Banco Nación",
            bank_type=BankType.BANCO_NACION,
            account_number=None,  # Usually masked in statements
            statement_period=statement_period or "Unknown",
            due_date=due_date,
            next_closing=next_closing,
            balance=balance or "0,00",
            minimum_payment=minimum_payment
        )

    def extract_transactions(self, text: str) -> List[Transaction]:
        """Extract transactions from Banco Nación statement"""
        transactions = []
        lines = text.split('\n')

        # Find transaction section
        in_transaction_section = False
        current_year = self._detect_year(text)

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Check for section start
            if self.transaction_section_start.search(line):
                in_transaction_section = True
                logger.info("Found transaction section start")
                continue

            # Check for section end
            if self.transaction_section_end.search(line):
                in_transaction_section = False
                logger.info("Found transaction section end")
                continue

            # Parse transaction if we're in the right section
            if in_transaction_section:
                transaction = self._parse_banco_nacion_transaction(line, current_year)
                if transaction:
                    transactions.append(transaction)

        logger.info(f"Extracted {len(transactions)} transactions from Banco Nación statement")
        return transactions

    def _parse_banco_nacion_transaction(self, line: str, year: int) -> Optional[Transaction]:
        """Parse a single Banco Nación transaction line"""
        match = self.transaction_pattern.match(line)
        if not match:
            return None

        try:
            date_str, description, reference, amount_str = match.groups()

            # Parse date (dd-mmm-yy format)
            transaction_date = self._parse_banco_nacion_date(date_str, year)
            if not transaction_date:
                logger.warning(f"Could not parse date: {date_str}")
                return None

            # Clean description
            description = description.strip()
            if not description:
                return None

            # Parse amount (format: 123.456,78)
            amount = self._parse_banco_nacion_amount(amount_str)
            if amount is None:
                logger.warning(f"Could not parse amount: {amount_str}")
                return None

            # Classify transaction type
            transaction_type = self._classify_banco_nacion_transaction(description)

            # All amounts are typically positive for purchases, negative for credits
            if transaction_type in [TransactionType.PAYMENT, TransactionType.CREDIT]:
                amount = -abs(amount)
            else:
                amount = abs(amount)

            return Transaction(
                date=transaction_date,
                description=description,
                amount=amount,
                transaction_type=transaction_type,
                reference=reference
            )

        except (ValueError, IndexError) as e:
            logger.warning(f"Error parsing transaction line '{line}': {str(e)}")
            return None

    def _parse_banco_nacion_date(self, date_str: str, current_year: int) -> Optional[date]:
        """Parse Banco Nación date format (dd-mmm-yy)"""
        try:
            # Split date parts using only hyphens, not dots
            parts = date_str.split('-')
            if len(parts) != 3:
                return None

            day_str, month_str, year_str = parts
            day = int(day_str)

            # Remove trailing dot from month if present
            month_str = month_str.rstrip('.')

            # Map Spanish month names
            month_str = month_str.lower()
            month = self.month_names.get(month_str)
            if not month:
                return None

            # Handle 2-digit year
            year = int(year_str)
            if year < 100:
                # Determine century based on current year
                if year <= 50:  # Assume years 00-50 are 20xx
                    year += 2000
                else:  # Years 51-99 are 19xx
                    year += 1900

            return date(year, month, day)

        except (ValueError, KeyError, IndexError):
            return None

    def _parse_banco_nacion_amount(self, amount_str: str) -> Optional[float]:
        """Parse Banco Nación amount format (123.456,78)"""
        try:
            # Remove spaces and handle Argentinian number format
            amount_str = amount_str.strip()

            # Convert from Argentinian format (123.456,78) to US format (123456.78)
            # First, replace comma with temp placeholder
            amount_str = amount_str.replace(',', '|DECIMAL|')
            # Remove dots (thousands separators)
            amount_str = amount_str.replace('.', '')
            # Replace temp placeholder with decimal point
            amount_str = amount_str.replace('|DECIMAL|', '.')

            return float(amount_str)

        except (ValueError, AttributeError):
            return None

    def _classify_banco_nacion_transaction(self, description: str) -> TransactionType:
        """Classify Banco Nación transaction type"""
        desc_upper = description.upper()

        # Check for specific patterns
        if any(keyword in desc_upper for keyword in ['PAGO', 'PAYMENT', 'ACREDITACION', 'CREDIT']):
            return TransactionType.PAYMENT
        elif any(keyword in desc_upper for keyword in ['INTERES', 'INTEREST', 'FINANCIACION']):
            return TransactionType.INTEREST
        elif any(keyword in desc_upper for keyword in ['COMISION', 'FEE', 'CARGO', 'ANUAL']):
            return TransactionType.FEE
        elif any(keyword in desc_upper for keyword in ['ADELANTO', 'CASH', 'ATM', 'CAJERO']):
            return TransactionType.CASH_ADVANCE
        elif any(keyword in desc_upper for keyword in ['DEVOLUCION', 'REFUND', 'NOTA CREDITO']):
            return TransactionType.CREDIT
        else:
            return TransactionType.PURCHASE

    def _extract_cardholder(self, text: str) -> Optional[str]:
        """Extract cardholder name"""
        match = self.cardholder_pattern.search(text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_statement_period(self, text: str) -> Optional[str]:
        """Extract statement period"""
        match = self.statement_period_pattern.search(text)
        if match:
            start_date, end_date = match.groups()
            return f"{start_date} to {end_date}"
        return None

    def _extract_due_date(self, text: str) -> Optional[str]:
        """Extract due date"""
        match = self.due_date_pattern.search(text)
        if match:
            return match.group(1)
        return None

    def _extract_next_closing(self, text: str) -> Optional[str]:
        """Extract next closing date"""
        match = self.next_closing_pattern.search(text)
        if match:
            return match.group(1)
        return None

    def _extract_balance(self, text: str) -> Optional[str]:
        """Extract balance amount"""
        match = self.balance_pattern.search(text)
        if match:
            return f"${match.group(1)}"
        return None

    def _extract_minimum_payment(self, text: str) -> Optional[str]:
        """Extract minimum payment amount"""
        match = self.minimum_payment_pattern.search(text)
        if match:
            return f"${match.group(1)}"
        return None

    def _detect_year(self, text: str) -> int:
        """Detect the statement year from text"""
        # Look for 4-digit years
        year_matches = re.findall(r'20\d{2}', text)
        if year_matches:
            # Return the most recent year found
            return max(int(year) for year in year_matches)

        # Fallback to current year
        return datetime.now().year

    def _should_ignore_line(self, line: str) -> bool:
        """Check if line should be ignored during parsing"""
        ignore_patterns = [
            r'^Page\s+\d+',
            r'^P[aá]gina\s+\d+',
            r'^Resumen\s+de\s+Cuenta',
            r'^Titular:',
            r'^Tarjeta:',
            r'^Per[ií]odo:',
            r'^Vencimiento:',
            r'^Saldo:',
            r'^Pago\s+M[ií]nimo:',
            r'^COMPRAS\s+DEL\s+MES\s*$',
            r'^TOTAL\s+COMPRAS',
            r'^DETALLE\s+DE\s+PAGOS',
            r'^\s*$',
            r'^-+\s*$',
            r'^=+\s*$',
        ]

        for pattern in ignore_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True

        return super()._should_ignore_line(line)