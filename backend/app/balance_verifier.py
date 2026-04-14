"""
Balance Verifier for dual-layer verification of transaction categorization.
"""
import logging
from typing import List, Dict, Tuple, Optional

from .table_structure_models import BalanceVerificationResult

logger = logging.getLogger(__name__)


class BalanceVerifier:
    """Verify and correct debit/credit categorization using balance tracking"""
    
    def __init__(self):
        """Initialize balance verifier"""
        pass
    
    def verify_and_correct(
        self, 
        transactions: List[Dict], 
        opening_balance: Optional[float] = None
    ) -> Tuple[List[Dict], BalanceVerificationResult]:
        """
        Verify transactions using balance tracking and correct misclassifications
        
        Args:
            transactions: List of transactions with debit/credit from VLM
            opening_balance: Opening balance if available
            
        Returns:
            Tuple of (corrected_transactions, BalanceVerificationResult)
            
        Logic:
            For each transaction:
            1. Calculate expected balance change from VLM categorization
            2. Compare with actual balance change
            3. If mismatch  Correct the categorization
            4. Track corrections for logging
        """
        if not transactions:
            return transactions, BalanceVerificationResult(
                total_transactions=0,
                corrections_made=0,
                debit_to_credit_corrections=0,
                credit_to_debit_corrections=0,
                verification_accuracy=100.0
            )
        
        corrected_transactions = []
        corrections_made = 0
        debit_to_credit_corrections = 0
        credit_to_debit_corrections = 0
        
        # Initialize previous balance
        prev_balance = opening_balance
        
        for idx, transaction in enumerate(transactions):
            # Get current balance from transaction
            current_balance = transaction.get('balance')
            
            # If no balance column, can't verify - just keep original
            if current_balance is None or prev_balance is None:
                corrected_transactions.append(transaction)
                # Set prev_balance for next iteration if we have opening balance
                if idx == 0 and opening_balance is not None:
                    prev_balance = opening_balance
                continue
            
            # Parse balance values
            try:
                current_balance_float = float(str(current_balance).replace(',', '').replace('', '').strip())
                prev_balance_float = float(str(prev_balance).replace(',', '').replace('', '').strip())
            except (ValueError, AttributeError):
                # Can't parse balance, keep original
                corrected_transactions.append(transaction)
                prev_balance = current_balance
                continue
            
            # Calculate balance change and determine correct transaction type
            change_amount, correct_type = self._calculate_balance_change(
                prev_balance_float, 
                current_balance_float
            )
            
            # Get VLM's categorization
            vlm_debit = transaction.get('debit', 0.0) or 0.0
            vlm_credit = transaction.get('credit', 0.0) or 0.0
            
            # Determine VLM's type
            if vlm_debit > 0:
                vlm_type = 'debit'
            elif vlm_credit > 0:
                vlm_type = 'credit'
            else:
                vlm_type = 'unknown'
            
            # Check if correction needed
            if correct_type != 'unknown' and vlm_type != 'unknown' and correct_type != vlm_type:
                # Mismatch - correct it
                corrected_transaction = self._correct_transaction(
                    transaction, 
                    correct_type, 
                    change_amount
                )
                corrected_transactions.append(corrected_transaction)
                corrections_made += 1
                
                # Track correction type
                if vlm_type == 'debit' and correct_type == 'credit':
                    debit_to_credit_corrections += 1
                    logger.info(f"      Transaction #{idx + 1}: {transaction.get('date', 'N/A')}")
                    logger.info(f"         VLM Says: Debit {vlm_debit:.2f}")
                    logger.info(f"         Balance: {prev_balance_float:.2f}  {current_balance_float:.2f} (increased {change_amount:.2f})")
                    logger.info(f"         [WARN] MISMATCH: Corrected to Credit")
                elif vlm_type == 'credit' and correct_type == 'debit':
                    credit_to_debit_corrections += 1
                    logger.info(f"      Transaction #{idx + 1}: {transaction.get('date', 'N/A')}")
                    logger.info(f"         VLM Says: Credit {vlm_credit:.2f}")
                    logger.info(f"         Balance: {prev_balance_float:.2f}  {current_balance_float:.2f} (decreased {change_amount:.2f})")
                    logger.info(f"         [WARN] MISMATCH: Corrected to Debit")
            else:
                # No correction needed
                corrected_transactions.append(transaction)
                
                # Log match for first few transactions
                if idx < 5 and correct_type != 'unknown':
                    logger.info(f"      Transaction #{idx + 1}: {transaction.get('date', 'N/A')}")
                    if vlm_type == 'debit':
                        logger.info(f"         VLM Says: Debit {vlm_debit:.2f}")
                        logger.info(f"         Balance: {prev_balance_float:.2f}  {current_balance_float:.2f} (decreased {change_amount:.2f})")
                    else:
                        logger.info(f"         VLM Says: Credit {vlm_credit:.2f}")
                        logger.info(f"         Balance: {prev_balance_float:.2f}  {current_balance_float:.2f} (increased {change_amount:.2f})")
                    logger.info(f"         [OK] MATCH: Confirmed {correct_type.capitalize()}")
            
            # Update previous balance for next iteration
            prev_balance = current_balance_float
        
        # Calculate verification accuracy
        total_transactions = len(transactions)
        verification_accuracy = ((total_transactions - corrections_made) / total_transactions * 100) if total_transactions > 0 else 100.0
        
        result = BalanceVerificationResult(
            total_transactions=total_transactions,
            corrections_made=corrections_made,
            debit_to_credit_corrections=debit_to_credit_corrections,
            credit_to_debit_corrections=credit_to_debit_corrections,
            verification_accuracy=verification_accuracy
        )
        
        return corrected_transactions, result
    
    def _calculate_balance_change(
        self, 
        prev_balance: float, 
        current_balance: float
    ) -> Tuple[float, str]:
        """
        Calculate balance change and determine transaction type
        
        Returns:
            Tuple of (change_amount, transaction_type)
            - If balance decreased  ("debit", amount)
            - If balance increased  ("credit", amount)
        """
        balance_change = current_balance - prev_balance
        
        if balance_change < 0:
            # Balance decreased  Debit transaction
            return abs(balance_change), 'debit'
        elif balance_change > 0:
            # Balance increased  Credit transaction
            return balance_change, 'credit'
        else:
            # No change
            return 0.0, 'unknown'
    
    def _correct_transaction(
        self, 
        transaction: Dict, 
        correct_type: str, 
        amount: float
    ) -> Dict:
        """
        Correct transaction categorization based on balance math
        
        Args:
            transaction: Original transaction from VLM
            correct_type: "debit" or "credit" from balance calculation
            amount: Correct amount from balance change
            
        Returns:
            Corrected transaction
        """
        corrected = transaction.copy()
        
        if correct_type == 'debit':
            corrected['debit'] = amount
            corrected['credit'] = 0.0
        elif correct_type == 'credit':
            corrected['debit'] = 0.0
            corrected['credit'] = amount
        
        # Add metadata flag
        corrected['correction_applied'] = True
        
        return corrected
