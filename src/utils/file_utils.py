"""
File utility functions for the E-Paper Automation project.
"""

import os
import shutil
import tempfile
from pathlib import Path
from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def create_temp_directory():
    """
    Create a temporary directory for processing files.
    
    Returns:
        str: Path to the temporary directory.
    """
    temp_dir = tempfile.mkdtemp(dir=settings.TEMP_DIR)
    logger.info(f"Created temporary directory: {temp_dir}")
    return temp_dir

def cleanup_temp_directory(temp_dir):
    """
    Clean up a temporary directory.
    
    Args:
        temp_dir (str): Path to the temporary directory.
    """
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        logger.info(f"Cleaned up temporary directory: {temp_dir}")

def get_output_path(pdf_path, suffix=None, extension=None):
    """
    Generate an output path for a processed file.
    
    Args:
        pdf_path (str): Path to the original PDF file.
        suffix (str, optional): Suffix to add to the filename. Defaults to None.
        extension (str, optional): File extension for the output file. Defaults to None.
        
    Returns:
        str: Path to the output file.
    """
    pdf_filename = os.path.basename(pdf_path)
    pdf_name = os.path.splitext(pdf_filename)[0]
    
    if suffix:
        pdf_name = f"{pdf_name}_{suffix}"
    
    if extension:
        if not extension.startswith('.'):
            extension = f".{extension}"
        output_filename = f"{pdf_name}{extension}"
    else:
        output_filename = f"{pdf_name}.pdf"
    
    output_path = os.path.join(settings.OUTPUT_DIR, output_filename)
    return output_path

def ensure_directory_exists(directory):
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory (str): Path to the directory.
        
    Returns:
        str: Path to the directory.
    """
    os.makedirs(directory, exist_ok=True)
    return directory

def list_pdf_files(directory=None):
    """
    List all PDF files in a directory.
    
    Args:
        directory (str, optional): Directory to search for PDF files. 
                                  Defaults to settings.PDF_DIR.
        
    Returns:
        list: List of paths to PDF files.
    """
    if directory is None:
        directory = settings.PDF_DIR
    
    pdf_files = []
    for file in os.listdir(directory):
        if file.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(directory, file))
    
    return pdf_files 