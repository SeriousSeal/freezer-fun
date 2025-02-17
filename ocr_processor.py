from paddleocr import PaddleOCR, draw_ocr
import cv2
import os
import numpy as np

def process_image(image_path: str) -> dict:
    try:
        # Bild einlesen
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image at {image_path}")

        # 1. Vorverarbeitungspipeline
        # a) Zu Graustufen konvertieren
        image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # b) Rauschreduzierung mit bilateralem Filter (erhält Kanten)
        image_filtered = cv2.bilateralFilter(image_gray, d=9, sigmaColor=75, sigmaSpace=75)
        
        # c) Adaptive Thresholding mit optimierten Parametern
        image_thresh = cv2.adaptiveThreshold(
            image_filtered, 
            255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,  # Invertieren für weißer Text auf schwarzem Hintergrund
            blockSize=21,  # Größerer Block für mehr Kontext
            C=10
        )
        
        # d) Morphologische Operationen zum Rauschentfernen
        kernel = np.ones((2, 2), np.uint8)
        image_processed = cv2.morphologyEx(image_thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Optional: Zwischenbild speichern zur Inspektion
        cv2.imwrite("processed_image.jpg", image_processed)
        
        # PaddleOCR arbeitet mit Bildern im BGR-Format, wie sie von cv2.imread() geliefert werden.
        # Initialisiere das PP-OCR-Modell. Hier wird "de" als Sprache angegeben – 
        # prüfe, ob dein Anwendungsfall deutsche Texte optimal unterstützt.
        ocr_model = PaddleOCR(use_angle_cls=True, lang="german")
        
        # OCR ausführen: Das Ergebnis ist eine Liste von Zeilen, in denen wiederum die erkannten Wörter mit Bounding Box und Konfidenz enthalten sind.
        results = ocr_model.ocr(image_thresh, cls=True)
        
        magnets = []
        for line in results:
            for word_info in line:
                bbox = word_info[0]          # Four corner points [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text, confidence = word_info[1]  # Detected word and confidence
                
                # Calculate bounding box properties
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                
                x = min(x_coords)
                y = min(y_coords)
                width = max(x_coords) - x
                height = max(y_coords) - y
                
                magnets.append({
                    "text": text,
                    "confidence": confidence,
                    "position": {
                        "x": int(x),
                        "y": int(y),
                        "width": int(width),
                        "height": int(height),
                        "points": bbox  # Keep original points for reference
                    }
                })
        
        return {"magnets": magnets}
        
    except Exception as e:
        raise Exception("Error processing image: " + str(e))


# Beispielaufruf:
if __name__ == "__main__":
    image_path = "pfad/zum/deinem/bild.jpg"  # Passe den Pfad zum Bild an
    result = process_image(image_path)
    print(result)
