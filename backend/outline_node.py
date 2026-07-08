"""
Outline Node - Generates presentation outline using Llama3
Uses LangGraph state management
"""

import json
import re
import ollama
from typing import TypedDict, Optional
from datetime import datetime
from language_utils import get_multilingual_prompt, LANGUAGE_NAMES

class PresentationState(TypedDict):
    topic: str
    slide_count: int
    theme: str
    language: Optional[str]
    content: list
    generated_at: str
    status: str
    pptx_path: Optional[str]
    error: Optional[str]
    pdf_content: Optional[str]
    pdf_path: Optional[str]
    image_urls: Optional[list]
    image_slides: Optional[list]
    image_keywords: Optional[list]
    slides: Optional[list]
    file_type: Optional[str]

def generate_outline_node(state: PresentationState) -> PresentationState:
    """
    Generate presentation outline using Llama3
    """
    try:
        language = state.get('language', 'english')
        lang_name = LANGUAGE_NAMES.get(language, language.capitalize())
        
        prompt = f"""Create a professional {state['slide_count']}-slide presentation outline about: {state['topic']}

IMPORTANT: 
1. Return ONLY valid, complete JSON - nothing else. NO markdown, NO code blocks.
2. ALL content must be in {lang_name}. Translate every title, description, and key point to {lang_name}.
3. Do NOT use English. Respond entirely in {lang_name}.
4. Each description should be 3-4 sentences - a proper paragraph explaining the concept.
5. Key points should be brief, punchy bullets - 5-10 words each.

{{
    "title": "Presentation Title in {lang_name}",
    "slides": [
        {{"slide_number": 1, "title": "Slide Title in {lang_name}", "description": "This is a 4-5 sentence paragraph explaining the slide topic in detail. It provides context and background information about the concept. The paragraph should be informative and give a good overview. It helps readers understand the key context before seeing the bullet points. The description flows naturally like a proper paragraph.", "key_points": ["Brief insight one", "Brief insight two", "Brief insight three", "Brief insight four", "Brief insight five"]}},
        {{"slide_number": 2, "title": "Another Title in {lang_name}", "description": "Another 4-5 sentence paragraph providing deeper explanation in {lang_name}. Each paragraph should be complete and informative. It gives the full context for understanding the topic properly. Multiple sentences help explain the concept thoroughly. This is the main body text for each slide.", "key_points": ["Key point one", "Key point two", "Key point three", "Key point four", "Key point five"]}}
    ],
    "summary": "One sentence summary in {lang_name}"
}}

REQUIREMENTS:
- Generate exactly {state['slide_count']} slides
- Each slide: slide_number, title, description (3-4 sentences as a proper paragraph), key_points (5 brief items, 5-10 words each)
- Return COMPLETE, VALID JSON
- ALL text must be in {lang_name}
- Description = paragraph (3-4 lines), Key Points = short bullets
- Descriptions must be substantial paragraphs, NOT short sentences
- Ensure all JSON brackets are closed properly"""

        print(f"DEBUG: Generating outline in {lang_name} for topic: {state['topic']}")
        response = ollama.generate(
            model="llama3",
            prompt=prompt,
            stream=False,
            options={"num_predict": 2048}  # 2048 needed for longer topics with 15 slides
        )
        
        response_text = response['response'].strip()
        print(f"DEBUG: Ollama response received (length: {len(response_text)})")
        
        # Check for truncation
        if response_text.endswith(',') or response_text.endswith('"'):
            print(f"DEBUG: WARNING - Response may be truncated, ends with: {response_text[-20:]}")
        
        def parse_markdown_outline_to_slides(text: str, expected_count: int = None):
            """Try to parse a markdown-style outline into structured slides.

            Looks for patterns like "**Slide 1: Title**", "* Slide Title: ...", "* Key Points:" and bullet lines.
            Returns a dict with title, slides list and optional summary.
            """
            slides = []
            title_match = re.search(r"\*\*Title:\*\*\s*(.+)", text)
            doc_title = title_match.group(1).strip() if title_match else state.get('topic', 'Presentation')

            # Split by Slide headings
            parts = re.split(r"\*\*Slide\s*\d+:\s*", text)
            if len(parts) <= 1:
                # Try alternative split on lines that start with 'Slide X:'
                parts = re.split(r"\n\s*Slide\s*\d+:\s*", text)

            for idx, part in enumerate(parts[1:] if len(parts) > 1 else []):
                # Try extracting title
                title_search = re.search(r"\*\s*Slide Title:\s*(.+)", part)
                slide_title = title_search.group(1).strip() if title_search else f"Slide {idx+1}"

                # Extract key points (lines starting with +, -, or *)
                key_points = re.findall(r"^[\t ]*[\+\-\*]\s*(.+)$", part, flags=re.MULTILINE)
                # Clean up key points
                key_points = [kp.strip().rstrip('.') for kp in key_points]

                # Extract a short summary or description if present
                summary_search = re.search(r"\*\*Summary:\*\*\s*(.+?)(?:\n\n|$)", part, flags=re.DOTALL)
                description = summary_search.group(1).strip() if summary_search else ''

                slides.append({
                    "slide_number": idx + 1,
                    "title": slide_title,
                    "description": description,
                    "key_points": key_points or []
                })

            # If no slides found, return None
            if not slides:
                return None

            # If expected_count provided, pad or trim
            if expected_count and len(slides) != expected_count:
                # Trim or extend with empty slides
                if len(slides) > expected_count:
                    slides = slides[:expected_count]
                else:
                    for i in range(len(slides), expected_count):
                        slides.append({
                            "slide_number": i + 1,
                            "title": f"Slide {i+1}",
                            "description": "",
                            "key_points": []
                        })

            return {"title": doc_title, "slides": slides}

        def clean_json(text: str) -> str:
            """
            Fix common LLM JSON mistakes before parsing:
            - Trailing commas before ] or }  (e.g. [..., ] or {..., })
            - Stray whitespace / newlines around commas
            """
            # Remove trailing commas before closing brackets/braces
            cleaned = re.sub(r',\s*([\]\}])', r'\1', text)
            return cleaned

        def extract_json_object(text: str) -> str:
            """
            Pull out the first complete {...} block from text.
            Handles LLM preamble like 'Here is the JSON:\n\n{...}'.
            """
            start = text.find('{')
            if start == -1:
                return text
            depth = 0
            for i in range(start, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        return text[start:i + 1]
            # Truncated — return from start to end and let cleaner fix it
            return text[start:]

        def try_parse(text: str):
            """Try json.loads with progressively more aggressive cleanup."""
            for candidate in (text, clean_json(text)):
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass
            # Extract the JSON object block and retry
            extracted = extract_json_object(text)
            for candidate in (extracted, clean_json(extracted)):
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass
            return None

        # Strip code fences if present
        raw = response_text
        if '```' in raw:
            start = raw.find('```json') + 7 if '```json' in raw else raw.find('```') + 3
            end   = raw.rfind('```')
            if end > start:
                raw = raw[start:end].strip()

        outline = try_parse(raw)

        if outline and 'slides' in outline:
            state['content'] = outline
            print(f"DEBUG: Successfully parsed JSON outline ({len(outline['slides'])} slides)")
        else:
            print(f"DEBUG: JSON parse failed, trying markdown outline parser")
            parsed = parse_markdown_outline_to_slides(response_text, expected_count=state.get('slide_count'))
            if parsed and parsed.get('slides'):
                state['content'] = parsed
                state['content']['status'] = 'parsed_markdown'
                print(f"DEBUG: Parsed slides from markdown outline ({len(parsed['slides'])} slides)")
            else:
                # Last resort – keep raw text so ppt_node can attempt its own extraction
                state['content'] = {
                    "title": state['topic'],
                    "outline": response_text,
                    "status": "raw"
                }
                print(f"DEBUG: Stored raw outline for downstream extraction")
        
        state['status'] = 'outline_generated'
        print(f"DEBUG: outline_node returning with content keys: {state['content'].keys() if isinstance(state['content'], dict) else 'N/A'}")
        return state
        
    except Exception as e:
        print(f"ERROR in generate_outline_node: {str(e)}")
        import traceback
        traceback.print_exc()
        state['status'] = 'error'
        state['content'] = {"error": str(e)}
        return state

def enrich_outline_node(state: PresentationState) -> PresentationState:
    """
    Enhance outline with detailed descriptions for each slide (if missing)
    """
    try:
        if isinstance(state['content'], dict) and 'slides' in state['content']:
            slides = state['content']['slides']
            enriched_slides = []
            
            for slide in slides:
                if 'description' not in slide or not slide.get('description', '').strip():
                    print(f"DEBUG: Generating description for: {slide['title']}")
                    key_points_text = ', '.join(slide.get('key_points', []))
                    prompt = f"""Add a comprehensive, detailed description (4-5 sentences) for this presentation slide:
Title: {slide['title']}
Key points: {key_points_text}

Return only the detailed description, nothing else. Make it informative and thorough."""
                    try:
                        response = ollama.generate(
                            model="llama3",
                            prompt=prompt,
                            stream=False
                        )
                        slide['description'] = response['response'].strip()
                        print(f"DEBUG: Description generated for {slide['title']}")
                    except Exception as desc_error:
                        print(f"ERROR: Failed to generate description: {str(desc_error)}")
                        slide['description'] = f"Learn more about {slide['title']} and understand its key aspects."
                else:
                    print(f"DEBUG: Description already exists for: {slide['title']}")
                
                enriched_slides.append(slide)
            
            state['content']['slides'] = enriched_slides
        state['status'] = 'enriched'
        return state
    except Exception as e:
        print(f"ERROR in enrich_outline_node: {str(e)}")
        state['status'] = 'enrichment_error'
        return state
