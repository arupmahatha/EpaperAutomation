# E-Paper Automation

A modular Python application for automating the process of extracting, translating, and reformatting articles from e-paper PDFs.

## Overview

This project automates the following tasks:

1. **Region Detection**: Automatically detects article regions in e-paper PDFs using computer vision techniques.
2. **Text Extraction**: Extracts text from detected regions using OCR.
3. **Translation**: Translates extracted text from Telugu to multiple languages.
4. **Article Generation**: Generates formatted articles from the extracted and translated content.

## Features

- **PDF Processing**: Extract images and text from PDF files.
- **Region Detection**: Detect article regions using various methods:
  - Adaptive thresholding and contour detection
  - Color-based detection
  - Layout analysis
- **Translation**: Translate text between languages using the Google Cloud Translation API.
- **Article Generation**: Generate formatted articles in HTML or JSON format.
- **Visualization**: Visualize detected regions for debugging and verification.

## Requirements

- Python 3.8 or higher
- Tesseract OCR
- Poppler (for PDF processing)
- Google Cloud Translation API key (for translation)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/epaper-automation.git
   cd epaper-automation
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Install Tesseract OCR:
   - On Ubuntu: `sudo apt-get install tesseract-ocr tesseract-ocr-tel`
   - On macOS: `brew install tesseract tesseract-lang`
   - On Windows: Download and install from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

5. Install Poppler:
   - On Ubuntu: `sudo apt-get install poppler-utils`
   - On macOS: `brew install poppler`
   - On Windows: Download and install from [poppler-windows](http://blog.alivate.com.au/poppler-windows/)

## Usage

### Command-line Interface

Process a single PDF file:
```
python -m src.main --pdf path/to/your/file.pdf --output path/to/output/dir --visualize
```

Process all PDF files in a directory:
```
python -m src.main --dir path/to/pdf/directory --output path/to/output/dir
```

### API Usage

```python
from src.main import EpaperAutomation

# Create an instance
automation = EpaperAutomation()

# Process a single PDF
result = automation.process_pdf("path/to/your/file.pdf", output_dir="path/to/output/dir", visualize=True)

# Process all PDFs in a directory
results = automation.process_directory("path/to/pdf/directory", output_dir="path/to/output/dir")
```

## Configuration

Configuration settings are stored in `src/config/settings.py`. You can modify these settings to customize the behavior of the application.

### Translation API Key

To use the translation functionality, you need to set up a Google Cloud Translation API key:

1. Create a Google Cloud account and project
2. Enable the Cloud Translation API
3. Create an API key
4. Set the API key as an environment variable:
   ```
   export TRANSLATION_API_KEY="your-api-key"
   ```

## Project Structure

```
epaper-automation/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   └── file_utils.py
│   ├── pdf_processing/
│   │   ├── __init__.py
│   │   └── pdf_extractor.py
│   ├── region_detection/
│   │   ├── __init__.py
│   │   └── detector.py
│   ├── translation/
│   │   ├── __init__.py
│   │   └── translator.py
│   └── article_generation/
│       ├── __init__.py
│       └── article_generator.py
├── Sample_PDFs/
│   └── *.pdf
├── output/
├── logs/
├── requirements.txt
└── README.md
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [OpenCV](https://opencv.org/) for computer vision functionality
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for text extraction
- [pdf2image](https://github.com/Belval/pdf2image) for PDF processing
- [Google Cloud Translation API](https://cloud.google.com/translate) for translation 