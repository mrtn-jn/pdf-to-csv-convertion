"""
Data models and schemas for credit card statement processing.
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class TransactionType(str, Enum):
    """Transaction type classification"""
    PURCHASE = "purchase"
    PAYMENT = "payment"
    FEE = "fee"
    INTEREST = "interest"
    CREDIT = "credit"
    CASH_ADVANCE = "cash_advance"
    TRANSFER = "transfer"
    OTHER = "other"


class BankType(str, Enum):
    """Supported bank types"""
    CHASE = "chase"
    AMEX = "amex"
    CITIBANK = "citibank"
    BANK_OF_AMERICA = "bank_of_america"
    CAPITAL_ONE = "capital_one"
    WELLS_FARGO = "wells_fargo"
    DISCOVER = "discover"
    BANCO_NACION = "banco_nacion"
    GENERIC = "generic"


class Transaction(BaseModel):
    """Individual transaction model"""
    date: date
    description: str
    amount: float
    transaction_type: TransactionType = TransactionType.OTHER
    category: Optional[str] = None
    reference: Optional[str] = None

    @validator('amount')
    def validate_amount(cls, v):
        if v == 0:
            return v
        return round(v, 2)

    @validator('description')
    def clean_description(cls, v):
        return v.strip() if v else ""


class StatementMetadata(BaseModel):
    """Statement metadata information"""
    bank_name: str
    bank_type: BankType = BankType.GENERIC
    account_number: Optional[str] = None
    statement_period: str
    due_date: Optional[str] = None
    next_closing: Optional[str] = None
    balance: str
    minimum_payment: Optional[str] = None
    credit_limit: Optional[str] = None
    available_credit: Optional[str] = None
    total_transactions: int = 0

    @validator('statement_period', 'due_date', 'next_closing', pre=True)
    def validate_dates(cls, v):
        if v and isinstance(v, str):
            return v.strip()
        return v


class ProcessedStatement(BaseModel):
    """Complete processed statement data"""
    transactions: List[Transaction]
    metadata: StatementMetadata
    raw_text: Optional[str] = None
    processing_notes: List[str] = Field(default_factory=list)

    @property
    def headers(self) -> List[str]:
        """CSV headers for export"""
        return ["Date", "Description", "Amount", "Type", "Category", "Reference"]

    @property
    def rows(self) -> List[List[str]]:
        """CSV rows for export"""
        rows = []
        for transaction in self.transactions:
            rows.append([
                transaction.date.strftime("%Y-%m-%d"),
                transaction.description,
                str(transaction.amount),
                transaction.transaction_type.value,
                transaction.category or "",
                transaction.reference or ""
            ])
        return rows


class ProcessingResult(BaseModel):
    """API response model"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)

    @classmethod
    def success_response(cls, statement: ProcessedStatement) -> "ProcessingResult":
        """Create success response from processed statement"""
        return cls(
            success=True,
            message="PDF processed successfully",
            data={
                "headers": statement.headers,
                "rows": statement.rows,
                "metadata": {
                    "totalTransactions": len(statement.transactions),
                    "statementPeriod": statement.metadata.statement_period,
                    "dueDate": statement.metadata.due_date,
                    "nextClosing": statement.metadata.next_closing,
                    "balance": statement.metadata.balance,
                    "bankName": statement.metadata.bank_name
                }
            }
        )

    @classmethod
    def error_response(cls, message: str, errors: List[str] = None) -> "ProcessingResult":
        """Create error response"""
        return cls(
            success=False,
            message=message,
            errors=errors or []
        )


class ParsingConfig(BaseModel):
    """Configuration for PDF parsing"""
    bank_type: Optional[BankType] = None
    date_formats: List[str] = Field(default_factory=lambda: [
        "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%d/%m/%Y",
        "%b %d, %Y", "%B %d, %Y", "%m-%d-%Y", "%Y/%m/%d"
    ])
    currency_symbols: List[str] = Field(default_factory=lambda: ["$", "USD", ""])
    amount_patterns: List[str] = Field(default_factory=lambda: [
        r'[\$]?([0-9,]+\.?[0-9]*)',
        r'([0-9,]+\.?[0-9]*)\s*(?:CR|DB)?',
        r'[\$]?\s*([0-9,]+\.?[0-9]*)\s*[-]?'
    ])
    ignore_patterns: List[str] = Field(default_factory=lambda: [
        r'^Page \d+',
        r'^Statement Date',
        r'^Account Number',
        r'^\s*$'
    ])