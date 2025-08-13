"""
AWS PII Detection Agent - Core Module
"""

from .pii_agent import AWSPIIDetectionAgent, PIIDetectionConfig, PIIDetectionResult, scan_pii
from .masking import PIIMaskingEngine, MaskingStrategy, MaskingRule, get_masking_strategies, create_custom_masking_rule

__version__ = "1.0.0"
__author__ = "AWS PII Detection Team"

__all__ = [
    "AWSPIIDetectionAgent",
    "PIIDetectionConfig", 
    "PIIDetectionResult",
    "scan_pii",
    "PIIMaskingEngine",
    "MaskingStrategy",
    "MaskingRule",
    "get_masking_strategies",
    "create_custom_masking_rule"
]
