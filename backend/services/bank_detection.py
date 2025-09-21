"""
Bank detection logic for credit card statements.
"""
import re
from typing import Dict, List, Optional
try:
    from ..models import BankType
except ImportError:
    from models.statement_data import BankType
import logging

logger = logging.getLogger(__name__)


class BankDetector:
    """Detects bank type from PDF text content"""

    def __init__(self):
        # Bank detection patterns - order matters for specificity
        self.bank_patterns = {
            BankType.CHASE: [
                r'chase\s*card\s*services',
                r'chase\s*bank',
                r'jp\s*morgan\s*chase',
                r'chase\.com',
                r'chase\s*credit\s*card',
                r'chase\s*sapphire',
                r'chase\s*freedom',
                r'chase\s*slate'
            ],
            BankType.AMEX: [
                r'american\s*express',
                r'amex',
                r'americanexpress\.com',
                r'member\s*since',
                r'membership\s*rewards',
                r'centurion\s*bank',
                r'amex\s*card'
            ],
            BankType.CITIBANK: [
                r'citibank',
                r'citi\s*card',
                r'citicards',
                r'citi\.com',
                r'citibank\s*n\.a\.',
                r'thank\s*you\s*points',
                r'citi\s*double\s*cash'
            ],
            BankType.BANK_OF_AMERICA: [
                r'bank\s*of\s*america',
                r'bankofamerica\.com',
                r'boa\s*card',
                r'merrill\s*lynch',
                r'cash\s*rewards\s*credit\s*card'
            ],
            BankType.CAPITAL_ONE: [
                r'capital\s*one',
                r'capitalone\.com',
                r'venture\s*card',
                r'quicksilver',
                r'savor\s*card',
                r'capital\s*one\s*bank'
            ],
            BankType.WELLS_FARGO: [
                r'wells\s*fargo',
                r'wellsfargo\.com',
                r'propel\s*card',
                r'wells\s*fargo\s*bank',
                r'cash\s*wise'
            ],
            BankType.DISCOVER: [
                r'discover\s*card',
                r'discover\s*bank',
                r'discover\.com',
                r'cashback\s*bonus',
                r'discover\s*it'
            ],
            BankType.BANCO_NACION: [
                r'banco\s*naci[oó]n',
                r'naci[oó]n\s*bank',
                r'mastercard\s*gold',
                r'nacion\s*mastercard',
                r'banco\s*de\s*la\s*naci[oó]n',
                r'bna\s*mastercard',
                r'compras\s*del\s*mes',
                r'resumen\s*de\s*cuenta'
            ]
        }

        # Compile patterns for better performance
        self.compiled_patterns = {}
        for bank_type, patterns in self.bank_patterns.items():
            self.compiled_patterns[bank_type] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                for pattern in patterns
            ]

        # Secondary indicators for ambiguous cases
        self.secondary_indicators = {
            BankType.CHASE: [
                r'ultimate\s*rewards',
                r'pay\s*chase',
                r'chase\s*online',
                r'fraud\s*prevention\s*center'
            ],
            BankType.AMEX: [
                r'pay\s*over\s*time',
                r'platinum\s*card',
                r'gold\s*card',
                r'green\s*card'
            ],
            BankType.CITIBANK: [
                r'citi\s*online',
                r'price\s*rewind',
                r'citi\s*concierge'
            ]
        }

    def detect_bank(self, text: str, confidence_threshold: float = 0.6) -> BankType:
        """
        Detect bank type from statement text.

        Args:
            text: Extracted PDF text
            confidence_threshold: Minimum confidence required for detection

        Returns:
            Detected bank type or GENERIC if uncertain
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for bank detection")
            return BankType.GENERIC

        # Clean text for better matching
        clean_text = self._clean_text_for_detection(text)

        # Score each bank type
        bank_scores = {}
        for bank_type, patterns in self.compiled_patterns.items():
            score = self._calculate_bank_score(clean_text, patterns, bank_type)
            if score > 0:
                bank_scores[bank_type] = score

        if not bank_scores:
            logger.info("No bank patterns matched, using generic parser")
            return BankType.GENERIC

        # Find the bank with highest score
        best_bank = max(bank_scores, key=bank_scores.get)
        best_score = bank_scores[best_bank]

        logger.info(f"Bank detection scores: {bank_scores}")
        logger.info(f"Best match: {best_bank} with score {best_score}")

        # Check if confidence is high enough
        if best_score < confidence_threshold:
            logger.warning(f"Low confidence ({best_score}) for bank detection, using generic parser")
            return BankType.GENERIC

        return best_bank

    def _clean_text_for_detection(self, text: str) -> str:
        """Clean text for better pattern matching"""
        # Remove extra whitespace and normalize
        clean_text = re.sub(r'\s+', ' ', text.strip())
        # Remove special characters that might interfere
        clean_text = re.sub(r'[^\w\s\.\-@]', ' ', clean_text)
        return clean_text

    def _calculate_bank_score(self, text: str, patterns: List[re.Pattern], bank_type: BankType) -> float:
        """
        Calculate confidence score for a bank type.

        Args:
            text: Clean text to search
            patterns: Compiled regex patterns for the bank
            bank_type: Bank type being scored

        Returns:
            Confidence score (0.0 to 1.0+)
        """
        base_score = 0.0
        pattern_matches = 0

        # Primary pattern matching
        for pattern in patterns:
            matches = len(pattern.findall(text))
            if matches > 0:
                pattern_matches += 1
                # Weight multiple matches higher but with diminishing returns
                base_score += min(matches * 0.3, 1.0)

        # Boost score if multiple different patterns match
        if pattern_matches > 1:
            base_score *= (1.0 + (pattern_matches - 1) * 0.2)

        # Check secondary indicators for additional confidence
        if bank_type in self.secondary_indicators:
            secondary_patterns = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in self.secondary_indicators[bank_type]
            ]

            for pattern in secondary_patterns:
                if pattern.search(text):
                    base_score += 0.1  # Small boost for secondary indicators

        return min(base_score, 2.0)  # Cap at 2.0 for very strong matches

    def get_bank_confidence_details(self, text: str) -> Dict[BankType, Dict[str, any]]:
        """
        Get detailed confidence information for all banks.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with confidence details for each bank
        """
        clean_text = self._clean_text_for_detection(text)
        results = {}

        for bank_type, patterns in self.compiled_patterns.items():
            matched_patterns = []
            total_matches = 0

            for i, pattern in enumerate(patterns):
                matches = len(pattern.findall(clean_text))
                if matches > 0:
                    matched_patterns.append({
                        'pattern_index': i,
                        'pattern': self.bank_patterns[bank_type][i],
                        'matches': matches
                    })
                    total_matches += matches

            score = self._calculate_bank_score(clean_text, patterns, bank_type)

            results[bank_type] = {
                'score': score,
                'total_matches': total_matches,
                'matched_patterns': matched_patterns,
                'pattern_count': len(matched_patterns)
            }

        return results

    def validate_detection(self, text: str, expected_bank: BankType) -> bool:
        """
        Validate if the expected bank type matches the detected one.

        Args:
            text: Statement text
            expected_bank: Expected bank type

        Returns:
            True if detection matches expectation
        """
        detected_bank = self.detect_bank(text)
        return detected_bank == expected_bank