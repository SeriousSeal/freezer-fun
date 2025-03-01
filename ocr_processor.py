from paddleocr import PaddleOCR, draw_ocr
import cv2
import os
import numpy as np
from collections import defaultdict
import difflib
import re

def generate_sliding_windows(image, window_size=400, overlap_percent=30):
    """
    Generate overlapping sliding windows across the image.
    
    Args:
        image: Input image
        window_size: Size of the sliding window (width & height)
        overlap_percent: Percentage of overlap between adjacent windows (0-100)
        
    Returns:
        List of (x, y, width, height) tuples representing each window
    """
    h, w = image.shape[:2]
    stride = int(window_size * (1 - overlap_percent / 100))
    
    windows = []
    
    # Adjust window_size if it's larger than the image
    if window_size > h or window_size > w:
        window_size = min(h, w) // 2
        stride = window_size // 2
    
    for y in range(0, h - window_size + 1, stride):
        for x in range(0, w - window_size + 1, stride):
            windows.append((x, y, window_size, window_size))
    
    # Add edge windows to ensure full coverage
    right_edge = w - window_size
    bottom_edge = h - window_size
    
    # Add right edge windows
    for y in range(0, h - window_size + 1, stride):
        if (right_edge, y, window_size, window_size) not in windows:
            windows.append((right_edge, y, window_size, window_size))
    
    # Add bottom edge windows
    for x in range(0, w - window_size + 1, stride):
        if (x, bottom_edge, window_size, window_size) not in windows:
            windows.append((x, bottom_edge, window_size, window_size))
    
    # Add bottom-right corner
    if (right_edge, bottom_edge, window_size, window_size) not in windows:
        windows.append((right_edge, bottom_edge, window_size, window_size))
    
    return windows

def calculate_iou(box1, box2):
    """Calculate Intersection over Union for two bounding boxes."""
    # Extract points from boxes
    if isinstance(box1, dict) and "position" in box1:
        points1 = box1["position"]["points"]
    else:
        points1 = box1
        
    if isinstance(box2, dict) and "position" in box2:
        points2 = box2["position"]["points"]
    else:
        points2 = box2
    
    # Get bounding box coordinates
    x1_min = min(p[0] for p in points1)
    y1_min = min(p[1] for p in points1)
    x1_max = max(p[0] for p in points1)
    y1_max = max(p[1] for p in points1)
    
    x2_min = min(p[0] for p in points2)
    y2_min = min(p[1] for p in points2)
    x2_max = max(p[0] for p in points2)
    y2_max = max(p[1] for p in points2)
    
    # Calculate intersection area
    x_overlap = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
    y_overlap = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
    intersection = x_overlap * y_overlap
    
    # Calculate union area
    area1 = (x1_max - x1_min) * (y1_max - y1_min)
    area2 = (x2_max - x2_min) * (y2_max - y2_min)
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0

def calculate_containment(box1, box2):
    """
    Calculate how much of box1 is contained within box2.
    Returns a value between 0 (no containment) and 1 (complete containment).
    """
    # Extract points from boxes
    if isinstance(box1, dict) and "position" in box1:
        points1 = box1["position"]["points"]
    else:
        points1 = box1
        
    if isinstance(box2, dict) and "position" in box2:
        points2 = box2["position"]["points"]
    else:
        points2 = box2
    
    # Get bounding box coordinates
    x1_min = min(p[0] for p in points1)
    y1_min = min(p[1] for p in points1)
    x1_max = max(p[0] for p in points1)
    y1_max = max(p[1] for p in points1)
    
    x2_min = min(p[0] for p in points2)
    y2_min = min(p[1] for p in points2)
    x2_max = max(p[0] for p in points2)
    y2_max = max(p[1] for p in points2)
    
    # Calculate intersection area
    x_overlap = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
    y_overlap = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
    intersection = x_overlap * y_overlap
    
    # Calculate area of box1
    area1 = (x1_max - x1_min) * (y1_max - y1_min)
    
    # Return the ratio of intersection to box1's area
    return intersection / area1 if area1 > 0 else 0

def is_substring_or_similar(text1, text2, similarity_threshold=0.8):
    """
    Check if one text is a substring of another or if they are very similar.
    Returns True if text1 is contained within text2 or vice versa,
    or if they have high similarity ratio.
    """
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()
    
    # Immediate check for identical text
    if text1 == text2:
        return True
    
    # Check if one is a substring of another
    if text1 in text2 or text2 in text1:
        return True
        
    # Check similarity using difflib
    similarity = difflib.SequenceMatcher(None, text1, text2).ratio()
    return similarity >= similarity_threshold

def get_box_coordinates(detection):
    """Extract the coordinates of a detection's bounding box in (x_min, y_min, x_max, y_max) format"""
    points = detection["position"]["points"]
    x_min = min(p[0] for p in points)
    y_min = min(p[1] for p in points)
    x_max = max(p[0] for p in points)
    y_max = max(p[1] for p in points)
    return x_min, y_min, x_max, y_max

