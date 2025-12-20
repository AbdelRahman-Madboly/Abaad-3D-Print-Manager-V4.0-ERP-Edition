"""
Cura Vision AI - OCR Module for Abaad 3D Print Manager v4.0
Extracts print time and weight from Cura slicer screenshots
"""
import re
from typing import Optional, Tuple, Dict
from io import BytesIO

# Check for required libraries
PILLOW_AVAILABLE = False
TESSERACT_AVAILABLE = False

try:
    from PIL import Image, ImageGrab
    PILLOW_AVAILABLE = True
except ImportError:
    pass

try:
    import pytesseract
    # Try to find Tesseract executable
    import shutil
    tesseract_path = shutil.which('tesseract')
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        TESSERACT_AVAILABLE = True
    else:
        # Try common Windows paths
        import os
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"D:\Program Files\Tesseract-OCR\tesseract.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                TESSERACT_AVAILABLE = True
                break
except ImportError:
    pass


class CuraVision:
    """
    AI-powered OCR for extracting print parameters from Cura screenshots.
    
    Usage:
        vision = CuraVision()
        result = vision.extract_from_clipboard()
        if result:
            print(f"Time: {result['time_minutes']} minutes")
            print(f"Weight: {result['weight_grams']} grams")
    """
    
    # Regex patterns for extracting data from Cura
    TIME_PATTERNS = [
        r'(\d+)\s*h\s*(\d+)\s*m',        # "4h 12m" or "4 h 12 m"
        r'(\d+)\s*hours?\s*(\d+)\s*min',  # "4 hours 12 min"
        r'(\d+):(\d+):(\d+)',              # "04:12:30" (h:m:s)
        r'(\d+)\s*h',                       # "4h" (hours only)
        r'(\d+)\s*m(?:in)?',               # "252m" or "252min" (minutes only)
    ]
    
    WEIGHT_PATTERNS = [
        r'(\d+(?:\.\d+)?)\s*g(?:ram)?s?',   # "123g" or "123.5 grams"
        r'(\d+(?:\.\d+)?)\s*(?:g|G)\b',     # "123 g" or "123G"
        r'Weight[:\s]+(\d+(?:\.\d+)?)',      # "Weight: 123" or "Weight 123.5"
        r'Material[:\s]+(\d+(?:\.\d+)?)',    # "Material: 123"
        r'Filament[:\s]+(\d+(?:\.\d+)?)',    # "Filament: 123"
    ]
    
    def __init__(self):
        self.last_error = None
        self.debug_text = ""  # Store OCR text for debugging
    
    @property
    def is_available(self) -> bool:
        """Check if OCR is available"""
        return PILLOW_AVAILABLE and TESSERACT_AVAILABLE
    
    def get_availability_status(self) -> Dict[str, bool]:
        """Get detailed availability status"""
        return {
            'pillow': PILLOW_AVAILABLE,
            'tesseract': TESSERACT_AVAILABLE,
            'ready': self.is_available
        }
    
    def extract_from_clipboard(self) -> Optional[Dict]:
        """
        Extract time and weight from clipboard image.
        
        Returns:
            Dict with 'time_minutes' and 'weight_grams' or None if failed
        """
        if not self.is_available:
            self.last_error = "OCR not available. Install Pillow and Tesseract."
            return None
        
        try:
            # Grab image from clipboard
            image = ImageGrab.grabclipboard()
            
            if image is None:
                self.last_error = "No image in clipboard. Copy a screenshot first."
                return None
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            return self._extract_from_image(image)
            
        except Exception as e:
            self.last_error = f"Error reading clipboard: {str(e)}"
            return None
    
    def extract_from_file(self, file_path: str) -> Optional[Dict]:
        """
        Extract time and weight from image file.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Dict with 'time_minutes' and 'weight_grams' or None if failed
        """
        if not self.is_available:
            self.last_error = "OCR not available"
            return None
        
        try:
            image = Image.open(file_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            return self._extract_from_image(image)
        except Exception as e:
            self.last_error = f"Error reading file: {str(e)}"
            return None
    
    def _extract_from_image(self, image: 'Image.Image') -> Optional[Dict]:
        """
        Internal method to extract data from PIL Image.
        """
        try:
            # Perform OCR
            text = pytesseract.image_to_string(image)
            self.debug_text = text  # Store for debugging
            
            # Extract time and weight
            time_minutes = self._extract_time(text)
            weight_grams = self._extract_weight(text)
            
            result = {
                'time_minutes': time_minutes,
                'weight_grams': weight_grams,
                'raw_text': text[:500]  # First 500 chars for debugging
            }
            
            if time_minutes is None and weight_grams is None:
                self.last_error = "Could not find time or weight in image"
                return None
            
            self.last_error = None
            return result
            
        except Exception as e:
            self.last_error = f"OCR error: {str(e)}"
            return None
    
    def _extract_time(self, text: str) -> Optional[int]:
        """Extract print time in minutes from text"""
        text = text.lower()
        
        for pattern in self.TIME_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # Handle different pattern matches
                if len(groups) == 3:  # h:m:s format
                    hours = int(groups[0])
                    minutes = int(groups[1])
                    return hours * 60 + minutes
                elif len(groups) == 2:  # hours and minutes
                    hours = int(groups[0])
                    minutes = int(groups[1])
                    return hours * 60 + minutes
                elif len(groups) == 1:
                    value = int(groups[0])
                    # Determine if hours or minutes based on pattern
                    if 'h' in pattern.lower():
                        return value * 60  # Hours
                    else:
                        return value  # Minutes
        
        return None
    
    def _extract_weight(self, text: str) -> Optional[float]:
        """Extract filament weight in grams from text"""
        for pattern in self.WEIGHT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    weight = float(match.group(1))
                    # Sanity check - typical prints are 1-2000g
                    if 0.1 <= weight <= 5000:
                        return weight
                except ValueError:
                    continue
        
        return None
    
    def preprocess_image(self, image: 'Image.Image') -> 'Image.Image':
        """
        Preprocess image for better OCR results.
        Can be used for difficult-to-read screenshots.
        """
        try:
            from PIL import ImageFilter, ImageEnhance
            
            # Convert to grayscale
            gray = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(gray)
            enhanced = enhancer.enhance(2.0)
            
            # Sharpen
            sharpened = enhanced.filter(ImageFilter.SHARPEN)
            
            return sharpened
        except:
            return image


# Singleton instance
_cura_vision = None

def get_cura_vision() -> CuraVision:
    """Get the CuraVision singleton instance"""
    global _cura_vision
    if _cura_vision is None:
        _cura_vision = CuraVision()
    return _cura_vision


def extract_from_cura_screenshot() -> Optional[Dict]:
    """
    Convenience function to extract data from clipboard.
    
    Returns:
        Dict with 'time_minutes' and 'weight_grams' or None
    """
    return get_cura_vision().extract_from_clipboard()


# Command-line testing
if __name__ == "__main__":
    print("=" * 50)
    print("Cura Vision AI - OCR Module")
    print("=" * 50)
    
    vision = CuraVision()
    status = vision.get_availability_status()
    
    print(f"\nPillow available: {'✓' if status['pillow'] else '✗'}")
    print(f"Tesseract available: {'✓' if status['tesseract'] else '✗'}")
    print(f"Ready: {'✓' if status['ready'] else '✗'}")
    
    if not status['ready']:
        print("\n⚠ To enable Cura Vision:")
        if not status['pillow']:
            print("  pip install Pillow")
        if not status['tesseract']:
            print("  Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")
            print("  Install and ensure it's in PATH")
    else:
        print("\n✓ Cura Vision is ready!")
        print("\nTest by:")
        print("1. Screenshot Cura slicer (after slicing)")
        print("2. Copy screenshot to clipboard")
        print("3. Run: result = extract_from_cura_screenshot()")
