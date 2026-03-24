"""
Data Masker Utility
Masks sensitive data in transactions before sending to LLM services.
"""

import re
from typing import Dict, List, Optional


class DataMasker:
    """Utility for masking sensitive data before LLM transmission"""
    
    def __init__(self):
        """Initialize masker with name mapping for consistent anonymization"""
        self.name_mapping = {}  # Map real names to generic labels
        self.name_counter = 0
        
        # Compile regex patterns once for performance
        self._phone_pattern = re.compile(r'\b\d{10}\b')
        self._account_pattern = re.compile(r'\b\d{12,16}\b')
        self._upi_pattern = re.compile(r'[\w.]+@([\w.]+)')
        self._email_pattern = re.compile(r'[\w.]+@([\w.]+\.\w+)')
    
    def mask_account_number(self, account: str) -> str:
        """
        Mask account number keeping last 4 digits
        
        Args:
            account: Account number string
            
        Returns:
            Masked account number (e.g., "************3456")
        """
        if not account:
            return account
            
        account = str(account).strip()
        
        if len(account) <= 4:
            return account
        
        return '*' * (len(account) - 4) + account[-4:]
    
    def mask_phone_number(self, phone: str) -> str:
        """
        Mask phone number keeping last 4 digits
        
        Args:
            phone: Phone number string
            
        Returns:
            Masked phone number (e.g., "******3210")
        """
        if not phone:
            return phone
            
        phone = str(phone).strip()
        
        if len(phone) <= 4:
            return phone
        
        return '*' * (len(phone) - 4) + phone[-4:]
    
    def mask_upi_id(self, upi: str) -> str:
        """
        Mask UPI ID keeping domain portion
        
        Args:
            upi: UPI ID string (e.g., "john.doe@paytm")
            
        Returns:
            Masked UPI ID (e.g., "****@paytm")
        """
        if not upi:
            return upi
            
        if '@' in upi:
            parts = upi.split('@')
            return '****@' + parts[1]
        
        return '****'
    
    def mask_email(self, email: str) -> str:
        """
        Mask email keeping domain portion
        
        Args:
            email: Email address string
            
        Returns:
            Masked email (e.g., "****@domain.com")
        """
        if not email:
            return email
            
        if '@' in email:
            parts = email.split('@')
            return '****@' + parts[1]
        
        return '****'
    
    def mask_name(self, name: str) -> str:
        """
        Replace name with generic label
        
        Args:
            name: Person's name
            
        Returns:
            Generic label (e.g., "PERSON_1")
        """
        if not name:
            return name
            
        if name not in self.name_mapping:
            self.name_counter += 1
            self.name_mapping[name] = f'PERSON_{self.name_counter}'
        
        return self.name_mapping[name]
    
    def mask_description(self, description: str) -> str:
        """
        Mask sensitive data in transaction description
        
        Masks:
        - Phone numbers (10 digits)
        - Account numbers (12-16 digits)
        - UPI IDs (keeps domain)
        - Email addresses (keeps domain)
        
        Preserves:
        - Merchant names (Swiggy, Amazon, etc.)
        - Transaction types (UPI, NEFT, etc.)
        - General transaction context
        
        Args:
            description: Transaction description string
            
        Returns:
            Masked description with sensitive data replaced
        """
        if not description:
            return description
        
        masked = str(description)
        
        # Mask phone numbers (10 digits)
        masked = self._phone_pattern.sub('**********', masked)
        
        # Mask account numbers (12-16 digits)
        masked = self._account_pattern.sub('************', masked)
        
        # Mask UPI IDs (keep domain for context)
        masked = self._upi_pattern.sub(r'****@\1', masked)
        
        # Mask email addresses (keep domain for context)
        masked = self._email_pattern.sub(r'****@\1', masked)
        
        return masked
    
    def mask_transaction(self, transaction: Dict) -> Dict:
        """
        Mask all sensitive data in a single transaction
        
        Masks the 'description' field while preserving other fields like:
        - date (safe)
        - amount/debit/credit (safe)
        - category (safe)
        - merchant names (safe, needed for categorization)
        
        Args:
            transaction: Transaction dictionary
            
        Returns:
            New dictionary with masked sensitive fields
        """
        if not transaction:
            return transaction
        
        # Create a copy to avoid modifying original
        masked = transaction.copy()
        
        # Mask description field if present
        if 'description' in masked and masked['description']:
            masked['description'] = self.mask_description(masked['description'])
        
        # Mask narration field if present (some banks use this)
        if 'narration' in masked and masked['narration']:
            masked['narration'] = self.mask_description(masked['narration'])
        
        # Mask reference field if present
        if 'reference' in masked and masked['reference']:
            masked['reference'] = self.mask_description(masked['reference'])
        
        # Keep all other fields unchanged (date, amount, category, etc.)
        
        return masked
    
    def mask_transactions_for_llm(self, transactions: List[Dict]) -> List[Dict]:
        """
        Mask list of transactions before sending to LLM
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            List of masked transaction dictionaries
        """
        if not transactions:
            return transactions
        
        return [self.mask_transaction(txn) for txn in transactions]
