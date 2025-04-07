import os
import fitz  # PyMuPDF
import pdfplumber
import io
import shutil
import sys
from article_segmenter import NewspaperArticleSegmenter
from PIL import Image, ImageDraw

class ArticleExtractor:
    """
    Extract individual articles from newspaper PDFs and save them as image files.
    Uses the NewspaperArticleSegmenter to detect article boundaries.
    """
    
    def __init__(self, output_dir="extracted_articles"):
        """
        Initialize the article extractor
        
        Args:
            output_dir: Directory to save extracted article images
        """
        self.output_dir = output_dir
        self.segmenter = NewspaperArticleSegmenter()
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
    def extract_articles_from_pdf(self, pdf_path):
        """
        Extract all articles from a PDF and save them as separate image files
        
        Args:
            pdf_path: Path to the input PDF file
            
        Returns:
            Directory containing all extracted articles
        """
        # Get PDF file name (without extension)
        pdf_filename = os.path.basename(pdf_path)
        pdf_name = os.path.splitext(pdf_filename)[0]
        
        # Create directory structure for this PDF
        pdf_dir = os.path.join(self.output_dir, pdf_name)
        
        # If directory exists, remove it to start fresh
        if os.path.exists(pdf_dir):
            shutil.rmtree(pdf_dir)
            
        os.makedirs(pdf_dir, exist_ok=True)
        
        print(f"Extracting articles from {pdf_filename}...")
        
        # Process each page
        with fitz.open(pdf_path) as pdf_doc:
            with pdfplumber.open(pdf_path) as pdf_plumber:
                for page_num in range(len(pdf_doc)):
                    print(f"Processing page {page_num + 1}/{len(pdf_doc)}")
                    
                    # Create page directory
                    page_dir = os.path.join(pdf_dir, f"page{page_num + 1}")
                    os.makedirs(page_dir, exist_ok=True)
                    
                    # Get the page
                    page = pdf_doc[page_num]
                    page_plumber = pdf_plumber.pages[page_num]
                    
                    # Create a PIL draw object (needed for the segmenter)
                    width = int(page_plumber.width)
                    height = int(page_plumber.height)
                    viz_img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
                    draw = ImageDraw.Draw(viz_img)
                    
                    # Use the segmenter to detect article regions
                    # Pass is_first_page parameter to handle different header sizes
                    article_regions = self.segmenter._extract_article_regions(
                        page_plumber, 
                        draw,
                        is_first_page=(page_num == 0)
                    )
                    
                    # Extract and save each article
                    for idx, region in enumerate(article_regions):
                        article_num = idx + 1
                        article_path = os.path.join(page_dir, f"article{article_num}.png")
                        
                        # Extract article using PyMuPDF
                        self._extract_region_as_image(page, region, article_path)
                        
                        print(f"  Saved article #{article_num} to {article_path}")
        
        print(f"Extraction complete! All articles saved to: {pdf_dir}")
        return pdf_dir
    
    def _extract_region_as_image(self, page, region, output_path):
        """
        Extract a region from a PDF page and save it as an image
        
        Args:
            page: fitz.Page object
            region: Dictionary with 'box' coordinates [x0, y0, x1, y1]
            output_path: Path to save the extracted image
        """
        # Create a rectangle with the region coordinates
        x0, y0, x1, y1 = region['box']
        rect = fitz.Rect(x0, y0, x1, y1)
        
        # Render the page region to a pixmap
        # Use a higher zoom factor for better quality
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, clip=rect)
        
        # Save the pixmap as PNG
        pix.save(output_path)

# Example usage
if __name__ == "__main__":
    pdf_path = "/Users/arup/Documents/EpaperAutomation/Sample.pdf"  # CHANGE THIS PATH
    output_dir = "extracted_articles"
    
    print(f"Processing PDF: {pdf_path}")
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        sys.exit(1)
        
    # Create extractor
    extractor = ArticleExtractor(output_dir=output_dir)
    
    # Process the PDF
    try:
        output_dir = extractor.extract_articles_from_pdf(pdf_path)
        print(f"All articles extracted to: {output_dir}")
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        sys.exit(1)