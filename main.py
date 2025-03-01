from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from ocr_processor import process_image
import ollama
import tempfile
import os
import json
import base64
import re

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    
#thirdeyeai/DeepSeek-R1-Distill-Qwen-7B-uncensored
def generate_sentences_with_ollama(words: list, model: str = "thirdeyeai/DeepSeek-R1-Distill-Qwen-7B-uncensored"):
    # Ensure we have words to process
    if not words or len(words) == 0:
        return {"sentence": "Keine Wörter gefunden", "used_words": []}
    
    prompt = (
        f"Antworte nur auf deutsch. Baue aus diesen Wörtern Sätze: {', '.join(words)}. "
        "Die Sätze/Wortzusammensetzungen sollen lustig, unhinged und kurz sein. "
        "WICHTIG: Deine Antwort MUSS ein valides JSON-Objekt sein, ohne Erklärungen drumherum:\n"
        "{\n"
        '  "sentence": "<der generierte Satz>",\n'
        '  "used_words": ["<Wort1>", "<Wort2>", ...]\n'
        "}\n"
    )
    
    response = ollama.generate(
        model=model,
        prompt=prompt,
        options={
            "temperature": 0.7,
            "max_tokens": 300,
            "top_p": 0.9
        }
    )
    
    raw_response = response["response"]
    print(f"Raw LLM response: {raw_response}")
    
    # Parse the JSON from the response
    try:
        # First attempt: direct JSON parsing
        try:
            result = json.loads(raw_response.strip())
            if "sentence" in result and "used_words" in result:
                return result
        except json.JSONDecodeError:
            pass
        
        # Second attempt: find JSON-like content using regex
        json_match = re.search(r'({[\s\S]*?})', raw_response)
        if json_match:
            json_str = json_match.group(1)
            try:
                result = json.loads(json_str)
                if "sentence" in result and "used_words" in result:
                    return result
            except json.JSONDecodeError:
                pass
        
        # Third attempt: construct JSON from parts
        sentence_match = re.search(r'"sentence"\s*:\s*"([^"]+)"', raw_response)
        words_match = re.search(r'"used_words"\s*:\s*\[(.*?)\]', raw_response, re.DOTALL)
        
        if sentence_match and words_match:
            sentence = sentence_match.group(1)
            words_text = words_match.group(1)
            used_words = [w.strip(' "\'') for w in re.findall(r'"([^"]+)"', words_text)]
            
            return {
                "sentence": sentence,
                "used_words": used_words
            }
        
        # If all parsing attempts failed, fallback to simple response
        fallback_sentence = " ".join(words[:5]) + "..."
        return {
            "sentence": fallback_sentence,
            "used_words": words
        }
        
    except Exception as e:
        print(f"Error parsing LLM response: {str(e)}")
        # Fallback response
        return {
            "sentence": f"Lustiger Satz mit: {', '.join(words[:3])}...",
            "used_words": words
        }

@app.post("/generate-sentence-from-image/")
async def generate_sentence_from_image(file: UploadFile = File(...)):
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
            
            # Generate sentence with enhanced error handling
            sentence_result = generate_sentences_with_ollama(words)
            print(f"Generated sentence result: {sentence_result}")
            
            # Encode image to base64
            base64_image = base64.b64encode(file_content).decode('utf-8')
            
            # Combine results - ensure we have valid data at each step
            complete_result = {
                "sentence": sentence_result.get("sentence", "Error generating sentence"),
                "used_words": sentence_result.get("used_words", words),
                "ocr_data": ocr_data,
                "image_base64": base64_image
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