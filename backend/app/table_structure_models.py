"""
Data models for table structure analysis results.
"""
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class TableStructureResult:
    """Result of table structure analysis"""
    
    is_complete_table: bool  # True if has separate debit AND credit columns
    has_debit_column: bool
    has_credit_column: bool
    has_balance_column: bool  # True if balance column available for verification
    column_headers: List[str]
    column_count: int
    recommended_method: str  # "PDFPLUMBER" or "VLM"
    requires_balance_verification: bool  # True if VLM + balance column
    reason: str  # Human-readable explanation for method selection
    analysis_metadata: Dict[str, Any]


@dataclass
class BalanceVerificationResult:
    """Result of balance-based verification"""
    
    total_transactions: int
    corrections_made: int
    debit_to_credit_corrections: int
    credit_to_debit_corrections: int
    verification_accuracy: float  # % of transactions that matched balance math
