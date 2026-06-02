# Presenton AI Backend

## Setup

1. **Install Dependencies**
```bash
cd backend
pip install -r requirements.txt
```

2. **Ensure Ollama is Running**
```bash
ollama serve
# In another terminal:
ollama pull llama3
```

3. **Start FastAPI Server**
```bash
python main.py
```
Server runs on `http://localhost:8000`

## API Endpoints

- **POST /generate** - Generate presentation
  ```json
  {
    "topic": "AI in Business",
    "slide_count": 10,
    "theme": "modern"
  }
  ```
  Returns: `{id, topic, status, pptx_path, generated_at}`

- **POST /upload-pdf** - Upload PDF for content extraction
- **GET /health** - Health check
- **GET /download/{file_path:path}** - Download PPTX

## Files

### Core Flow
1. **main.py** - FastAPI server + LangGraph workflow orchestration
   - Routes API requests through workflow graph
   - Integrates all nodes into pipeline

2. **outline_node.py** - Content generation nodes
   - `generate_outline_node()` - Creates structured outline using Llama3
   - `enrich_outline_node()` - Adds detailed descriptions to each slide

3. **ppt_node.py** - Presentation creation nodes
   - `generate_ppt_node()` - Converts outline to PPTX using python-pptx
   - `validate_pptx_node()` - Validates successful file creation

4. **generate_ppt.py** - PPTX generation library
   - `PresentationGenerator` class
   - Professional theme-aligned styling
   - Slide types: title, content, comparison, summary

## Workflow Pipeline

```
Topic Input
    ↓
outline_node (Llama3 outline generation)
    ↓
enrich_node (Add descriptions)
    ↓
ppt_node (Create PPTX with generate_ppt.py)
    ↓
validate_node (Verify output)
    ↓
Generate PPTX file
```

## Theme & Design

All colors match frontend (`/frontend/src/App.css`):
- Primary: `#1e40af` (blue) - used for titles, headers
- Accent: `#f59e0b` (amber) - used for highlights, dividers
- Professional sans-serif typography
- Consistent spacing and padding

## Notes

- Presentations saved to `presentations/` folder
- PDF uploads saved to `uploads/` folder
- Llama3 must be running for outline generation
- Minimal file structure: 4 Python files handle all functionality
- Modular design: Easy to update individual nodes