def remove_duplicates_and_subwords(detections):
    """
    Multi-strategy approach to aggressively filter duplicate and partial word detections.
    
    Strategies:
    1. Direct substring filtering with spatial overlap
    2. Text overlap analysis with exact character matching
    3. Relaxed matching based on common word prefixes/suffixes
    4. Confidence-based replacement for similar detections
    """
    if len(detections) <= 1:
        return detections
    
    # First - normalize text for better comparisons
    for det in detections:
        det["normalized_text"] = det["text"].lower().strip()
    
    # Sort by length (longer texts first) then by confidence
    sorted_detections = sorted(detections, key=lambda x: (len(x["normalized_text"]), x["confidence"]), reverse=True)
    
    # Set to track which detections to keep
    to_keep = set(range(len(sorted_detections)))
    
    # STRATEGY 1: Direct substring filtering with spatial check
    for i in range(len(sorted_detections)):
        if i not in to_keep:
            continue
            
        for j in range(len(sorted_detections)):
            if i == j or j not in to_keep:
                continue
                
            text_i = sorted_detections[i]["normalized_text"]
            text_j = sorted_detections[j]["normalized_text"]
            
            # Check if one is a substring of another
            if text_j in text_i and text_i != text_j:
                # Verify they have significant overlap (very low threshold to catch more)
                if calculate_iou(sorted_detections[i], sorted_detections[j]) > 0.1:
                    to_keep.remove(j)  # Remove the shorter text
                    
    # STRATEGY 2: Text overlap analysis - detect when most characters overlap
    for i in range(len(sorted_detections)):
        if i not in to_keep:
            continue
            
        for j in range(len(sorted_detections)):
            if i == j or j not in to_keep:
                continue
                
            # Check spatial overlap is significant
            if calculate_iou(sorted_detections[i], sorted_detections[j]) > 0.25:
                # If texts have significant character overlap but aren't identical
                text_i = sorted_detections[i]["normalized_text"]
                text_j = sorted_detections[j]["normalized_text"]
                
                # Count matching characters in both texts
                common_chars = sum(c in text_i for c in text_j)
                if common_chars / len(text_j) > 0.7:  # If 70% of shorter text's chars are in longer text
                    to_keep.remove(j)
    
    # STRATEGY 3: Relaxed matching for common prefixes/suffixes
    for i in range(len(sorted_detections)):
        if i not in to_keep:
            continue
            
        for j in range(len(sorted_detections)):
            if i == j or j not in to_keep:
                continue
                
            # Check if boxes are close to each other
            iou = calculate_iou(sorted_detections[i], sorted_detections[j])
            if iou > 0.2:
                text_i = sorted_detections[i]["normalized_text"]
                text_j = sorted_detections[j]["normalized_text"]
                
                # Check if one text starts or ends with the other (common prefix/suffix)
                if (text_i.startswith(text_j) or text_i.endswith(text_j)) and len(text_j) < len(text_i):
                    to_keep.remove(j)
    
    # STRATEGY 4: Position-based filtering for small subwords
    # Group by approximate vertical position (text lines)
    line_groups = defaultdict(list)
    for i in to_keep:
        y_min, _, _, y_max = get_box_coordinates(sorted_detections[i])
        y_center = (y_min + y_max) / 2
        # Group by vertical position with some tolerance
        line_key = int(y_center / 10) * 10  # Group in 10-pixel bands
        line_groups[line_key].append(i)
    
    # For each line, check for small contained words
    for _, indices in line_groups.items():
        if len(indices) <= 1:
            continue
            
        for i in indices:
            if i not in to_keep:
                continue
                
            for j in indices:
                if i == j or j not in to_keep:
                    continue
                    
                # Get bounding box coordinates
                i_x_min, i_y_min, i_x_max, i_y_max = get_box_coordinates(sorted_detections[i])
                j_x_min, j_y_min, j_x_max, j_y_max = get_box_coordinates(sorted_detections[j])
                
                # Check if j is fully contained within i horizontally
                if (j_x_min >= i_x_min and j_x_max <= i_x_max):
                    # If j's text is significantly shorter
                    if len(sorted_detections[j]["normalized_text"]) < 0.7 * len(sorted_detections[i]["normalized_text"]):
                        to_keep.remove(j)
    
    # Create final filtered list
    result = [sorted_detections[i] for i in to_keep]
    
    # Final sanity check - remove any very short (1-2 char) text that's close to a longer text
    result = [det for det in result if not (
        len(det["normalized_text"]) <= 2 and 
        any(calculate_iou(det, other) > 0.1 and len(other["normalized_text"]) > 2 
            for other in result if other != det)
    )]
    
    return result

