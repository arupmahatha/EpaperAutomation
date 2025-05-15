# E-Paper Automation

This project is an advanced e-paper processing system that automates the extraction and analysis of articles from digital newspapers. It implements a sophisticated two-phase pipeline for processing PDF documents and extracting relevant information.

## Technical Overview

### Phase 1: Article Detection and Extraction
The first phase (`phase_1.py`) implements an intelligent article detection system using computer vision techniques:

1. **PDF Processing**:
   - Converts PDF pages to high-resolution images
   - Implements smart header detection and masking
   - Uses a hybrid approach combining multiple detection techniques

2. **Article Detection Techniques**:
   - Adaptive Thresholding: Identifies text regions using local contrast
   - Canny Edge Detection: Detects article boundaries
   - Morphological Operations: Refines article boundaries
   - Contour Analysis: Filters and validates detected regions

3. **Smart Filtering**:
   - Area-based filtering (min: 30,000px, max: 90% of page)
   - Perimeter validation (min: 500px)
   - Aspect ratio constraints (0.2 to 5.0)
   - Overlap detection and removal

4. **Article Extraction**:
   - Extracts individual articles as separate images
   - Maintains original layout and formatting
   - Uploads articles to a cloud storage system
   - Generates clickable links in the processed PDF

### Phase 2: Text Analysis and Translation
The second phase (`phase_2.py`) focuses on text extraction and translation:

1. **Image Processing**:
   - Handles PNG and JPG formats
   - Maintains image quality for optimal text recognition
   - Implements efficient batch processing

2. **Text Extraction**:
   - Uses Google's Gemini 2.0 Flash API for advanced OCR
   - Extracts text in multiple languages (primarily Telugu)
   - Structures output into headline, subheadline, and main text

3. **Translation Pipeline**:
   - Translates extracted text to English
   - Maintains formatting and structure
   - Handles missing sections gracefully

4. **Output Organization**:
   - Creates hierarchical output structure
   - Separates content by page and article
   - Generates individual text files for each component

## Project Structure

```
.
├── engine/                 # Core processing engine
│   ├── phase_1.py         # Article detection and extraction
│   └── phase_2.py         # Text analysis and translation
├── phase_1_output/        # Extracted article images
├── phase_2_output/        # Translated text content
├── requirements.txt       # Project dependencies
└── venv/                  # Python virtual environment
```

## Prerequisites

- Python 3.x
- Virtual environment (recommended)
- Google Gemini API key (for text extraction)

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd EpaperAutomation
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API key:
```
GEMINI_API_KEY=your_api_key_here
```

## Dependencies

The project relies on the following main packages:
- pdfplumber (0.10.3) - PDF text extraction
- PyMuPDF (1.23.8) - PDF processing
- Pillow (10.2.0) - Image processing
- OpenCV (4.9.0.80) - Computer vision tasks
- NumPy (1.26.4) - Numerical operations
- tqdm (4.66.2) - Progress bars
- python-dotenv (1.0.1) - Environment variable management
- requests (2.31.0) - HTTP requests

## Usage

1. Place your PDF files in the root directory
2. Run Phase 1 to extract articles:
```bash
python engine/phase_1.py
```
3. Run Phase 2 to process extracted articles:
```bash
python engine/phase_2.py
```

## Output Structure

### Phase 1 Output
```
phase_1_output/
└── [pdf_name]/
    ├── page1/
    │   ├── article1.png
    │   ├── article2.png
    │   └── ...
    ├── page2/
    │   └── ...
    └── [pdf_name]_analysed.pdf
```

### Phase 2 Output
```
phase_2_output/
└── [pdf_name]/
    ├── page1/
    │   ├── article1/
    │   │   ├── headline.txt
    │   │   ├── subheadline.txt
    │   │   └── main_text.txt
    │   └── ...
    └── ...
```