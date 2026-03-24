"""
Data Encryptor Utility
Handles AES-256-GCM encryption/decryption for database storage.
"""

import base64
import os
from typing import Dict, List, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import logging

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption/decryption operations fail"""
    pass


class DataEncryptor:
    """Utility for AES-256-GCM encryption/decryption of sensitive data"""
    
    def __init__(self, encryption_key: str, salt: Optional[str] = None):
        """
        Initialize encryptor with encryption key
        
        Args:
            encryption_key: Base64-encoded 256-bit encryption key
            salt: Optional base64-encoded salt for key derivation
            
        Raises:
            EncryptionError: If key is missing or invalid
        """
        if not encryption_key:
            raise EncryptionError("ENCRYPTION_KEY not found in environment")
        
        try:
            # Decode the base64 key
            key_bytes = base64.b64decode(encryption_key)
            
            # Validate key length (must be 256 bits = 32 bytes)
            if len(key_bytes) != 32:
                raise EncryptionError(
                    f"ENCRYPTION_KEY must be 256 bits (32 bytes), got {len(key_bytes)} bytes"
                )
            
            # Initialize AES-GCM cipher
            self.cipher = AESGCM(key_bytes)
            
        except Exception as e:
            logger.error(f"Failed to initialize encryptor: {str(e)}")
            raise EncryptionError(f"Invalid encryption key: {str(e)}")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string using AES-256-GCM
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded string containing nonce + ciphertext + tag
            
        Raises:
            EncryptionError: If encryption fails
        """
        if not plaintext:
            return plaintext
        
        try:
            # Generate random 12-byte nonce (recommended for GCM)
            nonce = os.urandom(12)
            
            # Encrypt the plaintext
            plaintext_bytes = plaintext.encode('utf-8')
            ciphertext = self.cipher.encrypt(nonce, plaintext_bytes, None)
            
            # Combine nonce + ciphertext and encode as base64
            encrypted_data = nonce + ciphertext
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise EncryptionError(f"Failed to encrypt data: {str(e)}")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string using AES-256-GCM
        
        Args:
            ciphertext: Base64-encoded string containing nonce + ciphertext + tag
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            EncryptionError: If decryption fails
        """
        if not ciphertext:
            return ciphertext
        
        try:
            # Decode base64
            encrypted_data = base64.b64decode(ciphertext)
            
            # Extract nonce (first 12 bytes) and ciphertext (rest)
            nonce = encrypted_data[:12]
            ciphertext_bytes = encrypted_data[12:]
            
            # Decrypt
            plaintext_bytes = self.cipher.decrypt(nonce, ciphertext_bytes, None)
            return plaintext_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise EncryptionError(
                "Failed to decrypt data. Key may be incorrect or data corrupted."
            )
    
    def encrypt_transaction(self, transaction: Dict) -> Dict:
        """
        Encrypt sensitive fields in a transaction dictionary
        
        Encrypts:
        - description
        - reference
        - narration
        
        Preserves (not encrypted):
        - date
        - debit/credit/amount
        - balance
        - category
        - id, user_id, timestamps
        
        Args:
            transaction: Transaction dictionary
            
        Returns:
            New dictionary with encrypted sensitive fields
        """
        if not transaction:
            return transaction
        
        # Create a copy to avoid modifying original
        encrypted = transaction.copy()
        
        # Encrypt description field
        if 'description' in encrypted and encrypted['description']:
            encrypted['description_encrypted'] = self.encrypt(encrypted['description'])
            # Keep original for now (will be removed in migration)
            # del encrypted['description']
        
        # Encrypt reference field
        if 'reference' in encrypted and encrypted['reference']:
            encrypted['reference_encrypted'] = self.encrypt(encrypted['reference'])
            # Keep original for now
            # del encrypted['reference']
        
        # Encrypt narration field if present
        if 'narration' in encrypted and encrypted['narration']:
            encrypted['narration_encrypted'] = self.encrypt(encrypted['narration'])
            # Keep original for now
            # del encrypted['narration']
        
        return encrypted
    
    def decrypt_transaction(self, transaction: Dict) -> Dict:
        """
        Decrypt sensitive fields in a transaction dictionary
        
        Args:
            transaction: Transaction dictionary with encrypted fields
            
        Returns:
            New dictionary with decrypted fields
        """
        if not transaction:
            return transaction
        
        # Create a copy to avoid modifying original
        decrypted = transaction.copy()
        
        # Decrypt description field
        if 'description_encrypted' in decrypted and decrypted['description_encrypted']:
            try:
                decrypted['description'] = self.decrypt(decrypted['description_encrypted'])
            except EncryptionError as e:
                logger.warning(f"Failed to decrypt description: {str(e)}")
                decrypted['description'] = "[Decryption Failed]"
        
        # Decrypt reference field
        if 'reference_encrypted' in decrypted and decrypted['reference_encrypted']:
            try:
                decrypted['reference'] = self.decrypt(decrypted['reference_encrypted'])
            except EncryptionError as e:
                logger.warning(f"Failed to decrypt reference: {str(e)}")
                decrypted['reference'] = "[Decryption Failed]"
        
        # Decrypt narration field
        if 'narration_encrypted' in decrypted and decrypted['narration_encrypted']:
            try:
                decrypted['narration'] = self.decrypt(decrypted['narration_encrypted'])
            except EncryptionError as e:
                logger.warning(f"Failed to decrypt narration: {str(e)}")
                decrypted['narration'] = "[Decryption Failed]"
        
        return decrypted
    
    def encrypt_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """
        Encrypt list of transactions
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            List of encrypted transaction dictionaries
        """
        if not transactions:
            return transactions
        
        return [self.encrypt_transaction(txn) for txn in transactions]
    
    def decrypt_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """
        Decrypt list of transactions
        
        Args:
            transactions: List of encrypted transaction dictionaries
            
        Returns:
            List of decrypted transaction dictionaries
        """
        if not transactions:
            return transactions
        
        return [self.decrypt_transaction(txn) for txn in transactions]
