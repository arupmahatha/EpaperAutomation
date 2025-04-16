import os
import fitz  # PyMuPDF
import pdfplumber
import io
import shutil
import sys
import base64
import requests
from PIL import Image, ImageDraw

class PDFProcessor:
    """
    Process newspaper PDFs by extracting articles, creating visualizations, and generating analyzed PDFs with clickable links.
    """
    
    def __init__(self, output_dir):
        """
        Initialize the PDF processor
        
        Args:
            output_dir: Directory to save processed PDFs and extracted articles
        """
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
    def _upload_article_to_api(self, image_path, filename):
        """
        Upload an article image to the API
        
        Args:
            image_path: Path to the image file
            filename: The filename to be used in the API request
            
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
            response = requests.post("https://588dc01637.execute-api.ap-south-1.amazonaws.com/v1/paper-article-upload", json=payload)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error uploading article: {str(e)}")
            return None
        
    def extract_articles_from_pdf(self, pdf_path):
        """
        Extract all articles from a PDF and save them as separate image files
        
        Args:
            pdf_path: Path to the input PDF file
            
        Returns:
            tuple: (analyzed_pdf_path, article_urls)
                - analyzed_pdf_path: Path to the analyzed PDF with clickable links
                - article_urls: Dictionary mapping article numbers to their public URLs
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
        
        # Dictionary to store article URLs
        article_urls = {}
        
        # Create a new PDF for the analyzed version
        analyzed_pdf_path = os.path.join(pdf_dir, f"{pdf_name}_analysed.pdf")
        
        # Process each page
        with fitz.open(pdf_path) as pdf_doc:
            output_pdf = fitz.open()
            
            with pdfplumber.open(pdf_path) as pdf_plumber:
                for page_num in range(len(pdf_doc)):
                    print(f"Processing page {page_num + 1}/{len(pdf_doc)}")
                    
                    # Create page directory
                    page_dir = os.path.join(pdf_dir, f"page{page_num + 1}")
                    os.makedirs(page_dir, exist_ok=True)
                    
                    # Get the page
                    page = pdf_doc[page_num]
                    page_plumber = pdf_plumber.pages[page_num]
                    
                    # Create a PIL draw object for visualization
                    width = int(page_plumber.width)
                    height = int(page_plumber.height)
                    viz_img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
                    draw = ImageDraw.Draw(viz_img)
                    
                    # Calculate top margin to ignore
                    margin_percent = 14.5 if page_num == 0 else 8.5
                    top_margin = page_plumber.height * (margin_percent / 100)
                    
                    # Get all images from the page
                    images = page_plumber.images
                    article_count = 0
                    
                    for img_obj in images:
                        # Get coordinates
                        x0, y0 = img_obj['x0'], img_obj['top']
                        x1 = x0 + img_obj['width']
                        y1 = y0 + img_obj['height']
                        
                        # Skip regions in top margin
                        if y1 <= top_margin:
                            continue
                            
                        # Adjust regions overlapping with top margin
                        if y0 < top_margin:
                            y0 = top_margin
                        
                        # Calculate area ratio
                        area = (x1 - x0) * (y1 - y0)
                        page_area = page_plumber.width * page_plumber.height
                        area_ratio = area / page_area
                        
                        # Skip very small or very large regions
                        if area_ratio < 0.01 or area_ratio > 0.85:
                            continue
                        
                        article_count += 1
                        print(f"\nProcessing article #{article_count} on page {page_num + 1}")
                        
                        # Extract article as image
                        article_path = os.path.join(page_dir, f"article{article_count}.png")
                        print(f"1. Extracting article to {article_path}")
                        rect = fitz.Rect(x0, y0, x1, y1)
                        zoom = 3.0
                        mat = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=mat, clip=rect)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        img.save(article_path, "PNG", quality=95)
                        
                        # Upload to API with consistent article numbering
                        filename = f"page{page_num + 1}-article{article_count}"
                        api_response = self._upload_article_to_api(article_path, filename)
                        
                        if api_response:
                            public_url = api_response.get('public_url')
                            article_urls[filename] = public_url
                            print(f"3. Upload successful! Public URL: {public_url}")
                            
                            # Draw green rectangle with some transparency
                            draw.rectangle([x0, y0, x1, y1], outline=(0, 255, 0, 180), width=3)
                            
                            # Add a label in the top-left corner with consistent numbering
                            label = f"Article #{article_count}"
                            text_width, text_height = draw.textlength(label, font=None), 20
                            draw.rectangle(
                                [x0, y0, x0 + text_width + 10, y0 + text_height], 
                                fill=(0, 255, 0, 180)
                            )
                            draw.text((x0 + 5, y0), label, fill=(0, 0, 0, 255))
                        else:
                            print(f"3. Upload failed for article #{article_count}")
                        
                        print("---")
                    
                    # Convert PIL image to bytes
                    img_bytes = io.BytesIO()
                    viz_img.save(img_bytes, format='PNG')
                    img_bytes.seek(0)
                    
                    # Copy original page to output PDF
                    output_pdf.insert_pdf(pdf_doc, from_page=page_num, to_page=page_num)
                    page = output_pdf[-1]  # Get last added page
                    
                    # Add semi-transparent white overlay
                    shape = page.new_shape()
                    shape.draw_rect(page.rect)
                    shape.finish(color=(1, 1, 1), fill=(1, 1, 1), fill_opacity=0.2)
                    shape.commit()
                    
                    # Insert visualization
                    rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
                    page.insert_image(rect, stream=img_bytes.getvalue())
                    
                    # Add clickable links for each article
                    for i in range(article_count):
                        filename = f"page{page_num + 1}-article{i + 1}"
                        if filename in article_urls:
                            # Get the article region coordinates from the filtered images
                            # We need to find the corresponding image object for this article
                            img_index = 0
                            for img_obj in images:
                                # Skip regions in top margin
                                if img_obj['top'] + img_obj['height'] <= top_margin:
                                    continue
                                    
                                # Skip very small or very large regions
                                area = (img_obj['width']) * (img_obj['height'])
                                page_area = page_plumber.width * page_plumber.height
                                area_ratio = area / page_area
                                if area_ratio < 0.01 or area_ratio > 0.85:
                                    continue
                                    
                                if img_index == i:
                                    x0, y0 = img_obj['x0'], img_obj['top']
                                    x1 = x0 + img_obj['width']
                                    y1 = y0 + img_obj['height']
                                    
                                    # Create link
                                    rect = fitz.Rect(x0, y0, x1, y1)
                                    link = {
                                        "kind": fitz.LINK_URI,
                                        "uri": article_urls[filename],
                                        "from": rect
                                    }
                                    page.insert_link(link)
                                    break
                                img_index += 1
            
            # Save the analyzed PDF
            output_pdf.save(analyzed_pdf_path)
            output_pdf.close()
        
        print(f"Extraction complete! All articles saved to: {pdf_dir}")
        print(f"Analyzed PDF saved to: {analyzed_pdf_path}")
        return analyzed_pdf_path, article_urls

# Example usage
if __name__ == "__main__":
    pdf_path = "sample.pdf"  # Path to the input PDF file
    output_dir = "phase_1_output"
    
    print(f"Processing PDF: {pdf_path}")
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        sys.exit(1)
        
    # Create extractor
    extractor = PDFProcessor(output_dir=output_dir)
    
    # Process the PDF
    try:
        analyzed_pdf_path, article_urls = extractor.extract_articles_from_pdf(pdf_path)
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        sys.exit(1)