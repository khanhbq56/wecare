# utils/logging.py
import sys
import logging
import os
from logging.handlers import TimedRotatingFileHandler

def setup_logging():
    """
    Configure logging for the application
    
    Returns:
        logging.Logger: Configured logger
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Configure logging
    logger = logging.getLogger("patient-care-api")
    
    if logger.handlers:
        logger.handlers = []
        
    logger.setLevel(logging.INFO)
    
    # Formatter for logs
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with log rotation
    file_handler = TimedRotatingFileHandler(
        "logs/api.log",
        when="midnight",
        interval=1,
        backupCount=7,  # Keep logs for 7 days
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger