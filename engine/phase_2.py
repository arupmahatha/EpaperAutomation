import os
import requests
import json
from PIL import Image
import io
from dotenv import load_dotenv
import base64
import glob

# Load environment variables from .env file
load_dotenv()

class EpaperProcessor:
    def __init__(self, output_dir="phase_2_output"):
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize the text extractor
        self.text_extractor = ImageTextExtractor(output_dir)
        
    def process_folder(self, input_folder):
        """
        Process all images in the input folder to extract and translate text.
        
        Args:
            input_folder (str): Path to the input folder containing article images
        """
        print(f"\nProcessing images from folder: {input_folder}")
        self.text_extractor.process_folder(input_folder)
        print(f"\nProcessing complete! Extracted text saved to: {self.output_dir}")

class ImageTextExtractor:
    def __init__(self, output_dir="phase_2_output"):
        # Get API key from environment variable
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
    def extract_text(self, image_path: str) -> dict:
        """
        Extract and translate text from a PNG image.
        
        Args:
            image_path (str): Path to the PNG image file
            
        Returns:
            dict: Dictionary containing headline, subheadline, and main text
        """
        try:
            # Verify file exists and is a PNG
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            if not image_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                raise ValueError("Only PNG and JPG images are supported")
            
            # Open and process the image
            with Image.open(image_path) as img:
                # Convert image to bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                # Convert image to base64
                image_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
                
                # Prepare the prompt
                prompt = """
                Analyze the text in this image (which is in Telugu). 
                Translate the text into English and format the response as a JSON object with the keys: headline, subheadline, and main_text. 
                If a section is not present, set its value to null. 
                Ensure all text in the JSON object is in English.
                """
                
                # Prepare the request payload
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": image_base64
                                }
                            }
                        ]
                    }]
                }
                
                # Make the API request
                headers = {'Content-Type': 'application/json'}
                response = requests.post(self.api_url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    raise Exception(f"API request failed with status code {response.status_code}: {response.text}")
                
                # Parse the response
                response_data = response.json()
                
                # Extract the text from the response
                try:
                    text_response = response_data['candidates'][0]['content']['parts'][0]['text']
                    
                    # Clean the response text (remove markdown code blocks if present)
                    text_response = text_response.replace('```json', '').replace('```', '').strip()
                    
                    # Try to parse as JSON
                    try:
                        result = json.loads(text_response)
                        return result
                    except json.JSONDecodeError:
                        # If not JSON, return as main text
                        return {
                            "headline": None,
                            "subheadline": None,
                            "main_text": text_response.strip()
                        }
                except (KeyError, IndexError) as e:
                    raise Exception(f"Failed to parse API response: {str(e)}")
                    
        except Exception as e:
            print(f"Error processing image: {str(e)}")
            return {
                "headline": None,
                "subheadline": None,
                "main_text": None,
                "error": str(e)
            }
    
    def process_folder(self, input_folder):
        """
        Process all images in a folder and its subfolders in order.
        
        Args:
            input_folder (str): Path to the input folder containing images
        """
        # Get the base name of the input folder
        base_folder_name = os.path.basename(input_folder)
        
        # Create corresponding directory in output
        output_base_dir = os.path.join(self.output_dir, base_folder_name)
        os.makedirs(output_base_dir, exist_ok=True)
        
        # Get all page directories and sort them
        page_dirs = sorted([d for d in os.listdir(input_folder) 
                          if os.path.isdir(os.path.join(input_folder, d)) and d.startswith('page')],
                          key=lambda x: int(x[4:]))  # Sort by page number
        
        for page_dir in page_dirs:
            print(f"\nProcessing {page_dir}...")
            page_path = os.path.join(input_folder, page_dir)
            
            # Create corresponding output directory
            page_output_dir = os.path.join(output_base_dir, page_dir)
            os.makedirs(page_output_dir, exist_ok=True)
            
            # Get all article images and sort them
            article_images = sorted([f for f in os.listdir(page_path) 
                                  if f.lower().endswith(('.png', '.jpg', '.jpeg')) and f.startswith('article')],
                                  key=lambda x: int(x[7:-4]))  # Sort by article number
            
            for article_image in article_images:
                # Get full path of input image
                input_image_path = os.path.join(page_path, article_image)
                
                # Create article directory in output
                article_name = os.path.splitext(article_image)[0]
                article_output_dir = os.path.join(page_output_dir, article_name)
                os.makedirs(article_output_dir, exist_ok=True)
                
                print(f"Processing {page_dir}/{article_image}...")
                
                # Extract text from the image
                result = self.extract_text(input_image_path)
                
                # Save the extracted text to separate files
                if result.get('headline'):
                    with open(os.path.join(article_output_dir, 'headline.txt'), 'w', encoding='utf-8') as f:
                        f.write(result['headline'])
                
                if result.get('subheadline'):
                    with open(os.path.join(article_output_dir, 'subheadline.txt'), 'w', encoding='utf-8') as f:
                        f.write(result['subheadline'])
                
                if result.get('main_text'):
                    with open(os.path.join(article_output_dir, 'main_text.txt'), 'w', encoding='utf-8') as f:
                        f.write(result['main_text'])
                
                print(f"Completed processing {page_dir}/{article_image}")

# Example usage:
if __name__ == "__main__":
    # Specify your input folder path here
    input_folder = "/Users/arup/Documents/EpaperAutomation/phase_1_output/sample"  # Change this to your desired folder path
    
    extractor = ImageTextExtractor()
    extractor.process_folder(input_folder) 