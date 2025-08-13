#!/usr/bin/env python3
"""
PII Masking Utilities
Provides different masking strategies for PII data
"""

import re
import hashlib
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass

class MaskingStrategy(Enum):
    """Different PII masking strategies"""
    FULL_MASK = "full_mask"           # Replace with ***
    PARTIAL_MASK = "partial_mask"     # Show first/last chars
    HASH = "hash"                     # SHA-256 hash
    TOKENIZE = "tokenize"             # Replace with tokens
    REDACT = "redact"                 # Replace with [REDACTED]
    FORMAT_PRESERVE = "format_preserve" # Keep format, mask content

@dataclass
class MaskingRule:
    """Rule for masking specific PII types"""
    pii_type: str
    strategy: MaskingStrategy
    preserve_length: bool = True
    show_first: int = 0
    show_last: int = 0
    replacement_char: str = "*"

class PIIMaskingEngine:
    """Engine for applying PII masking strategies"""
    
    # Default masking rules for different PII types
    DEFAULT_MASKING_RULES = {
        "EMAIL": MaskingRule("EMAIL", MaskingStrategy.PARTIAL_MASK, show_first=2, show_last=0),
        "SSN": MaskingRule("SSN", MaskingStrategy.FORMAT_PRESERVE),
        "PHONE": MaskingRule("PHONE", MaskingStrategy.PARTIAL_MASK, show_first=3, show_last=2),
        "NAME": MaskingRule("NAME", MaskingStrategy.PARTIAL_MASK, show_first=1, show_last=1),
        "ADDRESS": MaskingRule("ADDRESS", MaskingStrategy.PARTIAL_MASK, show_first=3, show_last=0),
        "CREDIT_CARD": MaskingRule("CREDIT_CARD", MaskingStrategy.PARTIAL_MASK, show_last=4),
        "DATE_OF_BIRTH": MaskingRule("DATE_OF_BIRTH", MaskingStrategy.REDACT),
        "SALARY": MaskingRule("SALARY", MaskingStrategy.REDACT),
        "AGE": MaskingRule("AGE", MaskingStrategy.REDACT)
    }
    
    def __init__(self, custom_rules: Dict[str, MaskingRule] = None):
        self.masking_rules = self.DEFAULT_MASKING_RULES.copy()
        if custom_rules:
            self.masking_rules.update(custom_rules)
    
    def mask_value(self, value: str, pii_type: str) -> str:
        """Apply masking to a single value based on PII type"""
        if not value or pii_type not in self.masking_rules:
            return value
        
        rule = self.masking_rules[pii_type]
        
        if rule.strategy == MaskingStrategy.FULL_MASK:
            return self._full_mask(value, rule.replacement_char)
        
        elif rule.strategy == MaskingStrategy.PARTIAL_MASK:
            return self._partial_mask(value, rule.show_first, rule.show_last, rule.replacement_char)
        
        elif rule.strategy == MaskingStrategy.HASH:
            return self._hash_value(value)
        
        elif rule.strategy == MaskingStrategy.TOKENIZE:
            return self._tokenize_value(value, pii_type)
        
        elif rule.strategy == MaskingStrategy.REDACT:
            return f"[REDACTED_{pii_type}]"
        
        elif rule.strategy == MaskingStrategy.FORMAT_PRESERVE:
            return self._format_preserve_mask(value, pii_type, rule.replacement_char)
        
        return value
    
    def _full_mask(self, value: str, replacement_char: str = "*") -> str:
        """Replace entire value with mask characters"""
        return replacement_char * len(value)
    
    def _partial_mask(self, value: str, show_first: int = 0, show_last: int = 0, 
                     replacement_char: str = "*") -> str:
        """Show first/last characters, mask the middle"""
        if len(value) <= (show_first + show_last):
            return replacement_char * len(value)
        
        first_part = value[:show_first] if show_first > 0 else ""
        last_part = value[-show_last:] if show_last > 0 else ""
        middle_length = len(value) - show_first - show_last
        middle_part = replacement_char * middle_length
        
        return first_part + middle_part + last_part
    
    def _hash_value(self, value: str) -> str:
        """Create SHA-256 hash of the value"""
        return hashlib.sha256(value.encode()).hexdigest()[:16]  # First 16 chars
    
    def _tokenize_value(self, value: str, pii_type: str) -> str:
        """Replace with a token"""
        hash_suffix = hashlib.md5(value.encode()).hexdigest()[:8]
        return f"TOKEN_{pii_type}_{hash_suffix}"
    
    def _format_preserve_mask(self, value: str, pii_type: str, replacement_char: str = "*") -> str:
        """Preserve format while masking content"""
        if pii_type == "SSN":
            # Format: XXX-XX-XXXX
            if re.match(r'\d{3}-\d{2}-\d{4}', value):
                return f"{replacement_char*3}-{replacement_char*2}-{replacement_char*4}"
            elif re.match(r'\d{9}', value):
                return replacement_char * 9
        
        elif pii_type == "PHONE":
            # Preserve phone format
            masked = re.sub(r'\d', replacement_char, value)
            return masked
        
        elif pii_type == "CREDIT_CARD":
            # Show last 4 digits
            if len(value) >= 4:
                return replacement_char * (len(value) - 4) + value[-4:]
        
        # Default: replace alphanumeric with mask char
        return re.sub(r'[a-zA-Z0-9]', replacement_char, value)

def get_masking_strategies() -> Dict[str, str]:
    """Get available masking strategies with descriptions"""
    return {
        "full_mask": "Replace entire value with asterisks (***)",
        "partial_mask": "Show first/last characters, mask middle (Jo***hn)",
        "hash": "Replace with SHA-256 hash (a1b2c3d4...)",
        "tokenize": "Replace with unique token (TOKEN_NAME_a1b2c3d4)",
        "redact": "Replace with [REDACTED_TYPE] label",
        "format_preserve": "Keep format, mask content (***-**-****)"
    }

def create_custom_masking_rule(pii_type: str, strategy: str, **kwargs) -> MaskingRule:
    """Create a custom masking rule"""
    strategy_enum = MaskingStrategy(strategy)
    return MaskingRule(
        pii_type=pii_type,
        strategy=strategy_enum,
        preserve_length=kwargs.get('preserve_length', True),
        show_first=kwargs.get('show_first', 0),
        show_last=kwargs.get('show_last', 0),
        replacement_char=kwargs.get('replacement_char', '*')
    )
