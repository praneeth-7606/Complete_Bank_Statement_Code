"""
Table Structure Analyzer for intelligent extraction method selection.
"""
import pdfplumber
import tempfile
import logging
from typing import List, Optional
from pathlib import Path

from .table_structure_models import TableStructureResult

logger = logging.getLogger(__name__)


class TableStructureAnalyzer:
    """Analyzes PDF table structure to determine optimal extraction method"""
    
    def __init__(self):
        """Initialize analyzer with column detection keywords"""
        # Keywords for detecting debit column
        self.debit_keywords = ['debit', 'withdrawal', 'payment', 'dr', 'paid', 'deducted']
        
        # Keywords for detecting credit column
        self.credit_keywords = ['credit', 'deposit', 'receipt', 'cr', 'received', 'credited']
        
        # Keywords for detecting balance column
        self.balance_keywords = ['balance', 'closing balance', 'bal', 'running balance']
    
    def analyze_structure(self, pdf_bytes: bytes, password: str = "") -> TableStructureResult:
        """
        Analyze table structure in PDF to determine extraction method
        
        Args:
            pdf_bytes: PDF file content
            password: PDF password if encrypted
            
        Returns:
            TableStructureResult with method recommendation and balance availability
        """
        try:
            # Create temporary file for pdfplumber
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(pdf_bytes)
                tmp_path = tmp_file.name
            
            try:
                # Open PDF with pdfplumber
                pdf_config = {'password': password} if password else {}
                with pdfplumber.open(tmp_path, **pdf_config) as pdf:
                    if not pdf.pages:
                        return self._create_default_result("No pages found in PDF")
                    
                    # Analyze first page (sample-based approach)
                    first_page = pdf.pages[0]
                    
                    # Detect column headers
                    columns = self._detect_columns(first_page)
                    
                    # Check for specific column types
                    has_debit = self._has_separate_debit_column(columns)
                    has_credit = self._has_separate_credit_column(columns)
                    has_balance = self._has_balance_column(columns)
                    
                    # Determine if table is complete
                    is_complete = self._is_complete_table(has_debit, has_credit)
                    
                    # Determine recommended method
                    recommended_method = "PDFPLUMBER" if is_complete else "VLM"
                    
                    # Determine if balance verification is needed
                    requires_balance_verification = (not is_complete) and has_balance
                    
                    # Create reason string
                    if is_complete:
                        reason = "Table has separate debit/credit columns"
                    elif has_balance:
                        reason = "No separate debit/credit columns (merged into 'Amount')"
                    else:
                        reason = "No separate debit/credit columns and no balance column"
                    
                    # Build result
                    return TableStructureResult(
                        is_complete_table=is_complete,
                        has_debit_column=has_debit,
                        has_credit_column=has_credit,
                        has_balance_column=has_balance,
                        column_headers=columns,
                        column_count=len(columns),
                        recommended_method=recommended_method,
                        requires_balance_verification=requires_balance_verification,
                        reason=reason,
                        analysis_metadata={
                            'analyzed_page': 1,
                            'total_pages': len(pdf.pages)
                        }
                    )
            finally:
                # Clean up temporary file
                Path(tmp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.warning(f"Table structure analysis failed: {str(e)}")
            return self._create_default_result(f"Analysis error: {str(e)}")
    
    def _detect_columns(self, page) -> List[str]:
        """
        Detect column headers in table
        
        Returns:
            List of detected column names (lowercase)
        """
        columns = []
        
        try:
            # Extract tables from page
            tables = page.extract_tables()
            
            if not tables:
                # Try to extract text and look for common headers
                text = page.extract_text()
                if text:
                    text_lower = text.lower()
                    # Look for common column keywords in text
                    common_headers = ['date', 'description', 'particulars', 'narration', 
                                    'debit', 'credit', 'amount', 'balance', 'withdrawal', 
                                    'deposit', 'payment', 'receipt']
                    for header in common_headers:
                        if header in text_lower:
                            columns.append(header)
                return columns
            
            # Get first table (usually the transaction table)
            first_table = tables[0]
            
            if not first_table or len(first_table) == 0:
                return columns
            
            # Look for header row (usually first or second row)
            for row_idx in range(min(3, len(first_table))):
                row = first_table[row_idx]
                if row and any(row):  # Check if row has content
                    # Check if this looks like a header row
                    row_text = ' '.join([str(cell).lower() if cell else '' for cell in row])
                    if any(keyword in row_text for keyword in ['date', 'description', 'amount', 'balance']):
                        # This is likely the header row
                        columns = [str(cell).lower().strip() if cell else '' for cell in row]
                        columns = [col for col in columns if col]  # Remove empty strings
                        break
            
        except Exception as e:
            logger.debug(f"Error detecting columns: {str(e)}")
        
        return columns
    
    def _has_separate_debit_column(self, columns: List[str]) -> bool:
        """Check if table has a separate debit column"""
        for col in columns:
            if any(keyword in col for keyword in self.debit_keywords):
                return True
        return False
    
    def _has_separate_credit_column(self, columns: List[str]) -> bool:
        """Check if table has a separate credit column"""
        for col in columns:
            if any(keyword in col for keyword in self.credit_keywords):
                return True
        return False
    
    def _has_balance_column(self, columns: List[str]) -> bool:
        """Check if table has a balance column (for verification)"""
        for col in columns:
            if any(keyword in col for keyword in self.balance_keywords):
                return True
        return False
    
    def _is_complete_table(self, has_debit: bool, has_credit: bool) -> bool:
        """
        Determine if table structure is complete
        
        A complete table has BOTH separate debit and credit columns.
        If either is missing, the table is incomplete.
        
        Returns:
            True if complete (use PDFPlumber), False if incomplete (use VLM)
        """
        return has_debit and has_credit
    
    def _create_default_result(self, reason: str) -> TableStructureResult:
        """Create default result when analysis fails (fallback to VLM)"""
        return TableStructureResult(
            is_complete_table=False,
            has_debit_column=False,
            has_credit_column=False,
            has_balance_column=False,
            column_headers=[],
            column_count=0,
            recommended_method="VLM",
            requires_balance_verification=False,
            reason=reason,
            analysis_metadata={'error': True}
        )