def create_debug_visualization(image, all_detections, filtered_detections):
    """
    Create a comprehensive debug visualization showing which detections are kept and which are filtered.
    Also includes more information about why detections were filtered.
    """
    debug_image = image.copy()
    
    # Create mapping for quick lookup
    filtered_ids = {id(det): det for det in filtered_detections}
    
    # Group filtered-out detections by possible reason
    substrings = []
    overlapping = []
    low_confidence = []
    
    for det in all_detections:
        if id(det) not in filtered_ids:
            # Try to determine why this detection was filtered out
            is_substring = any(det["text"].lower() in other["text"].lower() and det["text"].lower() != other["text"].lower() 
                              for other in filtered_detections)
            
            has_overlap = any(calculate_iou(det, other) > 0.2 for other in filtered_detections)
            
            if is_substring and has_overlap:
                substrings.append(det)
            elif has_overlap:
                overlapping.append(det)
            else:
                low_confidence.append(det)
    
    # Draw filtered out substrings in red
    for det in substrings:
        bbox = np.array(det["position"]["points"])
        text = det["text"]
        cv2.polylines(debug_image, [bbox], isClosed=True, color=(0, 0, 255), thickness=1)
        cv2.putText(debug_image, f"SUB: {text}", (bbox[0][0], bbox[0][1]-5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    
    # Draw filtered out overlapping detections in yellow
    for det in overlapping:
        bbox = np.array(det["position"]["points"])
        text = det["text"]
        cv2.polylines(debug_image, [bbox], isClosed=True, color=(0, 255, 255), thickness=1)
        cv2.putText(debug_image, f"OVER: {text}", (bbox[0][0], bbox[0][1]-5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    
    # Draw other filtered detections in blue
    for det in low_confidence:
        bbox = np.array(det["position"]["points"])
        text = det["text"]
        cv2.polylines(debug_image, [bbox], isClosed=True, color=(255, 0, 0), thickness=1)
        cv2.putText(debug_image, f"OTHER: {text}", (bbox[0][0], bbox[0][1]-5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
    
    # Draw kept detections in green with confidence
    for det in filtered_detections:
        bbox = np.array(det["position"]["points"])
        text = det["text"]
        conf = det["confidence"]
        cv2.polylines(debug_image, [bbox], isClosed=True, color=(0, 255, 0), thickness=2)
        cv2.putText(debug_image, f"{text} ({conf:.2f})", (bbox[0][0], bbox[0][1]-5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    return debug_image

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
            cv2.THRESH_BINARY,
            blockSize=21,  
            C=10
        )
        
        # d) Morphologische Operationen zum Rauschentfernen
        kernel = np.ones((2, 2), np.uint8)
        image_processed = cv2.morphologyEx(image_thresh, cv2.MORPH_OPEN, kernel, iterations=3)
        
        # Segmentierung: Verwende sliding windows statt quarter_image_with_padding
        h, w = image_processed.shape[:2]
        window_size = min(400, min(h, w) // 2)  # Dynamische Fenstergröße basierend auf Bildgröße
        rois = generate_sliding_windows(image_processed, window_size=window_size, overlap_percent=30)
        
        # Initialisiere das PaddleOCR-Modell
        ocr_model = PaddleOCR(use_angle_cls=False, lang="german", ocr_version='PP-OCRv4', use_space_char=True)
        
        all_detections = []
        # Erstelle eine Kopie des Originalbildes zur Visualisierung
        image_with_boxes = image.copy()

        # Für jeden sliding window:
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
                if(line is None or not line):
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
                    
                    all_detections.append({
                        "text": text,
                        "confidence": confidence,
                        "position": {
                            "x": adjusted_bbox[0][0],
                            "y": adjusted_bbox[0][1],
                            "width": adjusted_bbox[2][0] - adjusted_bbox[0][0],
                            "height": adjusted_bbox[2][1] - adjusted_bbox[0][1],
                            "points": adjusted_bbox
                        }
                    })
        
        # Apply the aggressive multi-strategy filtering approach
        filtered_detections = remove_duplicates_and_subwords(all_detections)
        
        # Create detailed debug visualization
        debug_image = create_debug_visualization(image, all_detections, filtered_detections)
        
        # Final result is our filtered detections
        magnets = filtered_detections
        
        # Draw final detections in the result image
        image_with_boxes = image.copy()
        for detection in magnets:
            bbox = np.array(detection["position"]["points"])
            text = detection["text"]
            cv2.polylines(image_with_boxes, [bbox], isClosed=True, color=(0, 255, 0), thickness=2)
            cv2.putText(image_with_boxes, text, (bbox[0][0], bbox[0][1]-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Save the images
        cv2.imwrite("annotated_image.jpg", image_with_boxes)
        cv2.imwrite("debug_filtering.jpg", debug_image)
        
        return {"magnets": magnets}
    
    except Exception as e:
        raise Exception("Error processing image: " + str(e))


# Beispielaufruf:
if __name__ == "__main__":
    image_path = "pfad/zum/deinem/bild.jpg"  # Passe den Pfad zum Bild an
    result = process_image(image_path)
    print(result)
