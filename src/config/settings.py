"""
Configuration settings for the E-Paper Automation project.
"""

import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Directory for sample PDFs
PDF_DIR = os.path.join(BASE_DIR, "Sample_PDFs")

# Directory for output files
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Directory for temporary files
TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# Region detection settings
REGION_DETECTION = {
    "min_area": 1000,  # Minimum area of a region to be considered an article
    "margin": 10,      # Margin around detected regions
    "color_threshold": 30,  # Threshold for color-based detection
}

# Translation settings
TRANSLATION = {
    "source_language": "te",  # Telugu
    "target_languages": ["en", "hi", "ta"],  # English, Hindi, Tamil
    "api_key": os.environ.get("TRANSLATION_API_KEY", ""),
}

# Article generation settings
ARTICLE_GENERATION = {
    "template_dir": os.path.join(BASE_DIR, "src", "article_generation", "templates"),
    "output_format": "html",
}

# Logging settings
LOGGING = {
    "level": "INFO",
    "file": os.path.join(BASE_DIR, "logs", "epaper_automation.log"),
}
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True) 