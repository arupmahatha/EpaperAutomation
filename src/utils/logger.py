"""
Logger utility for the E-Paper Automation project.
"""

import logging
import os
from datetime import datetime
from src.config import settings

def setup_logger(name=None):
    """
    Set up and return a logger instance.
    
    Args:
        name (str, optional): Name of the logger. Defaults to None.
        
    Returns:
        logging.Logger: Configured logger instance.
    """
    if name is None:
        name = "epaper_automation"
    
    logger = logging.getLogger(name)
    
    # Set logging level from settings
    level = getattr(logging, settings.LOGGING["level"])
    logger.setLevel(level)
    
    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(settings.LOGGING["file"])
    os.makedirs(log_dir, exist_ok=True)
    
    # Create file handler
    file_handler = logging.FileHandler(settings.LOGGING["file"])
    file_handler.setLevel(level)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set formatter for handlers
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger 