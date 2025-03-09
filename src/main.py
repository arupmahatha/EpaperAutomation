"""
Main module for the E-Paper Automation project.
"""

import os
import argparse
import cv2
import numpy as np
from typing import Dict, List, Any, Optional
import pytesseract
from src.config import settings
from src.utils.logger import setup_logger
from src.utils.file_utils import list_pdf_files, get_output_path, ensure_directory_exists
from src.pdf_processing.pdf_extractor import PDFExtractor
from src.region_detection.detector import RegionDetector, Region
from src.translation.translator import Translator
from src.article_generation.article_generator import ArticleGenerator

logger = setup_logger(__name__)

class EpaperAutomation:
    """
    Main class for the E-Paper Automation project.
    """
    
    def __init__(self):
        """
        Initialize the EpaperAutomation.
        """
        self.pdf_extractor = None
        self.region_detector = RegionDetector()
        self.translator = Translator()
        self.article_generator = ArticleGenerator()
        
    def process_pdf(self, pdf_path: str, output_dir: str = None, visualize: bool = False) -> Dict[str, Any]:
        """
        Process a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file.
            output_dir (str, optional): Directory to save output files.
                                      Defaults to None (use settings.OUTPUT_DIR).
            visualize (bool, optional): Whether to visualize detected regions.
                                      Defaults to False.
            
        Returns:
            Dict[str, Any]: Dictionary containing processing results.
        """
        if output_dir is None:
            output_dir = settings.OUTPUT_DIR
            
        ensure_directory_exists(output_dir)
        
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Extract images from PDF
        with PDFExtractor(pdf_path) as pdf_extractor:
            self.pdf_extractor = pdf_extractor
            images = pdf_extractor.extract_images()
            
            if not images:
                logger.error(f"No images extracted from PDF: {pdf_path}")
                return {"error": "No images extracted from PDF"}
            
            # Process each page
            results = []
            
            for page_num, image in enumerate(images):
                logger.info(f"Processing page {page_num+1} of {len(images)}")
                
                # Convert PIL Image to numpy array for OpenCV
                image_np = np.array(image)
                
                # Detect regions
                regions = self.region_detector.detect_regions(image_np)
                
                if not regions:
                    logger.warning(f"No regions detected on page {page_num+1}")
                    continue
                
                # Extract text from regions
                region_images = self.region_detector.extract_region_images(image_np)
                
                for region in regions:
                    region_image = region_images[region.id]
                    text = pytesseract.image_to_string(region_image, lang='eng+tel')
                    region.text = text
                
                # Visualize regions if requested
                if visualize:
                    vis_image = self.region_detector.visualize_regions(image_np)
                    vis_path = get_output_path(pdf_path, f"page_{page_num+1}_regions", "png")
                    cv2.imwrite(vis_path, cv2.cvtColor(vis_image, cv2.COLOR_RGB2BGR))
                    logger.info(f"Saved visualization to {vis_path}")
                
                # Translate regions
                regions_by_language = {settings.TRANSLATION["source_language"]: regions}
                
                for target_language in settings.TRANSLATION["target_languages"]:
                    translated_regions = self.translator.translate_regions(
                        regions, target_language, settings.TRANSLATION["source_language"]
                    )
                    regions_by_language[target_language] = translated_regions
                
                # Generate articles
                article_paths_by_language = self.article_generator.generate_multilingual_articles(
                    regions_by_language, pdf_path, output_dir
                )
                
                # Collect results
                page_result = {
                    "page_num": page_num + 1,
                    "num_regions": len(regions),
                    "regions": [region.to_dict() for region in regions],
                    "article_paths": article_paths_by_language
                }
                
                results.append(page_result)
            
            # Return results
            return {
                "pdf_path": pdf_path,
                "num_pages": len(images),
                "results": results
            }
    
    def process_directory(self, directory: str = None, output_dir: str = None, visualize: bool = False) -> List[Dict[str, Any]]:
        """
        Process all PDF files in a directory.
        
        Args:
            directory (str, optional): Directory containing PDF files.
                                     Defaults to None (use settings.PDF_DIR).
            output_dir (str, optional): Directory to save output files.
                                      Defaults to None (use settings.OUTPUT_DIR).
            visualize (bool, optional): Whether to visualize detected regions.
                                      Defaults to False.
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing processing results.
        """
        if directory is None:
            directory = settings.PDF_DIR
            
        if output_dir is None:
            output_dir = settings.OUTPUT_DIR
            
        ensure_directory_exists(output_dir)
        
        # List PDF files
        pdf_files = list_pdf_files(directory)
        
        if not pdf_files:
            logger.error(f"No PDF files found in directory: {directory}")
            return []
        
        # Process each PDF file
        results = []
        
        for pdf_path in pdf_files:
            result = self.process_pdf(pdf_path, output_dir, visualize)
            results.append(result)
        
        return results


def main():
    """
    Main function for the E-Paper Automation project.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="E-Paper Automation")
    parser.add_argument("--pdf", help="Path to a PDF file to process")
    parser.add_argument("--dir", help="Directory containing PDF files to process")
    parser.add_argument("--output", help="Directory to save output files")
    parser.add_argument("--visualize", action="store_true", help="Visualize detected regions")
    args = parser.parse_args()
    
    # Create EpaperAutomation instance
    automation = EpaperAutomation()
    
    # Process PDF file or directory
    if args.pdf:
        result = automation.process_pdf(args.pdf, args.output, args.visualize)
        logger.info(f"Processed PDF: {args.pdf}")
        logger.info(f"Result: {result}")
    elif args.dir:
        results = automation.process_directory(args.dir, args.output, args.visualize)
        logger.info(f"Processed {len(results)} PDF files in directory: {args.dir}")
    else:
        # Process default directory
        results = automation.process_directory(None, args.output, args.visualize)
        logger.info(f"Processed {len(results)} PDF files in default directory")


if __name__ == "__main__":
    main() 