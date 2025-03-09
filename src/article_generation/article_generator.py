"""
Article generation module for the E-Paper Automation project.
"""

import os
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from src.config import settings
from src.utils.logger import setup_logger
from src.utils.file_utils import ensure_directory_exists, get_output_path

logger = setup_logger(__name__)

class ArticleGenerator:
    """
    Class for generating formatted articles from extracted and translated content.
    """
    
    def __init__(self, template_dir: str = None, output_format: str = None):
        """
        Initialize the ArticleGenerator.
        
        Args:
            template_dir (str, optional): Directory containing article templates.
                                        Defaults to None (use settings.ARTICLE_GENERATION["template_dir"]).
            output_format (str, optional): Output format for generated articles.
                                         Defaults to None (use settings.ARTICLE_GENERATION["output_format"]).
        """
        self.template_dir = template_dir or settings.ARTICLE_GENERATION["template_dir"]
        self.output_format = output_format or settings.ARTICLE_GENERATION["output_format"]
        
        # Create template directory if it doesn't exist
        ensure_directory_exists(self.template_dir)
        
        # Create default templates if they don't exist
        self._create_default_templates()
        
        # Set up Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True
        )
    
    def _create_default_templates(self):
        """
        Create default templates if they don't exist.
        """
        # HTML template
        html_template_path = os.path.join(self.template_dir, "article.html")
        if not os.path.exists(html_template_path):
            html_template = """<!DOCTYPE html>
<html lang="{{ language }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
        }
        .article-header {
            margin-bottom: 20px;
        }
        .article-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .article-meta {
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        }
        .article-content {
            font-size: 16px;
            margin-bottom: 20px;
        }
        .article-image {
            max-width: 100%;
            height: auto;
            margin-bottom: 20px;
        }
        .article-footer {
            font-size: 14px;
            color: #666;
            margin-top: 20px;
            padding-top: 10px;
            border-top: 1px solid #eee;
        }
        .language-selector {
            margin-bottom: 20px;
        }
        .language-selector select {
            padding: 5px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="article-container">
        {% if available_languages %}
        <div class="language-selector">
            <label for="language-select">Language:</label>
            <select id="language-select" onchange="changeLanguage(this.value)">
                {% for lang_code, lang_name in available_languages.items() %}
                <option value="{{ lang_code }}" {% if lang_code == language %}selected{% endif %}>{{ lang_name }}</option>
                {% endfor %}
            </select>
        </div>
        {% endif %}
        
        <div class="article-header">
            <div class="article-title">{{ title }}</div>
            <div class="article-meta">
                {% if date %}Published: {{ date }}{% endif %}
                {% if author %} | Author: {{ author }}{% endif %}
            </div>
        </div>
        
        {% if image_url %}
        <img class="article-image" src="{{ image_url }}" alt="{{ title }}">
        {% endif %}
        
        <div class="article-content">
            {{ content|safe }}
        </div>
        
        <div class="article-footer">
            <p>Source: {{ source }}</p>
        </div>
    </div>
    
    {% if available_languages %}
    <script>
        function changeLanguage(langCode) {
            // Replace the current URL with the URL for the selected language
            window.location.href = window.location.pathname.replace(/\/[^\/]+\.html$/, '/' + '{{ article_id }}' + '_' + langCode + '.html');
        }
    </script>
    {% endif %}
</body>
</html>"""
            
            with open(html_template_path, "w") as f:
                f.write(html_template)
                
            logger.info(f"Created default HTML template at {html_template_path}")
        
        # JSON template
        json_template_path = os.path.join(self.template_dir, "article.json")
        if not os.path.exists(json_template_path):
            json_template = """{
    "article_id": "{{ article_id }}",
    "title": "{{ title }}",
    "content": {{ content|tojson }},
    "date": "{{ date }}",
    "author": "{{ author }}",
    "source": "{{ source }}",
    "language": "{{ language }}",
    "image_url": "{{ image_url }}",
    "available_languages": {{ available_languages|tojson }}
}"""
            
            with open(json_template_path, "w") as f:
                f.write(json_template)
                
            logger.info(f"Created default JSON template at {json_template_path}")
    
    def generate_article(self, article_data: Dict[str, Any], output_dir: str = None) -> str:
        """
        Generate a formatted article from article data.
        
        Args:
            article_data (Dict[str, Any]): Article data.
            output_dir (str, optional): Directory to save the generated article.
                                      Defaults to None (use settings.OUTPUT_DIR).
            
        Returns:
            str: Path to the generated article file.
        """
        if output_dir is None:
            output_dir = settings.OUTPUT_DIR
            
        ensure_directory_exists(output_dir)
        
        # Get article ID
        article_id = article_data.get("article_id", f"article_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        
        # Get language
        language = article_data.get("language", "en")
        
        # Get template
        template_name = f"article.{self.output_format}"
        template = self.env.get_template(template_name)
        
        # Render template
        rendered_article = template.render(**article_data)
        
        # Save to file
        filename = f"{article_id}_{language}.{self.output_format}"
        output_path = os.path.join(output_dir, filename)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered_article)
            
        logger.info(f"Generated article at {output_path}")
        return output_path
    
    def generate_articles_from_regions(self, regions: List, pdf_path: str, language: str = "en", output_dir: str = None) -> List[str]:
        """
        Generate articles from regions.
        
        Args:
            regions (List): List of Region objects with text attributes.
            pdf_path (str): Path to the original PDF file.
            language (str, optional): Language of the articles. Defaults to "en".
            output_dir (str, optional): Directory to save the generated articles.
                                      Defaults to None (use settings.OUTPUT_DIR).
            
        Returns:
            List[str]: List of paths to the generated article files.
        """
        if output_dir is None:
            output_dir = settings.OUTPUT_DIR
            
        ensure_directory_exists(output_dir)
        
        # Get PDF filename without extension
        pdf_filename = os.path.basename(pdf_path)
        pdf_name = os.path.splitext(pdf_filename)[0]
        
        # Generate articles
        article_paths = []
        
        for i, region in enumerate(regions):
            if hasattr(region, "text") and region.text.strip():
                # Extract title from the first line of text
                lines = region.text.strip().split("\n")
                title = lines[0] if lines else f"Article {i+1}"
                
                # Join the rest of the lines as content
                content = "\n".join(lines[1:]) if len(lines) > 1 else ""
                
                # Create article data
                article_data = {
                    "article_id": f"{pdf_name}_article_{i+1}",
                    "title": title,
                    "content": content,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "author": "E-Paper Automation",
                    "source": pdf_filename,
                    "language": language,
                    "image_url": "",
                    "available_languages": {"en": "English", "te": "Telugu", "hi": "Hindi", "ta": "Tamil"}
                }
                
                # Generate article
                article_path = self.generate_article(article_data, output_dir)
                article_paths.append(article_path)
                
        logger.info(f"Generated {len(article_paths)} articles from {pdf_path}")
        return article_paths
    
    def generate_multilingual_articles(self, regions_by_language: Dict[str, List], pdf_path: str, output_dir: str = None) -> Dict[str, List[str]]:
        """
        Generate multilingual articles from regions.
        
        Args:
            regions_by_language (Dict[str, List]): Dictionary mapping language codes to lists of Region objects.
            pdf_path (str): Path to the original PDF file.
            output_dir (str, optional): Directory to save the generated articles.
                                      Defaults to None (use settings.OUTPUT_DIR).
            
        Returns:
            Dict[str, List[str]]: Dictionary mapping language codes to lists of paths to the generated article files.
        """
        if output_dir is None:
            output_dir = settings.OUTPUT_DIR
            
        ensure_directory_exists(output_dir)
        
        # Generate articles for each language
        article_paths_by_language = {}
        
        for language, regions in regions_by_language.items():
            article_paths = self.generate_articles_from_regions(regions, pdf_path, language, output_dir)
            article_paths_by_language[language] = article_paths
            
        return article_paths_by_language 