"""
PDF extraction module for the E-Paper Automation project.
"""

import os
import tempfile
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import numpy as np
from src.config import settings
from src.utils.logger import setup_logger
from src.utils.file_utils import create_temp_directory, cleanup_temp_directory

logger = setup_logger(__name__)

class PDFExtractor:
    """
    Class for extracting content from PDF files.
    """
    
    def __init__(self, pdf_path):
        """
        Initialize the PDFExtractor.
        
        Args:
            pdf_path (str): Path to the PDF file.
        """
        self.pdf_path = pdf_path
        self.temp_dir = None
        self.images = []
        self.dpi = 300  # Default DPI for PDF conversion
        
    def __enter__(self):
        """
        Context manager entry point.
        
        Returns:
            PDFExtractor: The PDFExtractor instance.
        """
        self.temp_dir = create_temp_directory()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit point.
        
        Args:
            exc_type: Exception type.
            exc_val: Exception value.
            exc_tb: Exception traceback.
        """
        self.cleanup()
        
    def cleanup(self):
        """
        Clean up temporary files and directories.
        """
        if self.temp_dir:
            cleanup_temp_directory(self.temp_dir)
            self.temp_dir = None
        
    def extract_images(self, pages=None, dpi=None):
        """
        Extract images from the PDF file.
        
        Args:
            pages (list, optional): List of page numbers to extract. Defaults to None (all pages).
            dpi (int, optional): DPI for image extraction. Defaults to None (use self.dpi).
            
        Returns:
            list: List of extracted images as PIL Image objects.
        """
        if dpi is not None:
            self.dpi = dpi
            
        logger.info(f"Extracting images from PDF: {self.pdf_path}")
        
        try:
            # Convert PDF to images
            self.images = convert_from_path(
                self.pdf_path,
                dpi=self.dpi,
                output_folder=self.temp_dir,
                fmt="png",
                paths_only=False,
                first_page=pages[0] if pages else None,
                last_page=pages[-1] if pages else None
            )
            
            logger.info(f"Extracted {len(self.images)} images from PDF")
            return self.images
            
        except Exception as e:
            logger.error(f"Error extracting images from PDF: {e}")
            raise
    
    def extract_text(self, page_num=None):
        """
        Extract text from the PDF using OCR.
        
        Args:
            page_num (int, optional): Page number to extract text from. Defaults to None (all pages).
            
        Returns:
            str or dict: Extracted text as a string (for a single page) or a dictionary (for multiple pages).
        """
        if not self.images:
            self.extract_images()
            
        logger.info(f"Extracting text from PDF: {self.pdf_path}")
        
        try:
            if page_num is not None:
                if page_num < 0 or page_num >= len(self.images):
                    raise ValueError(f"Invalid page number: {page_num}")
                
                # Extract text from a single page
                image = self.images[page_num]
                text = pytesseract.image_to_string(image, lang='eng+tel')
                return text
            else:
                # Extract text from all pages
                result = {}
                for i, image in enumerate(self.images):
                    text = pytesseract.image_to_string(image, lang='eng+tel')
                    result[i] = text
                return result
                
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    def save_images(self, output_dir=None, prefix=None):
        """
        Save extracted images to disk.
        
        Args:
            output_dir (str, optional): Directory to save images to. Defaults to None (use settings.OUTPUT_DIR).
            prefix (str, optional): Prefix for image filenames. Defaults to None.
            
        Returns:
            list: List of paths to saved images.
        """
        if not self.images:
            self.extract_images()
            
        if output_dir is None:
            output_dir = settings.OUTPUT_DIR
            
        if prefix is None:
            prefix = os.path.splitext(os.path.basename(self.pdf_path))[0]
            
        os.makedirs(output_dir, exist_ok=True)
        
        image_paths = []
        for i, image in enumerate(self.images):
            image_path = os.path.join(output_dir, f"{prefix}_page_{i+1}.png")
            image.save(image_path, "PNG")
            image_paths.append(image_path)
            
        logger.info(f"Saved {len(image_paths)} images to {output_dir}")
        return image_paths
    
    def get_image_as_array(self, page_num=0):
        """
        Get an image as a numpy array.
        
        Args:
            page_num (int, optional): Page number to get. Defaults to 0.
            
        Returns:
            numpy.ndarray: Image as a numpy array.
        """
        if not self.images:
            self.extract_images()
            
        if page_num < 0 or page_num >= len(self.images):
            raise ValueError(f"Invalid page number: {page_num}")
            
        return np.array(self.images[page_num]) 