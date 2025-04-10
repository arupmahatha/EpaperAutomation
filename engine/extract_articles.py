import os
import fitz  # PyMuPDF
import pdfplumber
import io
import shutil
import sys
import base64
import requests
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
        self.api_url = "https://588dc01637.execute-api.ap-south-1.amazonaws.com/v1/paper-article-upload"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
    def _upload_article_to_api(self, image_path, filename):
        """
        Upload an article image to the API
        
        Args:
            image_path: Path to the image file
            filename: Name to use for the uploaded file
            
        Returns:
            dict: API response containing public_url
        """
        try:
            # Read image and convert to base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Prepare request payload
            payload = {
                "image": base64_image,
                "is_base64": True,
                "filename": filename
            }
            
            # Make API request
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()  # Raise exception for bad status codes
            
            return response.json()
            
        except Exception as e:
            print(f"Error uploading {filename}: {str(e)}")
            return None
        
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
                        
                        # Upload to API
                        filename = f"page{page_num + 1}-article{article_num}"
                        api_response = self._upload_article_to_api(article_path, filename)
                        
                        if api_response:
                            print(f"  Uploaded article #{article_num} to {api_response.get('public_url', 'unknown')}")
                        else:
                            print(f"  Failed to upload article #{article_num}")
                        
                        print(f"  Saved article #{article_num} to {article_path}")
        
        print(f"Extraction complete! All articles saved to: {pdf_dir}")
        return pdf_dir
    
    def _extract_region_as_image(self, page, region, output_path):
        """
        Extract a region from a PDF page and save it as an image
        
        Args:
            page: fitz.Page object
            region: Dictionary with 'box' coordinates [x0, y0, x1, y1] and original_box
            output_path: Path to save the extracted image
        """
        # Use original coordinates for extraction
        x0, y0, x1, y1 = region.get('original_box', region['box'])
        rect = fitz.Rect(x0, y0, x1, y1)
        
        # Render the page region to a pixmap with high resolution
        zoom = 3.0  # Higher zoom factor for better quality
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, clip=rect)
        
        # Convert to PIL Image for potential post-processing
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Enhance image if needed (optional)
        # from PIL import ImageEnhance
        # enhancer = ImageEnhance.Sharpness(img)
        # img = enhancer.enhance(1.2)
        
        # Save with high quality
        img.save(output_path, "PNG", quality=95)

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