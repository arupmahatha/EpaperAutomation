"""
Region detection module for the E-Paper Automation project.
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class Region:
    """
    Class representing a detected region in an image.
    """
    id: int
    x: int
    y: int
    width: int
    height: int
    contour: np.ndarray
    text: str = ""
    
    @property
    def area(self) -> int:
        """
        Calculate the area of the region.
        
        Returns:
            int: Area of the region.
        """
        return self.width * self.height
    
    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """
        Get the bounding box of the region.
        
        Returns:
            Tuple[int, int, int, int]: Bounding box as (x, y, width, height).
        """
        return (self.x, self.y, self.width, self.height)
    
    @property
    def center(self) -> Tuple[int, int]:
        """
        Get the center of the region.
        
        Returns:
            Tuple[int, int]: Center coordinates as (x, y).
        """
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the region to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the region.
        """
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "area": self.area,
            "center": self.center,
            "text": self.text
        }
    
    def contains_point(self, point: Tuple[int, int]) -> bool:
        """
        Check if the region contains a point.
        
        Args:
            point (Tuple[int, int]): Point coordinates as (x, y).
            
        Returns:
            bool: True if the region contains the point, False otherwise.
        """
        x, y = point
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)


class RegionDetector:
    """
    Class for detecting article regions in images.
    """
    
    def __init__(self, min_area: int = None, margin: int = None):
        """
        Initialize the RegionDetector.
        
        Args:
            min_area (int, optional): Minimum area of a region to be considered an article.
                                     Defaults to None (use settings.REGION_DETECTION["min_area"]).
            margin (int, optional): Margin around detected regions.
                                   Defaults to None (use settings.REGION_DETECTION["margin"]).
        """
        self.min_area = min_area or settings.REGION_DETECTION["min_area"]
        self.margin = margin or settings.REGION_DETECTION["margin"]
        self.regions = []
        
    def detect_regions(self, image: np.ndarray) -> List[Region]:
        """
        Detect article regions in an image.
        
        Args:
            image (np.ndarray): Image as a numpy array.
            
        Returns:
            List[Region]: List of detected regions.
        """
        # Convert to grayscale if the image is in color
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area and create Region objects
        self.regions = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area >= self.min_area:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Add margin to the region
                x = max(0, x - self.margin)
                y = max(0, y - self.margin)
                w = min(image.shape[1] - x, w + 2 * self.margin)
                h = min(image.shape[0] - y, h + 2 * self.margin)
                
                region = Region(id=i, x=x, y=y, width=w, height=h, contour=contour)
                self.regions.append(region)
        
        logger.info(f"Detected {len(self.regions)} regions")
        return self.regions
    
    def detect_regions_by_color(self, image: np.ndarray, color_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]] = None) -> List[Region]:
        """
        Detect article regions in an image based on color.
        
        Args:
            image (np.ndarray): Image as a numpy array.
            color_range (Tuple[Tuple[int, int, int], Tuple[int, int, int]], optional): 
                Color range as (lower_bound, upper_bound) in HSV format.
                Defaults to None (use a predefined range).
            
        Returns:
            List[Region]: List of detected regions.
        """
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if color_range is None:
            # Default color range (light blue)
            lower_bound = np.array([90, 50, 50])
            upper_bound = np.array([130, 255, 255])
        else:
            lower_bound = np.array(color_range[0])
            upper_bound = np.array(color_range[1])
        
        # Create a mask for the specified color range
        mask = cv2.inRange(hsv, lower_bound, upper_bound)
        
        # Find contours in the mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area and create Region objects
        self.regions = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area >= self.min_area:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Add margin to the region
                x = max(0, x - self.margin)
                y = max(0, y - self.margin)
                w = min(image.shape[1] - x, w + 2 * self.margin)
                h = min(image.shape[0] - y, h + 2 * self.margin)
                
                region = Region(id=i, x=x, y=y, width=w, height=h, contour=contour)
                self.regions.append(region)
        
        logger.info(f"Detected {len(self.regions)} regions by color")
        return self.regions
    
    def detect_regions_by_layout(self, image: np.ndarray) -> List[Region]:
        """
        Detect article regions in an image based on layout analysis.
        
        Args:
            image (np.ndarray): Image as a numpy array.
            
        Returns:
            List[Region]: List of detected regions.
        """
        # Convert to grayscale if the image is in color
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply Canny edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Dilate the edges to connect nearby edges
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area and create Region objects
        self.regions = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area >= self.min_area:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Add margin to the region
                x = max(0, x - self.margin)
                y = max(0, y - self.margin)
                w = min(image.shape[1] - x, w + 2 * self.margin)
                h = min(image.shape[0] - y, h + 2 * self.margin)
                
                region = Region(id=i, x=x, y=y, width=w, height=h, contour=contour)
                self.regions.append(region)
        
        logger.info(f"Detected {len(self.regions)} regions by layout analysis")
        return self.regions
    
    def extract_region_images(self, image: np.ndarray) -> Dict[int, np.ndarray]:
        """
        Extract images of detected regions.
        
        Args:
            image (np.ndarray): Original image as a numpy array.
            
        Returns:
            Dict[int, np.ndarray]: Dictionary mapping region IDs to region images.
        """
        if not self.regions:
            logger.warning("No regions detected. Call detect_regions() first.")
            return {}
        
        region_images = {}
        for region in self.regions:
            x, y, w, h = region.bbox
            region_image = image[y:y+h, x:x+w]
            region_images[region.id] = region_image
        
        return region_images
    
    def visualize_regions(self, image: np.ndarray, color: Tuple[int, int, int] = (0, 255, 0), thickness: int = 2) -> np.ndarray:
        """
        Visualize detected regions on an image.
        
        Args:
            image (np.ndarray): Original image as a numpy array.
            color (Tuple[int, int, int], optional): Color for region boundaries. Defaults to (0, 255, 0) (green).
            thickness (int, optional): Thickness of region boundaries. Defaults to 2.
            
        Returns:
            np.ndarray: Image with visualized regions.
        """
        if not self.regions:
            logger.warning("No regions detected. Call detect_regions() first.")
            return image.copy()
        
        # Create a copy of the image to draw on
        vis_image = image.copy()
        
        # Draw regions
        for region in self.regions:
            x, y, w, h = region.bbox
            cv2.rectangle(vis_image, (x, y), (x + w, y + h), color, thickness)
            cv2.putText(vis_image, f"ID: {region.id}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return vis_image 