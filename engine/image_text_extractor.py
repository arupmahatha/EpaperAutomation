import os
import requests
import json
from PIL import Image
import io
from dotenv import load_dotenv
import base64

# Load environment variables from .env file
load_dotenv()

class ImageTextExtractor:
    def __init__(self):
        # Get API key from environment variable
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        
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
            
            if not image_path.lower().endswith('.png'):
                raise ValueError("Only PNG images are supported")
            
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
                Analyze this image (text is in Telugu) and translate to English.
                Please translate the following to English and provide:
                1. Headline (if present)
                2. Subheadline (if present)
                3. Main text content
                
                IMPORTANT: All text must be in English.
                
                Format the response as a JSON object with these keys:
                - headline
                - subheadline
                - main_text
                
                If any section is not present, set its value to null.
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

# Example usage:
if __name__ == "__main__":
    extractor = ImageTextExtractor()
    result = extractor.extract_text("/Users/arup/Documents/EpaperAutomation/extracted_articles/Sample/page1/article3.png")
    print(json.dumps(result, indent=2, ensure_ascii=False)) 