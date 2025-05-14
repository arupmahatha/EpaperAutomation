import os
import cv2
import numpy as np
from PIL import Image, ImageDraw
import fitz  # PyMuPDF
import base64
import requests
import io
import pdfplumber

class ArticleExtractor:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def _upload_article_to_api(self, image_path, filename, pdf_name):
        """
        Upload an article image to the API
        
        Args:
            image_path: Path to the image file
            filename: The filename to be used in the API request
            pdf_name: The name of the PDF file
            
        Returns:
            dict: API response containing public_url
        """
        try:
            # Read image and convert to base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Prepare request payload
            api_filename = f"{pdf_name}-{filename}"
            payload = {
                "image": base64_image,
                "is_base64": True,
                "filename": api_filename
            }
            
            # Make API request
            response = requests.post("https://588dc01637.execute-api.ap-south-1.amazonaws.com/v1/paper-article-upload", json=payload)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error uploading article: {str(e)}")
            return None

    def _detect_articles_with_technique(self, gray, ignore_height, technique, cv_img=None):
        """
        Detect article bounding boxes using a specified technique.
        Returns: list of (x, y, w, h, cnt)
        """
        if technique == 'canny':
            # Edge detection (Canny)
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        elif technique == 'adaptive':
            # Adaptive thresholding
            edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY_INV, 25, 15)
        elif technique == 'morphology':
            # Morphological closing after threshold
            _, threshed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
            edges = cv2.morphologyEx(threshed, cv2.MORPH_CLOSE, kernel)
        else:
            raise ValueError(f"Unknown technique: {technique}")

        # Find all contours
        contours, hierarchy = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        closed_contours = []
        min_area = 30000
        max_area = gray.shape[1] * gray.shape[0] * 0.9
        min_perimeter = 500
        if hierarchy is not None:
            hierarchy = hierarchy[0]
            for idx, cnt in enumerate(contours):
                if hierarchy[idx][3] != -1:
                    continue
                area = cv2.contourArea(cnt)
                if area < min_area or area > max_area:
                    continue
                perimeter = cv2.arcLength(cnt, True)
                if perimeter < min_perimeter:
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = w / float(h)
                if aspect_ratio < 0.2 or aspect_ratio > 5.0:
                    continue
                closed_contours.append(cnt)
        rects = []
        for cnt in closed_contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if y < ignore_height:
                continue
            rects.append((x, y, w, h, cnt))
        # Filter overlapping/contained rectangles
        filtered_rects = []
        for i, (x1, y1, w1, h1, cnt1) in enumerate(rects):
            overlap = False
            for j, (x2, y2, w2, h2, cnt2) in enumerate(rects):
                if i == j:
                    continue
                if x1 > x2 and y1 > y2 and x1 + w1 < x2 + w2 and y1 + h1 < y2 + h2:
                    overlap = True
                    break
            if not overlap:
                filtered_rects.append((x1, y1, w1, h1, cnt1))
        return filtered_rects, edges

    def _rects_overlap(self, r1, r2, thresh=0.5):
        x1, y1, w1, h1, _ = r1
        x2, y2, w2, h2, _ = r2
        xa = max(x1, x2)
        ya = max(y1, y2)
        xb = min(x1 + w1, x2 + w2)
        yb = min(y1 + h1, y2 + h2)
        inter_area = max(0, xb - xa) * max(0, yb - ya)
        area1 = w1 * h1
        area2 = w2 * h2
        if area1 == 0 or area2 == 0:
            return False
        overlap1 = inter_area / area1
        overlap2 = inter_area / area2
        return overlap1 > thresh or overlap2 > thresh

    def detect_and_extract_articles(self, pdf_path):
        """
        Detect articles in a PDF, extract them as images, and upload to API
        
        Args:
            pdf_path: Path to the input PDF file
            
        Returns:
            tuple: (analyzed_pdf_path, article_urls)
                - analyzed_pdf_path: Path to the analyzed PDF with clickable links
                - article_urls: Dictionary mapping article numbers to their public URLs
        """
        # Create output directory
        # if not os.path.exists(output_dir):
        #     os.makedirs(output_dir, exist_ok=True) # Handled in __init__
        
        # Get PDF file name (without extension)
        pdf_filename = os.path.basename(pdf_path)
        pdf_name = os.path.splitext(pdf_filename)[0]
        
        # Create directory for this PDF
        pdf_dir = os.path.join(self.output_dir, pdf_name)
        if os.path.exists(pdf_dir):
            os.system(f'rm -rf {pdf_dir}')
        os.makedirs(pdf_dir, exist_ok=True)
        
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
                    pix = page.get_pixmap()
                    
                    # Convert to PIL Image
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # Convert to OpenCV format
                    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    
                    # Convert to grayscale
                    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                    
                    # Calculate top margin to ignore (14.5% of page height)
                    ignore_height = int(pix.height * 0.145)
                    
                    # Create a mask for the top portion
                    mask = np.ones_like(gray) * 255
                    mask[:ignore_height, :] = 0
                    
                    # Apply the mask to ignore top portion
                    masked_gray = cv2.bitwise_and(gray, gray, mask=mask)
                    
                    # Hybrid approach: run both 'adaptive' and 'canny', merge results
                    adaptive_rects, adaptive_edges = self._detect_articles_with_technique(masked_gray, ignore_height, 'adaptive')
                    canny_rects, canny_edges = self._detect_articles_with_technique(masked_gray, ignore_height, 'canny')

                    # Merge rectangles: if two rectangles overlap significantly, keep only one
                    merged_rects = list(adaptive_rects)
                    for c_rect in canny_rects:
                        if not any(self._rects_overlap(c_rect, a_rect) for a_rect in merged_rects):
                            merged_rects.append(c_rect)

                    filtered_rects = merged_rects
                    edges = adaptive_edges  # For visualization, use adaptive

                    # Create visualization
                    viz_img = cv_img.copy()
                    
                    # Draw a line to show the ignored top portion
                    cv2.line(viz_img, (0, ignore_height), (viz_img.shape[1], ignore_height), (0, 0, 255), 2)
                    
                    # Process each detected article
                    for idx, (x, y, w, h, cnt) in enumerate(filtered_rects):
                        # Create mask for the article
                        mask = np.zeros_like(gray)
                        cv2.drawContours(mask, [cnt], -1, 255, -1)
                        
                        # Extract article image
                        article_img = cv2.bitwise_and(cv_img, cv_img, mask=mask)
                        article_img = article_img[y:y+h, x:x+w]
                        
                        # Save article image
                        article_path = os.path.join(page_dir, f"article{idx+1}.png")
                        cv2.imwrite(article_path, article_img)
                        print(f"Saved article image to {article_path}")
                        
                        # Upload to API
                        filename = f"page{page_num + 1}-article{idx + 1}"
                        api_response = self._upload_article_to_api(article_path, filename, pdf_name)
                        
                        if api_response:
                            public_url = api_response.get('public_url')
                            article_urls[f"{pdf_name}-{filename}"] = public_url
                            print(f"Upload successful! Public URL: {public_url}")
                        else:
                            print(f"Upload failed for article #{idx + 1}")
                        
                        print()  # Add empty line between articles
                        
                        # Draw the contour
                        cv2.drawContours(viz_img, [cnt], -1, (0, 255, 0), 2)
                        # Get the center of the bounding box for placing the number
                        cx = x + w // 2
                        cy = y + h // 2
                        # Draw a filled circle background for the number
                        cv2.circle(viz_img, (cx, cy), 20, (0, 255, 0), -1)
                        # Add the number
                        cv2.putText(viz_img, str(idx + 1), (cx - 10, cy + 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
                    
                    # Save visualization
                    viz_path = os.path.join(pdf_dir, f"page{page_num + 1}_article_boundaries.png")
                    cv2.imwrite(viz_path, viz_img)
                    print(f"Saved visualization to {viz_path}")
                    
                    # Save edge image
                    edge_path = os.path.join(pdf_dir, f"page{page_num + 1}_edges.png")
                    cv2.imwrite(edge_path, edges)
                    print(f"Saved edge image to {edge_path}")
                    
                    print(f"Found {len(filtered_rects)} article boundaries")
                    
                    # Copy original page to output PDF
                    output_pdf.insert_pdf(pdf_doc, from_page=page_num, to_page=page_num)
                    page = output_pdf[-1]
                    
                    # Add semi-transparent white overlay
                    shape = page.new_shape()
                    shape.draw_rect(page.rect)
                    shape.finish(color=(1, 1, 1), fill=(1, 1, 1), fill_opacity=0.2)
                    shape.commit()
                    
                    # Add clickable links for each article
                    for idx, (x, y, w, h, cnt) in enumerate(filtered_rects):
                        filename = f"page{page_num + 1}-article{idx + 1}"
                        if f"{pdf_name}-{filename}" in article_urls:
                            # Create link
                            rect = fitz.Rect(x, y, x + w, y + h)
                            link = {
                                "kind": fitz.LINK_URI,
                                "uri": article_urls[f"{pdf_name}-{filename}"],
                                "from": rect
                            }
                            page.insert_link(link)
            
            # Save the analyzed PDF
            output_pdf.save(analyzed_pdf_path)
            output_pdf.close()
        
        print(f"Analyzed PDF saved to: {analyzed_pdf_path}")
        return analyzed_pdf_path, article_urls

if __name__ == "__main__":
    pdf_path = "6.pdf"  # Path to the input PDF file
    output_dir = "phase_1_output"
    
    print(f"Processing PDF: {pdf_path}")
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        exit(1)
    
    try:
        # analyzed_pdf_path, article_urls = detect_and_extract_articles(pdf_path, output_dir)
        extractor = ArticleExtractor(output_dir=output_dir)
        analyzed_pdf_path, article_urls = extractor.detect_and_extract_articles(pdf_path)
        print("Processing complete!")
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        exit(1)
