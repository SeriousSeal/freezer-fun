from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from ocr_processor import process_image
import ollama
import tempfile
import os
import json

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
    prompt = (
        f"Antworte nur auf deutsch. Baue aus diesen Wörtern Sätze: {', '.join(words)}. "
        "Es dürfen auch Wörter benutzt werden die sich nur so ähnlich anhören wie existierende Wörter, gib mir aber trotzdem als used_words die existierenden Wörter an. "
        "Die Sätze/Wortzusammensetzungen sollen lustig, unhinged und kurz sein. "
        "Bitte antworte im folgenden JSON-Format:\n"
        "{\n"
        '  "sentence": "<der generierte Satz>",\n'
        '  "used_words": ["<Wort1>", "<Wort2>", ...]\n'
        "}\n"
        "Stelle sicher, dass ALLE benutzten Wörter in der Liste 'used_words' also auch in dem genrierten Satz enthalten sind. Wenn nicht ist der Satz invalide."
    )
    
    response = ollama.generate(
        model=model,
        prompt=prompt,
        options={
            "temperature": 0.7,
            "max_tokens": 100,
            "top_p": 0.9
        }
    )
    
    return response["response"]

@app.post("/generate-sentence-from-image/")
async def generate_sentence_from_image(file: UploadFile = File(...)):
    try:
        ocr_result_response = await process_image_run(file)
        ocr_result = ocr_result_response.body.decode()  # falls nötig, anpassen je nach Response
        

        ocr_data = json.loads(ocr_result)
        words = [item["text"] for item in ocr_data.get("magnets", [])]
        print(words)
        sentence_result = generate_sentences_with_ollama(words)
        
        return JSONResponse(content=sentence_result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)