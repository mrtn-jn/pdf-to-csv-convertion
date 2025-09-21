"""
Bank parsers package for credit card statement processing.
"""
from typing import Optional

try:
    from ...models import BankType
except ImportError:
    from models.statement_data import BankType
from .base_parser import BaseStatementParser
from .chase_parser import ChaseParser
from .amex_parser import AmexParser
from .generic_parser import GenericParser
from .banco_nacion_parser import BancoNacionParser


# Parser registry
PARSER_REGISTRY = {
    BankType.CHASE: ChaseParser,
    BankType.AMEX: AmexParser,
    BankType.BANCO_NACION: BancoNacionParser,
    BankType.GENERIC: GenericParser,
    # Add more parsers as they are implemented
    BankType.CITIBANK: GenericParser,  # Use generic parser for now
    BankType.BANK_OF_AMERICA: GenericParser,
    BankType.CAPITAL_ONE: GenericParser,
    BankType.WELLS_FARGO: GenericParser,
    BankType.DISCOVER: GenericParser,
}


def get_parser_for_bank(bank_type: BankType) -> Optional[BaseStatementParser]:
    """
    Get the appropriate parser for a bank type.

    Args:
        bank_type: The detected bank type

    Returns:
        Parser instance or None if not supported
    """
    parser_class = PARSER_REGISTRY.get(bank_type)
    if parser_class:
        return parser_class()

    # Fallback to generic parser
    return GenericParser()


def get_supported_banks() -> list[BankType]:
    """
    Get list of supported bank types.

    Returns:
        List of supported BankType enums
    """
    return list(PARSER_REGISTRY.keys())


def register_parser(bank_type: BankType, parser_class: type) -> None:
    """
    Register a new parser for a bank type.

    Args:
        bank_type: The bank type to register
        parser_class: Parser class that extends BaseStatementParser
    """
    if not issubclass(parser_class, BaseStatementParser):
        raise ValueError("Parser class must extend BaseStatementParser")

    PARSER_REGISTRY[bank_type] = parser_class


__all__ = [
    "BaseStatementParser",
    "ChaseParser",
    "AmexParser",
    "GenericParser",
    "BancoNacionParser",
    "get_parser_for_bank",
    "get_supported_banks",
    "register_parser"
]