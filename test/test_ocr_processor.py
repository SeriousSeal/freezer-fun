import unittest
from ocr_processor import process_image
import os

class TestOCRProcessor(unittest.TestCase):
    def setUp(self):
        # Create a test images directory if it doesn't exist
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.test_images_dir = os.path.join(self.test_dir, "test_images")
        self.test_image_path = os.path.join(self.test_images_dir, "test.jpg")
    
        # Verify test image exists
        self.assertTrue(os.path.exists(self.test_image_path), 
                   f"Test image not found at {self.test_image_path}")

        os.environ['TESSDATA_PREFIX'] = '/usr/share/tesseract-ocr/5/tessdata/'

    def test_process_image(self):
        # Test with a known image containing text
        test_image_path = os.path.join(self.test_images_dir, "test.jpg")
        
        # Create a test image if needed
        # You should add a real test image file with known text
        
        result = process_image(test_image_path)

        print("\nDetailed OCR Analysis:")
        print("=====================")
        print(f"Total detected elements: {len(result['magnets'])}")
    
        # Group by text size
        size_groups = {'small': [], 'medium': [], 'large': []}
        for magnet in result['magnets']:
            h = magnet['position']['height']
            if h < 20:
                size_groups['small'].append(magnet)
            elif h < 40:
                size_groups['medium'].append(magnet)
            else:
                size_groups['large'].append(magnet)
    
        # Print results by size
        for size, magnets in size_groups.items():
            print(f"\n{size.capitalize()} Text ({len(magnets)} elements):")
            print("-" * 40)
            for m in magnets:
                print(f"Text: '{m['text']}' (height: {m['position']['height']}px)")
 
        
        # Assertions
        self.assertIn("magnets", result)
        self.assertIsInstance(result["magnets"], list)
        
        if result["magnets"]:
            magnet = result["magnets"][0]
            self.assertIn("text", magnet)
            self.assertIn("position", magnet)
            self.assertIn("x", magnet["position"])
            self.assertIn("y", magnet["position"])
            self.assertIn("width", magnet["position"])
            self.assertIn("height", magnet["position"])

if __name__ == '__main__':
    unittest.main()