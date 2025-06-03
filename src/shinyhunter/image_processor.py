import cv2
import os
from typing import Tuple
from config import ConfigManager

class ImageProcessor:
    def __init__(self):
        self.config = ConfigManager().get_config()
    
    def is_on_encounter_screen(self, screenshot_path: str) -> bool:
        """Verify we're on the encounter screen before checking for shiny."""
        if not os.path.exists(screenshot_path):
            return False
            
        # Define template image that should appear on encounter screen
        encounter_template_path = './images/encounter_screen_template.png'
        if not os.path.exists(encounter_template_path):
            #TODO: Log warning about missing template 
            return True  # Skip validation if template doesn't exist
            
        screenshot = cv2.imread(screenshot_path)
        template = cv2.imread(encounter_template_path)
        
        if screenshot is None or template is None:
            return False
            
        # Template matching to find UI elements specific to encounter screen
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        
        return max_val > 0.8  # Adjust threshold as needed
    
    def is_shiny_found(self, ref_img_path: str, screenshot_path: str) -> bool:
        """Check if a shiny Pokemon is found by comparing reference image to screenshot of current encounter."""
        if not os.path.exists(ref_img_path) or not os.path.exists(screenshot_path):
            return False
            
        # First validate we're on the correct screen
        if not self.is_on_encounter_screen(screenshot_path):
            return False
            
        correlation = self.get_correlation(ref_img_path, screenshot_path)
        print(f"Correlation: {correlation}")
        return abs(self.config.correlation_threshold - correlation) > self.config.correlation_tolerance
    
    def get_correlation(self, ref_img_path: str, screenshot_path: str) -> float:
        """Calculate correlation between reference and screenshot images."""
        ref_image = cv2.imread(ref_img_path)
        screenshot = cv2.imread(screenshot_path)
        
        if ref_image is None or screenshot is None:
            return 0.0
        
        # Convert to HSV color space
        reference_hsv = cv2.cvtColor(ref_image, cv2.COLOR_BGR2HSV)
        screenshot_hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)
        
        # Calculate histograms
        reference_hist = cv2.calcHist([reference_hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])
        screenshot_hist = cv2.calcHist([screenshot_hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])
        
        # Normalize histograms
        cv2.normalize(reference_hist, reference_hist, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(screenshot_hist, screenshot_hist, 0, 1, cv2.NORM_MINMAX)
        
        # Compare histograms
        return cv2.compareHist(reference_hist, screenshot_hist, cv2.HISTCMP_CORREL)