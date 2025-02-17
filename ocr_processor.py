from PIL import Image
import pytesseract
import cv2
import os
from config import Config

def process_image(image_path: str) -> dict:
    try:
        # Read image using cv2
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image at {image_path}")
            
        # Convert to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Optional: Resize image to make text bigger
        height, width = image.shape[:2]
        scale_factor = 2.0  # Double the size
        image = cv2.resize(image, (int(width * scale_factor), int(height * scale_factor)))
        
        # Optional: Image preprocessing for better text recognition
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        # Apply thresholding to get black and white image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # OCR mit Tesseract (deutsche Sprache)
        custom_config = r'--oem 3 --psm 6'  # PSM 6 assumes uniform text block
        data = pytesseract.image_to_data(
            binary,  # Use preprocessed image
            lang="deu",
            output_type=pytesseract.Output.DICT,
            config=custom_config
        )
        
        # Extrahiere Wörter + Bounding Boxes
        magnets = []
        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            if text:
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                magnets.append({
                    "text": text,
                    "position": {"x": x, "y": y, "width": w, "height": h}
                })
        
        return {"magnets": magnets}
    except Exception as e:
        raise Exception(f"Error processing image: {str(e)}")