"""
Translation module for the E-Paper Automation project.
"""

import os
import json
from typing import Dict, List, Optional, Union
import requests
from langdetect import detect
from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class Translator:
    """
    Class for translating text between languages.
    """
    
    def __init__(self, api_key: str = None, source_language: str = None, target_languages: List[str] = None):
        """
        Initialize the Translator.
        
        Args:
            api_key (str, optional): API key for the translation service.
                                    Defaults to None (use settings.TRANSLATION["api_key"]).
            source_language (str, optional): Source language code.
                                           Defaults to None (use settings.TRANSLATION["source_language"]).
            target_languages (List[str], optional): List of target language codes.
                                                  Defaults to None (use settings.TRANSLATION["target_languages"]).
        """
        self.api_key = api_key or settings.TRANSLATION["api_key"]
        self.source_language = source_language or settings.TRANSLATION["source_language"]
        self.target_languages = target_languages or settings.TRANSLATION["target_languages"]
        
    def detect_language(self, text: str) -> str:
        """
        Detect the language of a text.
        
        Args:
            text (str): Text to detect language for.
            
        Returns:
            str: Detected language code.
        """
        try:
            return detect(text)
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return self.source_language
    
    def translate_text(self, text: str, target_language: str, source_language: str = None) -> str:
        """
        Translate text to a target language.
        
        Args:
            text (str): Text to translate.
            target_language (str): Target language code.
            source_language (str, optional): Source language code.
                                           Defaults to None (use self.source_language).
            
        Returns:
            str: Translated text.
        """
        if not text.strip():
            return text
            
        if source_language is None:
            source_language = self.source_language
            
        # If source and target languages are the same, return the original text
        if source_language == target_language:
            return text
            
        try:
            # Use Google Cloud Translation API
            url = "https://translation.googleapis.com/language/translate/v2"
            params = {
                "q": text,
                "target": target_language,
                "source": source_language,
                "format": "text",
                "key": self.api_key
            }
            
            response = requests.post(url, params=params)
            response.raise_for_status()
            
            result = response.json()
            translated_text = result["data"]["translations"][0]["translatedText"]
            
            logger.info(f"Translated text from {source_language} to {target_language}")
            return translated_text
            
        except Exception as e:
            logger.error(f"Error translating text: {e}")
            return text
    
    def translate_to_all_targets(self, text: str, source_language: str = None) -> Dict[str, str]:
        """
        Translate text to all target languages.
        
        Args:
            text (str): Text to translate.
            source_language (str, optional): Source language code.
                                           Defaults to None (use self.source_language).
            
        Returns:
            Dict[str, str]: Dictionary mapping language codes to translated texts.
        """
        if source_language is None:
            source_language = self.source_language
            
        result = {source_language: text}
        
        for target_language in self.target_languages:
            if target_language != source_language:
                translated_text = self.translate_text(text, target_language, source_language)
                result[target_language] = translated_text
                
        return result
    
    def translate_batch(self, texts: List[str], target_language: str, source_language: str = None) -> List[str]:
        """
        Translate a batch of texts to a target language.
        
        Args:
            texts (List[str]): List of texts to translate.
            target_language (str): Target language code.
            source_language (str, optional): Source language code.
                                           Defaults to None (use self.source_language).
            
        Returns:
            List[str]: List of translated texts.
        """
        if source_language is None:
            source_language = self.source_language
            
        # If source and target languages are the same, return the original texts
        if source_language == target_language:
            return texts
            
        translated_texts = []
        
        try:
            # Use Google Cloud Translation API for batch translation
            url = "https://translation.googleapis.com/language/translate/v2"
            params = {
                "target": target_language,
                "source": source_language,
                "format": "text",
                "key": self.api_key
            }
            
            # Split into batches of 100 texts (API limit)
            batch_size = 100
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                
                # Skip empty texts
                batch = [text for text in batch if text.strip()]
                
                if not batch:
                    continue
                
                # Create request data
                data = {"q": batch}
                
                response = requests.post(url, params=params, json=data)
                response.raise_for_status()
                
                result = response.json()
                batch_translations = [t["translatedText"] for t in result["data"]["translations"]]
                translated_texts.extend(batch_translations)
                
            logger.info(f"Translated {len(translated_texts)} texts from {source_language} to {target_language}")
            return translated_texts
            
        except Exception as e:
            logger.error(f"Error translating batch: {e}")
            return texts
    
    def translate_regions(self, regions: List, target_language: str, source_language: str = None) -> List:
        """
        Translate text in regions to a target language.
        
        Args:
            regions (List): List of Region objects with text attributes.
            target_language (str): Target language code.
            source_language (str, optional): Source language code.
                                           Defaults to None (use self.source_language).
            
        Returns:
            List: List of Region objects with translated text.
        """
        if source_language is None:
            source_language = self.source_language
            
        # Extract texts from regions
        texts = [region.text for region in regions if hasattr(region, "text") and region.text.strip()]
        
        # Translate texts
        translated_texts = self.translate_batch(texts, target_language, source_language)
        
        # Update regions with translated texts
        text_index = 0
        translated_regions = []
        
        for region in regions:
            if hasattr(region, "text") and region.text.strip():
                # Create a copy of the region
                translated_region = region
                
                # Update the text with the translated text
                if text_index < len(translated_texts):
                    translated_region.text = translated_texts[text_index]
                    text_index += 1
                
                translated_regions.append(translated_region)
            else:
                translated_regions.append(region)
                
        logger.info(f"Translated {text_index} regions from {source_language} to {target_language}")
        return translated_regions 