from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from ocr_processor import process_image, create_marked_image
import tempfile
import os
import base64

from llm_service import LLMService

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM service
llm_service = LLMService()

@app.post("/process-image/")
async def process_image_run(file: UploadFile = File(...)):
    try:
        # Temporäre Datei erstellen
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            contents = await file.read()  # await the file read
            temp.write(contents)
            temp_path = temp.name

        # Bildverarbeitung durchführen - no await needed since it's synchronous
        result = process_image(temp_path)

        # Temporäre Datei löschen
        os.unlink(temp_path)

        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/generate-sentence-from-image/")
async def generate_sentence_from_image(file: UploadFile = File(...), instructions: str = None):
    try:
        # Save the file content for later use
        file_content = await file.read()
        
        # Create a temporary file for OCR processing
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp.write(file_content)
            temp_path = temp.name
        
        try:
            # Process OCR directly with the temporary file path
            ocr_data = process_image(temp_path)
            
            # Check if we got valid OCR results
            if not ocr_data or "magnets" not in ocr_data or not ocr_data["magnets"]:
                return JSONResponse({"error": "No text detected in image"}, status_code=400)
            
            # Ensure each magnet has the expected structure
            for magnet in ocr_data["magnets"]:
                if "text" not in magnet:
                    magnet["text"] = "Unknown"
                
                # If box is missing or incomplete, add a default box
                if "box" not in magnet or not all(k in magnet["box"] for k in ["x", "y", "w", "h"]):
                    magnet["box"] = {"x": 10, "y": 10, "w": 100, "h": 30}
            
            words = [item["text"] for item in ocr_data.get("magnets", [])]
            print(f"Detected words: {words}")
            
            # Generate sentence using the service with optional instructions
            sentence_result = llm_service.generate_sentence(words, instructions)
            print(f"Generated sentence result: {sentence_result}")
            
            # Return the original image
            original_image_base64 = base64.b64encode(file_content).decode('utf-8')
            
            # Combine results
            complete_result = {
                "sentence": sentence_result.get("sentence", "Error generating sentence"),
                "used_words": sentence_result.get("used_words", words),
                "ocr_data": ocr_data,
                "base64_image": original_image_base64
            }
            
            return JSONResponse(content=complete_result)
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"Processing error: {str(e)}"}, status_code=500)