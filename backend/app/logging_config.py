"""
Logging Configuration
Configures application logging with separate security audit log.
"""

import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(log_level: str = "INFO"):
    """
    Setup application logging with security audit trail.
    
    Creates two log files:
    1. app.log - General application logs
    2. security_audit.log - Security-specific operations (masking, encryption, decryption)
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Application log file handler
    app_log_file = log_dir / "app.log"
    app_file_handler = logging.handlers.RotatingFileHandler(
        app_log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    app_file_handler.setLevel(logging.DEBUG)
    app_file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    app_file_handler.setFormatter(app_file_formatter)
    root_logger.addHandler(app_file_handler)
    
    # Security audit log file handler
    security_log_file = log_dir / "security_audit.log"
    security_file_handler = logging.handlers.RotatingFileHandler(
        security_log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10  # Keep more backups for audit trail
    )
    security_file_handler.setLevel(logging.INFO)
    security_file_formatter = logging.Formatter(
        '%(asctime)s - SECURITY - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    security_file_handler.setFormatter(security_file_formatter)
    
    # Create security logger
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)
    security_logger.addHandler(security_file_handler)
    security_logger.propagate = False  # Don't propagate to root logger
    
    logging.info(f"Logging configured: Level={log_level}, App Log={app_log_file}, Security Log={security_log_file}")


def get_security_logger():
    """
    Get the security audit logger.
    
    Use this logger for security-related operations:
    - Data masking before LLM transmission
    - Data encryption before database storage
    - Data decryption on retrieval
    - Authentication events
    - Authorization failures
    
    Returns:
        Security audit logger instance
    """
    return logging.getLogger('security')


# Security logging helper functions
def log_masking_operation(transaction_count: int, context: str = ""):
    """Log data masking operation"""
    security_logger = get_security_logger()
    security_logger.info(f"DATA_MASKING: Masked {transaction_count} transactions before LLM transmission. Context: {context}")


def log_encryption_operation(transaction_count: int, context: str = ""):
    """Log data encryption operation"""
    security_logger = get_security_logger()
    security_logger.info(f"DATA_ENCRYPTION: Encrypted {transaction_count} transactions before database storage. Context: {context}")


def log_decryption_operation(transaction_count: int, user_id: str = "", context: str = ""):
    """Log data decryption operation"""
    security_logger = get_security_logger()
    security_logger.info(f"DATA_DECRYPTION: Decrypted {transaction_count} transactions for user {user_id}. Context: {context}")


def log_password_usage(context: str = "PDF decryption"):
    """Log password usage (without logging the actual password)"""
    security_logger = get_security_logger()
    security_logger.info(f"PASSWORD_USAGE: Password used for {context}. Password NOT logged.")


def log_llm_request(masked: bool, data_type: str = "transactions", context: str = ""):
    """Log LLM API request"""
    security_logger = get_security_logger()
    mask_status = "MASKED" if masked else "UNMASKED"
    security_logger.info(f"LLM_REQUEST: Sending {mask_status} {data_type} to LLM. Context: {context}")


def log_auth_event(event_type: str, user_id: str = "", success: bool = True, details: str = ""):
    """Log authentication/authorization events"""
    security_logger = get_security_logger()
    status = "SUCCESS" if success else "FAILURE"
    security_logger.info(f"AUTH_{event_type.upper()}: {status} - User: {user_id} - {details}")


def log_data_access(user_id: str, resource: str, action: str = "READ"):
    """Log data access events"""
    security_logger = get_security_logger()
    security_logger.info(f"DATA_ACCESS: User {user_id} performed {action} on {resource}")


# Example usage in application code:
"""
from app.logging_config import (
    log_masking_operation,
    log_encryption_operation,
    log_decryption_operation,
    log_password_usage,
    log_llm_request
)

# In categorization agent
log_masking_operation(len(transactions), "categorization")
log_llm_request(masked=True, data_type="transactions", context="categorization")

# In main.py before database save
log_encryption_operation(len(transactions), "process_statement")

# In main.py when retrieving transactions
log_decryption_operation(len(transactions), current_user.user_id, "get_statement_details")

# In main.py when using PDF password
log_password_usage("PDF decryption")
"""
