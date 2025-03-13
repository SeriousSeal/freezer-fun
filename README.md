# Freezer Fun

A web application that processes images using OCR and LLM services.

## Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- npm or yarn
- Ollama (for local LLM support)

## Configuration

### Python Backend Configuration

1. Copy the example config file:
```bash
cp config.json.example config.json
```

2. Configure your `config.json` with the following settings:
```json
{
  "llm_provider": "openrouter",
  "openrouter": {
    "api_key": "your_openrouter_api_key_here",
    "model": "qwen/qwq-32b:free",
    "temperature": 0.7
  },
  "ollama": {
    "model": "thirdeyeai/DeepSeek-R1-Distill-Qwen-7B-uncensored",
    "temperature": 0.7
    "top_p": 0.9
  }
}

```

### LLM Setup

1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull the required model:
```bash
ollama pull llama2
```

You can also use other models supported by Ollama. Update the `model` field in your `config.json` accordingly.

## Project Structure

```
freezer-fun/
├── freez_frontend/     # Vite/React frontend
├── main.py            # FastAPI backend server
├── llm_service.py     # LLM service implementation
├── ocr_processor.py   # OCR processing implementation
└── requirements.txt   # Python dependencies
```

## Backend Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Start the backend server:
```bash
uvicorn main:app --reload
```

The backend server will run on `http://localhost:8000` by default.

## Frontend Setup

1. Navigate to the frontend directory:
```bash
cd freez_frontend
```

2. Install dependencies:
```bash
npm install
# or
yarn install
```

3. Start the development server:
```bash
npm run dev
# or
yarn dev
```

The frontend development server will run on `http://localhost:5173` by default.

## Usage

1. Open your browser and navigate to `http://localhost:5173`
2. Upload an image using the interface
3. The application will process the image using OCR and LLM services
4. View the results in the web interface

## Development

- Backend API endpoints are defined in `main.py`
- OCR processing logic is in `ocr_processor.py`
- LLM service implementation is in `llm_service.py`
- Frontend components are in the `freez_frontend/src` directory

