from flask import Flask, render_template, send_file, jsonify, request, make_response
import os
import fitz
import pdfplumber
from article_segmenter import NewspaperArticleSegmenter
from extract_articles import ArticleExtractor
import tempfile
import shutil
from PIL import Image, ImageDraw
import io
import traceback

app = Flask(__name__)

class PDFWebViewer:
    def __init__(self, output_dir="web_viewer_output"):
        self.output_dir = output_dir
        self.segmenter = NewspaperArticleSegmenter()
        self.extractor = ArticleExtractor()
        self.current_pdf = None
        self.article_regions = {}
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
    def process_pdf(self, pdf_path):
        """Process a PDF and prepare it for web viewing"""
        try:
            self.current_pdf = pdf_path
            pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
            
            # Create a temporary directory for this PDF
            temp_dir = os.path.join(self.output_dir, pdf_name)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            
            # Process the PDF to get article regions
            with fitz.open(pdf_path) as pdf_doc:
                for page_num in range(len(pdf_doc)):
                    page = pdf_doc[page_num]
                    page_key = f"page_{page_num + 1}"
                    self.article_regions[page_key] = []
                    
                    # Convert page to image
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # Save page image
                    page_img_path = os.path.join(temp_dir, f"page_{page_num + 1}.png")
                    img.save(page_img_path)
                    
                    # Extract article regions
                    with pdfplumber.open(pdf_path) as pdf_plumber:
                        page_plumber = pdf_plumber.pages[page_num]
                        viz_img = Image.new('RGBA', (img.width, img.height), (255, 255, 255, 0))
                        draw = ImageDraw.Draw(viz_img)
                        
                        regions = self.segmenter._extract_article_regions(
                            page_plumber,
                            draw,
                            is_first_page=(page_num == 0)
                        )
                        
                        # Save each article region
                        for idx, region in enumerate(regions):
                            article_num = idx + 1
                            article_path = os.path.join(temp_dir, f"page_{page_num + 1}_article_{article_num}.png")
                            
                            # Extract and save the article image
                            self.extractor._extract_region_as_image(page, region, article_path)
                            
                            # Store region information
                            self.article_regions[page_key].append({
                                'id': f"page_{page_num + 1}_article_{article_num}",
                                'box': region['box'],
                                'image_path': f"page_{page_num + 1}_article_{article_num}.png"
                            })
            
            return temp_dir
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            print(traceback.format_exc())
            raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/load_pdf', methods=['GET'])
def load_pdf():
    try:
        if not viewer.current_pdf:
            return make_response(jsonify({'error': 'No PDF loaded'}), 400)
        
        pdf_name = os.path.splitext(os.path.basename(viewer.current_pdf))[0]
        return make_response(jsonify({
            'pdf_name': pdf_name,
            'article_regions': viewer.article_regions
        }), 200)
    except Exception as e:
        print(f"Error in load_pdf: {str(e)}")
        print(traceback.format_exc())
        return make_response(jsonify({'error': str(e)}), 500)

@app.route('/image/<path:image_path>')
def get_image(image_path):
    try:
        # Get the PDF name directory from the current PDF path
        pdf_name = os.path.splitext(os.path.basename(viewer.current_pdf))[0]
        # Construct the full path to the image
        full_image_path = os.path.join(viewer.output_dir, pdf_name, image_path)
        if os.path.exists(full_image_path):
            return send_file(full_image_path)
        else:
            return make_response(jsonify({'error': 'Image not found'}), 404)
    except Exception as e:
        print(f"Error getting image: {str(e)}")
        print(traceback.format_exc())
        return make_response(jsonify({'error': str(e)}), 500)

if __name__ == '__main__':
    viewer = PDFWebViewer()
    
    # Set your PDF path here
    pdf_path = "/Users/arup/Documents/EpaperAutomation/Sample.pdf"  # Change this to your PDF path
    viewer.process_pdf(pdf_path)
    
    app.run(debug=True) 