class Config:
    # Pfade
    TESSERACT_PATH = "/usr/share/tesseract-ocr/5/tessdata/"  # Pfad zu Tesseract (Linux/Mac)
    MODEL_PATH = "models/deepseek-7b-ggml-q4.bin"  # Pfad zum quantisierten LLM
    TEMP_IMAGE_FOLDER = "temp_images"

    # LLM-Einstellungen
    MAX_TOKENS = 100
    TEMPERATURE = 0.7