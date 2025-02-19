from paddleocr import PaddleOCR, draw_ocr
import cv2
import os
import numpy as np

def quarter_image_with_padding(image, pad=40):
    h, w = image.shape[:2]
    rois = []
    # Definiere die Mitte des Bildes
    mid_x, mid_y = w // 2, h // 2
    # Vier Viertel mit Padding (achte auf Bildgrenzen)
    coords = [
        (max(0, 0 - pad), max(0, 0 - pad), min(mid_x + pad, w), min(mid_y + pad, h)),
        (max(mid_x - pad, 0), max(0 - pad, 0), min(w, w), min(mid_y + pad, h)),
        (max(0 - pad, 0), max(mid_y - pad, 0), min(mid_x + pad, w), min(h, h)),
        (max(mid_x - pad, 0), max(mid_y - pad, 0), min(w, w), min(h, h))
    ]
    for (x1, y1, x2, y2) in coords:
        rois.append((x1, y1, x2 - x1, y2 - y1))
    return rois

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
            cv2.THRESH_BINARY,  # Invertieren für weißer Text auf schwarzem Hintergrund
            blockSize=21,  
            C=10
        )
        
        # d) Morphologische Operationen zum Rauschentfernen
        kernel = np.ones((2, 2), np.uint8)
        image_processed = cv2.morphologyEx(image_thresh, cv2.MORPH_OPEN, kernel, iterations=3)
        
        # Segmentierung: Finde ROIs (Regionen) im vorverarbeiteten Bild
        rois = quarter_image_with_padding(image_processed)
        
        # Initialisiere das PaddleOCR-Modell
        ocr_model = PaddleOCR(use_angle_cls=False, lang="german")
        
        magnets = []
        # Erstelle eine Kopie des Originalbildes zur Visualisierung
        image_with_boxes = image.copy()

        # Für jeden erkannten ROI:
        for (x, y, w, h) in rois:
            # Ausschneiden des interessanten Bereichs
            cropped = image_thresh[y:y+h, x:x+w]
            # Optional: Upscaling des Ausschnitts, falls die Schrift zu klein ist
            scale_factor = 2
            cropped_upscaled = cv2.resize(cropped, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_LINEAR)
            
            # Führe OCR auf dem zugeschnittenen (und ggf. vergrößerten) Bild aus
            results = ocr_model.ocr(cropped_upscaled, cls=False)
            
            # Da wir den Ausschnitt skaliert haben, müssen wir die Koordinaten der erkannten Boxen anpassen
            for line in results:
                if( line is None or not line ):
                    continue
                for word_info in line:
                    if word_info is None or not word_info:
                        continue
                    bbox = word_info[0]  # Liste der 4 Eckpunkte im skalierten Ausschnitt
                    text, confidence = word_info[1]
                    
                    # Passe die Koordinaten zurück auf den Originalausschnitt
                    adjusted_bbox = []
                    for point in bbox:
                        adj_x = int(point[0] / scale_factor) + x
                        adj_y = int(point[1] / scale_factor) + y
                        adjusted_bbox.append((adj_x, adj_y))
                    
                    magnets.append({
                        "text": text,
                        "confidence": confidence,
                        "position": {
                            "x": adjusted_bbox[0][0],
                            "y": adjusted_bbox[0][1],
                            "width": w,
                            "height": h,
                            "points": adjusted_bbox  # Originale Eckpunkte relativ zum Gesamtbild
                        }
                    })
                    
                    # Zeichne die Bounding Box und den erkannten Text in das Visualisierungsbild
                    cv2.polylines(image_with_boxes, [np.array(adjusted_bbox)], isClosed=True, color=(0, 255, 0), thickness=2)
                    cv2.putText(image_with_boxes, text, (adjusted_bbox[0][0], adjusted_bbox[0][1]-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Speichere das Bild mit den eingezeichneten Bounding Boxes
        cv2.imwrite("annotated_image.jpg", image_with_boxes)
        
        return {"magnets": magnets}
    
    except Exception as e:
        raise Exception("Error processing image: " + str(e))


# Beispielaufruf:
if __name__ == "__main__":
    image_path = "pfad/zum/deinem/bild.jpg"  # Passe den Pfad zum Bild an
    result = process_image(image_path)
    print(result)
