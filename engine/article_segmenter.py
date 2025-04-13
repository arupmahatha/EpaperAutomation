import pdfplumber
from PIL import Image, ImageDraw
import os
try:
    import fitz  # PyMuPDF
except ImportError:
    from PyMuPDF import fitz  # Alternative import method
import io
from typing import List, Dict, Any, Tuple
from datetime import datetime

class NewspaperArticleSegmenter:
    """
    Segment newspaper articles using pdfplumber to detect article regions.
    This class identifies article boundaries by looking for image boxes in the PDF.
    """
    
    def __init__(self, 
                output_dir: str = "output",
                temp_dir: str = "temp",
                min_area_ratio: float = 0.01,
                max_area_ratio: float = 0.85,
                first_page_margin_percent: float = 14.5,  # Typically first page has larger header
                other_pages_margin_percent: float = 8.5,  # Other pages usually have smaller headers
                date: str = None):  # Date in YYYY-MM-DD format
        """
        Initialize the newspaper article segmenter
        
        Args:
            output_dir: Directory to save results
            temp_dir: Directory for temporary files
            min_area_ratio: Minimum ratio of page area for a region to be considered an article
            max_area_ratio: Maximum ratio of page area for a region to be considered an article
                            (prevents entire page from being detected as an article)
            first_page_margin_percent: Percentage of the top of the first page to ignore
            other_pages_margin_percent: Percentage of the top of other pages to ignore
            date: Date in YYYY-MM-DD format
        """
        # Create directories if they don't exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        self.output_dir = output_dir
        self.temp_dir = temp_dir
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.first_page_margin_percent = first_page_margin_percent
        self.other_pages_margin_percent = other_pages_margin_percent
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.s3_base_url = "https://epaper-article-db.s3.ap-south-1.amazonaws.com/epaper-articles"
    
    def _generate_article_url(self, page_num: int, article_num: int) -> str:
        """
        Generate URL for an article based on page number and article number
        
        Args:
            page_num: Page number (1-based)
            article_num: Article number (1-based)
            
        Returns:
            Generated URL string
        """
        # Convert date from YYYY-MM-DD to YYYY/YYYYMMDD format
        year = self.date[:4]
        yyyymmdd = self.date.replace("-", "")
        return f"{self.s3_base_url}/{year}/{yyyymmdd}/page{page_num}-article{article_num}.jpg"
    
    def process_pdf(self, pdf_path: str) -> str:
        """
        Process a PDF file to detect and segment articles
        
        Args:
            pdf_path: Path to the input PDF file
            
        Returns:
            Path to the output PDF with segmented articles
        """
        pdf_filename = os.path.basename(pdf_path)
        pdf_name = os.path.splitext(pdf_filename)[0]
        output_filename = f"{pdf_name}_analysed.pdf"
        output_path = os.path.join(self.output_dir, output_filename)
        
        print(f"Processing {pdf_filename}...")
        
        # Open source PDF with PyMuPDF
        source_pdf = fitz.open(pdf_path)
        output_pdf = fitz.open()
        
        # Process each page
        with pdfplumber.open(pdf_path) as pdf_plumber:
            for page_num in range(len(source_pdf)):
                print(f"Processing page {page_num + 1}/{len(source_pdf)}")
                
                # Process with pdfplumber
                try:
                    page_plumber = pdf_plumber.pages[page_num]
                    
                    # Get page dimensions
                    width = int(page_plumber.width)
                    height = int(page_plumber.height)
                    
                    # Create visualization image
                    viz_img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
                    draw = ImageDraw.Draw(viz_img)
                    
                    # Extract article regions (as images)
                    article_regions = self._extract_article_regions(page_plumber, draw, is_first_page=(page_num == 0))
                    
                    # Update article numbers for this page
                    for i, region in enumerate(article_regions):
                        article_num = i + 1  # Start from 1 for each page
                        region['label'] = f'article_{article_num}'
                        region['url'] = self._generate_article_url(page_num + 1, article_num)
                        
                        # Update the article box text with the page-specific number
                        x0, y0, x1, y1 = region['box']
                        label = f"Article #{article_num}"
                        # Draw background for text
                        text_width, text_height = draw.textlength(label, font=None), 20
                        draw.rectangle(
                            [x0, y0, x0 + text_width + 10, y0 + text_height], 
                            fill=(0, 255, 0, 180)
                        )
                        # Draw text
                        draw.text((x0 + 5, y0), label, fill=(0, 0, 0, 255))
                    
                    # Convert PIL image to bytes
                    img_bytes = io.BytesIO()
                    viz_img.save(img_bytes, format='PNG')
                    img_bytes.seek(0)
                    
                    # Use PyMuPDF to overlay the visualization
                    # Copy original page to output PDF
                    output_pdf.insert_pdf(source_pdf, from_page=page_num, to_page=page_num)
                    page = output_pdf[-1]  # Get last added page
                    
                    # Add semi-transparent white overlay to reduce page brightness
                    shape = page.new_shape()
                    shape.draw_rect(page.rect)
                    shape.finish(color=(1, 1, 1), fill=(1, 1, 1), fill_opacity=0.2)
                    shape.commit()
                    
                    # Insert visualization
                    rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
                    page.insert_image(rect, stream=img_bytes.getvalue())
                    
                    # Add clickable links for each article region
                    for region in article_regions:
                        x0, y0, x1, y1 = region['box']
                        # Convert coordinates to PDF page coordinates
                        rect = fitz.Rect(x0, y0, x1, y1)
                        # Create link annotation
                        link = {
                            "kind": fitz.LINK_URI,
                            "uri": region['url'],
                            "from": rect
                        }
                        page.insert_link(link)
                        
                except Exception as e:
                    print(f"Error processing page {page_num}: {str(e)}")
                    # Add the page as-is if error occurs
                    output_pdf.insert_pdf(source_pdf, from_page=page_num, to_page=page_num)
        
        # Save the output PDF
        output_pdf.save(output_path)
        output_pdf.close()
        source_pdf.close()
        
        print(f"Analysis complete! Saved to: {output_path}")
        return output_path
    
    def _extract_article_regions(self, page, draw, is_first_page: bool = False) -> List[Dict[str, Any]]:
        """
        Extract article regions from a page using pdfplumber.
        
        Args:
            page: pdfplumber page object
            draw: PIL ImageDraw object for visualization
            is_first_page: Whether this is the first page of the newspaper
            
        Returns:
            List of article regions with coordinates
        """
        article_regions = []

        # Debug directory for saving intermediate steps
        debug_dir = os.path.join(self.temp_dir, "debug")
        os.makedirs(debug_dir, exist_ok=True)
        
        # Calculate top margin to ignore based on whether it's first page or not
        if is_first_page:
            margin_percent = self.first_page_margin_percent
            margin_label = "First page"
        else:
            margin_percent = self.other_pages_margin_percent
            margin_label = "Other page"
            
        top_margin = page.height * (margin_percent / 100)
        
        # Draw a line showing the top margin that's being ignored
        draw.line([(0, top_margin), (page.width, top_margin)], fill=(255, 0, 0, 180), width=2)
        draw.text((10, top_margin - 20), f"{margin_label}: Ignoring top {margin_percent}%", fill=(255, 0, 0, 255))
        
        # Get all images from the page (newspaper articles are often detected as images)
        images = page.images
        
        for i, img_obj in enumerate(images):
            # Get coordinates
            x0, y0 = img_obj['x0'], img_obj['top']
            x1 = x0 + img_obj['width']
            y1 = y0 + img_obj['height']
            
            # Skip regions that are entirely in the top margin
            if y1 <= top_margin:
                continue
                
            # For regions that partially overlap with the top margin, adjust them
            if y0 < top_margin:
                y0 = top_margin
            
            # Calculate area ratios
            area = (x1 - x0) * (y1 - y0)
            page_area = page.width * page.height
            area_ratio = area / page_area
            
            # Skip very small regions (likely not articles) and very large regions (likely full page)
            if area_ratio < self.min_area_ratio or area_ratio > self.max_area_ratio:
                continue
                
            # Check if it's almost covering the entire page (indicating it might be the page background)
            page_coverage = self._calculate_page_coverage([x0, y0, x1, y1], [0, 0, page.width, page.height])
            if page_coverage > 0.9:  # If it covers more than 90% of the page
                continue

            # Generate URL for this article
            article_url = self._generate_article_url(page.page_number + 1, i + 1)

            # Create region dictionary
            region = {
                'score': 1.0,
                'label': f'article_{i}',
                'box': [x0, y0, x1, y1],
                'original_box': [img_obj['x0'], img_obj['top'], 
                               img_obj['x0'] + img_obj['width'], 
                               img_obj['top'] + img_obj['height']],
                'url': article_url
            }
            article_regions.append(region)
            
            # Draw green rectangle with some transparency
            draw.rectangle([x0, y0, x1, y1], outline=(0, 255, 0, 180), width=3)
            
            # Add a label in the top-left corner with a filled background
            label = f"Article #{i+1}"
            # Draw background for text
            text_width, text_height = draw.textlength(label, font=None), 20
            draw.rectangle(
                [x0, y0, x0 + text_width + 10, y0 + text_height], 
                fill=(0, 255, 0, 180)
            )
            # Draw text
            draw.text((x0 + 5, y0), label, fill=(0, 0, 0, 255))
        
        # Also try to find boxes/tables that might contain articles
        tables = page.find_tables()
        
        for i, table in enumerate(tables):
            x0, y0, x1, y1 = table.bbox
            
            # Skip regions that are entirely in the top margin
            if y1 <= top_margin:
                continue
                
            # For regions that partially overlap with the top margin, adjust them
            if y0 < top_margin:
                y0 = top_margin
            
            # Calculate area ratios
            area = (x1 - x0) * (y1 - y0)
            page_area = page.width * page.height
            area_ratio = area / page_area
            
            # Skip very small regions (likely not articles) and very large regions (likely full page)
            if area_ratio < self.min_area_ratio or area_ratio > self.max_area_ratio:
                continue
                
            # Check if it's almost covering the entire page
            page_coverage = self._calculate_page_coverage([x0, y0, x1, y1], [0, 0, page.width, page.height])
            if page_coverage > 0.9:  # If it covers more than 90% of the page
                continue
                
            # Create region dictionary
            region = {
                'score': 0.9,
                'label': f'table_article_{i}',
                'box': [x0, y0, x1, y1],
                'original_box': [x0, y0, x1, y1],
                'url': self._generate_article_url(page.page_number + 1, len(images) + i + 1)
            }
            article_regions.append(region)
            
            # Draw red rectangle with some transparency
            draw.rectangle([x0, y0, x1, y1], outline=(255, 0, 0, 180), width=3)
            
            # Add a label
            label = f"Article #{len(images) + i+1}"
            # Draw background for text
            text_width, text_height = draw.textlength(label, font=None), 20
            draw.rectangle(
                [x0, y0, x0 + text_width + 10, y0 + text_height], 
                fill=(255, 0, 0, 180)
            )
            # Draw text
            draw.text((x0 + 5, y0), label, fill=(0, 0, 0, 255))
        
        # Add title showing the total number of articles detected
        if article_regions:
            title = f"Detected {len(article_regions)} article regions"
            draw.rectangle([10, 10, 400, 40], fill=(0, 0, 255, 180))
            draw.text((20, 15), title, fill=(255, 255, 255, 255))
        
        return article_regions
        
    def _calculate_page_coverage(self, region_box, page_box):
        """
        Calculate how much of the page the region covers
        
        Args:
            region_box: [x0, y0, x1, y1] of the region
            page_box: [x0, y0, x1, y1] of the page
            
        Returns:
            Coverage ratio (0-1)
        """
        # Simple calculation based on bounding box coordinates
        rx0, ry0, rx1, ry1 = region_box
        px0, py0, px1, py1 = page_box
        
        # Check for edge proximity
        left_edge_proximity = abs(rx0 - px0) / (px1 - px0)
        right_edge_proximity = abs(rx1 - px1) / (px1 - px0)
        top_edge_proximity = abs(ry0 - py0) / (py1 - py0)
        bottom_edge_proximity = abs(ry1 - py1) / (py1 - py0)
        
        # Average proximity to all edges (lower is closer to page boundaries)
        avg_edge_proximity = (left_edge_proximity + right_edge_proximity + 
                             top_edge_proximity + bottom_edge_proximity) / 4
        
        # If avg_edge_proximity is very low, it means the region is very close to page boundaries
        return 1 - avg_edge_proximity

# Example usage
if __name__ == "__main__":
    # Initialize segmenter
    segmenter = NewspaperArticleSegmenter()
    
    # Process a PDF
    pdf_path = "sample.pdf"
    if os.path.exists(pdf_path):
        output_path = segmenter.process_pdf(pdf_path)
        print(f"Output saved to: {output_path}")
    else:
        print(f"PDF file not found: {pdf_path}") 