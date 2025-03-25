import pdfplumber
from PIL import Image, ImageDraw
import os
import tempfile
try:
    import fitz  # PyMuPDF
except ImportError:
    from PyMuPDF import fitz  # Alternative import method
import io

class LayoutParser:
    def __init__(self, pdf_path):
        """Initialize the layout parser with a PDF file path."""
        self.pdf_path = pdf_path
        
    def analyze_page(self, page_number=0, display=True, output_path=None):
        """Analyze a specific page of the PDF and overlay the analysis on the PDF itself."""
        # Extract elements using pdfplumber
        elements = None
        with pdfplumber.open(self.pdf_path) as pdf:
            page = pdf.pages[page_number]
            width = int(page.width)
            height = int(page.height)
            
            # Create transparent visualization image
            viz_img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            draw = ImageDraw.Draw(viz_img)
            
            # Extract and process elements
            elements = self._extract_elements(page, draw)
        
        # Now overlay the visualization on the PDF using PyMuPDF
        output_path = output_path or self.pdf_path.replace('.pdf', '_analyzed.pdf')
        self._overlay_on_pdf(viz_img, page_number, output_path)
        
        if display:
            self._display_pdf(output_path)
            
        return elements, output_path
    
    def _extract_elements(self, page, draw):
        """Extract and visualize different elements from the page."""
        elements = {
            'words': [],
            'tables': [],
            'images': []
        }
        
        # Extract words with semi-transparent blue
        words = page.extract_words()
        elements['words'] = words
        for word in words:
            x0, y0, x1, y1 = word['x0'], word['top'], word['x1'], word['bottom']
            draw.rectangle([x0, y0, x1, y1], outline=(0, 0, 255, 128), width=1)
        
        # Extract tables with semi-transparent red
        tables = page.find_tables()
        elements['tables'] = tables
        for table in tables:
            x0, y0, x1, y1 = table.bbox
            draw.rectangle([x0, y0, x1, y1], outline=(255, 0, 0, 128), width=2)
        
        # Extract images with semi-transparent green
        images = page.images
        elements['images'] = images
        for img_obj in images:
            x0, y0 = img_obj['x0'], img_obj['top']
            x1 = x0 + img_obj['width']
            y1 = y0 + img_obj['height']
            draw.rectangle([x0, y0, x1, y1], outline=(0, 255, 0, 128), width=2)
        
        return elements
    
    def _overlay_on_pdf(self, viz_img, page_number, output_path):
        """Overlay the visualization on the PDF and save to output_path."""
        # Convert PIL image to bytes
        img_bytes = io.BytesIO()
        viz_img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Open the PDF with PyMuPDF
        pdf = fitz.open(self.pdf_path)
        page = pdf[page_number]
        
        # Reduce page brightness by adding a semi-transparent white overlay
        shape = page.new_shape()
        shape.draw_rect(page.rect)
        shape.finish(color=(1, 1, 1), fill=(1, 1, 1), fill_opacity=0.2)
        shape.commit()
        
        # Insert the visualization image
        rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
        page.insert_image(rect, stream=img_bytes.getvalue())
        
        # Save the modified PDF
        pdf.save(output_path)
        pdf.close()
    
    def _display_pdf(self, pdf_path):
        """Display the PDF using the system's default PDF viewer."""
        import subprocess
        import platform
        
        system = platform.system().lower()
        try:
            if system == 'darwin':  # macOS
                subprocess.run(['open', pdf_path])
            elif system == 'linux':
                subprocess.run(['xdg-open', pdf_path])
            elif system == 'windows':
                subprocess.run(['start', pdf_path], shell=True)
        except Exception as e:
            print(f"Could not open PDF: {str(e)}") 