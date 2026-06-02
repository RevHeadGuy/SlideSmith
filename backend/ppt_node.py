"""
PPT Node - Converts outline to PPTX presentation
Integrates with generate_ppt.py
"""

from generate_ppt import PresentationGenerator, detect_slide_layout, extract_pie_data, extract_bar_data
from image_node import calculate_image_positions
from outline_node import PresentationState
from typing import Optional
from datetime import datetime
from pathlib import Path
import json


def generate_ppt_node(state: PresentationState) -> PresentationState:
    """
    Convert presentation outline to PPTX file
    """
    try:
        # Extract content
        content = state['content']
        print(f"DEBUG: Content type: {type(content)}")
        print(f"DEBUG: Content: {content}")
        
        if not isinstance(content, dict):
            print(f"ERROR: Content is not a dict, it's {type(content)}")
            state['status'] = 'ppt_error'
            state['error'] = f"Content must be dict, got {type(content)}"
            return state
        
        title = content.get('title', state['topic'])
        slides = content.get('slides', [])
        print(f"DEBUG: Found {len(slides)} slides in content")
        
        if not slides and 'outline' in content:
            print("DEBUG: No structured slides, attempting to parse from raw outline")
            import re as _re
            raw_outline = content.get('outline', '')

            def _clean_json(text: str) -> str:
                """Strip trailing commas before ] or } so LLM output parses cleanly."""
                return _re.sub(r',\s*([\]\}])', r'\1', text)

            def _extract_json_object(text: str) -> str:
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

            def _try_parse(text: str):
                for candidate in (text, _clean_json(text)):
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        pass
                # Last attempt: extract the JSON object block first
                extracted = _extract_json_object(text)
                for candidate in (extracted, _clean_json(extracted)):
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        pass
                return None

            try:
                # Strip code fences if present, then try to parse
                candidate = raw_outline
                if '```' in candidate:
                    s = candidate.find('```json') + 7 if '```json' in candidate else candidate.find('```') + 3
                    e = candidate.rfind('```')
                    if e > s:
                        candidate = candidate[s:e].strip()

                extracted_json = _try_parse(candidate)

                if extracted_json and 'slides' in extracted_json and isinstance(extracted_json['slides'], list):
                    slides = extracted_json['slides']
                    title  = extracted_json.get('title', title)
                    print(f"DEBUG: Successfully extracted {len(slides)} slides from raw outline")
                else:
                    print(f"DEBUG: Parsed JSON but no slides array found")

            except Exception as parse_error:
                print(f"DEBUG: Unexpected error in JSON parsing: {str(parse_error)}")
        
        if not slides:
            print("DEBUG: Still no slides, generating generic ones from topic")
            slides = [
                {
                    "title": f"Slide {i+1}", 
                    "key_points": [f"Key point {j+1}" for j in range(3)], 
                    "description": ""
                }
                for i in range(state['slide_count'])
            ]
            print(f"DEBUG: Generated {len(slides)} generic slides")
        
        # Create presentation
        ppt = PresentationGenerator(
            title=title,
            subtitle="",
            theme=state['theme']  
        )
        
        ppt.add_title_slide()
        
        print(f"\nDEBUG: === PPT NODE STATE CHECK ===")
        print(f"DEBUG: state object id: {id(state)}")
        print(f"DEBUG: state['image_urls'] type: {type(state.get('image_urls'))}")
        print(f"DEBUG: state['image_urls'] value: {state.get('image_urls')}")
        print(f"DEBUG: state['image_urls'] list object id: {id(state.get('image_urls'))}")
        print(f"DEBUG: state['image_slides'] value: {state.get('image_slides')}")
        print(f"DEBUG: state['image_keywords'] value: {state.get('image_keywords')}")
        
        # Get image info from state
        image_paths_available = state.get('image_urls', [])
        
        print(f"DEBUG: Available images from cache: {len(image_paths_available)}")
        for idx, img_path in enumerate(image_paths_available):
            print(f"DEBUG:   Image {idx}: {img_path}")
            print(f"DEBUG:   Exists: {Path(img_path).exists() if img_path else 'None'}")
        
        if len(slides) > 0 and len(image_paths_available) > 0:
            total_actual_slides = len(slides) + 2 
            image_positions = calculate_image_positions(total_actual_slides)
            print(f"DEBUG: Recalculated image positions for {total_actual_slides} total slides: {image_positions}")
            
            slide_to_image = {}
            for idx, slide_pos in enumerate(image_positions):
                if idx < len(image_paths_available):
                    image_path = image_paths_available[idx]
                    if Path(image_path).exists():
                        slide_to_image[slide_pos] = image_path
                        print(f"DEBUG: ✓ Mapping slide {slide_pos} to valid image: {image_path}")
                    else:
                        print(f"DEBUG: ✗ Image not found: {image_path}")
        else:
            slide_to_image = {}
            if len(slides) == 0:
                print(f"DEBUG: No slides available")
            if len(image_paths_available) == 0:
                print(f"DEBUG: No images available")
        
        total_slides = len(slides)

        for i, slide in enumerate(slides):
            slide_title = slide.get('title', f'Slide {i+1}')
            key_points = slide.get('key_points', [])
            description = slide.get('description', '')
            slide_absolute_index = i + 1
            page_num = i + 2  # +2 because slide 1 is title slide

            print(f"DEBUG: Processing slide {i}: absolute_index={slide_absolute_index}, title='{slide_title}'")

            has_image = slide_absolute_index in slide_to_image
            is_last_slide = (i == len(slides) - 1)
            layout_type = detect_slide_layout(slide, is_last_slide=is_last_slide, has_image=has_image)
            print(f"DEBUG: Slide {i} layout_type={layout_type}")

            if layout_type == "full_image" and has_image:
                image_path = slide_to_image[slide_absolute_index]
                ppt.add_full_image_slide(slide_title, image_path, description)
            elif layout_type == "large_key_points":
                ppt.add_enhanced_conclusion_slide(slide_title, key_points)
            elif layout_type == "stats":
                ppt.add_stats_slide(slide_title, key_points, description, page_num=page_num)
            elif layout_type == "timeline":
                ppt.add_timeline_slide(slide_title, key_points, description, page_num=page_num)
            elif layout_type == "pie_chart":
                ppt.add_pie_chart_slide(slide_title, key_points, description, page_num=page_num)
            elif layout_type == "bar_chart":
                ppt.add_bar_chart_slide(slide_title, key_points, description, page_num=page_num)
            else:
                # ── 1-2 sentence intro paragraph ──────────────────────────────
                bullets = []
                if description:
                    sentences = [s.strip() for s in description.replace('!', '.').replace('?', '.').split('.') if s.strip()]
                    short_desc = '. '.join(sentences[:2])
                    if short_desc and not short_desc.endswith('.'):
                        short_desc += '.'
                    bullets.append(short_desc)

                # ── 3-4 bullet points ─────────────────────────────────────────
                for point in key_points[:4]:
                    bullets.append(f"• {point}")

                if not bullets or all(b == "" for b in bullets):
                    bullets = [f"• {slide_title}", f"• Key information about {slide_title}"]

                if has_image:
                    image_path = slide_to_image[slide_absolute_index]
                    try:
                        ppt.add_content_slide_with_image(
                            slide_title, bullets, image_path,
                            image_position="right", page_num=page_num
                        )
                    except Exception as e:
                        print(f"ERROR: Failed to add slide with image: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        ppt.add_content_slide(slide_title, bullets, slide_type='bullet', page_num=page_num)
                else:
                    ppt.add_content_slide(slide_title, bullets, slide_type='bullet', page_num=page_num)

        if len(slides) >= 2:
            comparison_items = [
                {
                    "title": s.get("title", f"Topic {idx + 1}"),
                    "content": "\n".join(s.get("key_points", [])[:3])
                    or (s.get("description", "")[:200]),
                }
                for idx, s in enumerate(slides[:3])
            ]
            ppt.add_comparison_slide("Presentation Flow", comparison_items)
        
        # Add summary slide
        summary_points = [
            slide.get('title', f'Point {i+1}')
            for i, slide in enumerate(slides[:5])  
        ]
        ppt.add_summary_slide(summary_points)
        
        # Save presentation
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"slidesmith_{timestamp}.pptx"
        filepath = ppt.save(filename)
        
        print(f"DEBUG: PPTX saved to {filepath}")
        state['pptx_path'] = filepath
        state['generated_at'] = datetime.now().isoformat()
        state['status'] = 'completed'
        
        # Store slides in state for frontend
        state['slides'] = slides
        
        return state
        
    except Exception as e:
        print(f"ERROR in generate_ppt_node: {str(e)}")
        import traceback
        traceback.print_exc()
        state['status'] = 'ppt_error'
        state['error'] = str(e)
        return state

def validate_pptx_node(state: PresentationState) -> PresentationState:
    """
    Validate that PPTX was created successfully
    """
    try:
        import os
        
        pptx_path = state.get('pptx_path')
        print(f"DEBUG: Validating PPTX at path: {pptx_path}")
        
        if pptx_path and os.path.exists(pptx_path):
            file_size = os.path.getsize(pptx_path)
            print(f"DEBUG: PPTX file exists, size: {file_size} bytes")
            state['status'] = 'validated'
            state['file_size'] = file_size
            return state
        else:
            print(f"ERROR: PPTX file not found at {pptx_path}")
            state['status'] = 'validation_failed'
            state['error'] = f"File not found at {pptx_path}"
            return state
            
    except Exception as e:
        print(f"ERROR in validate_pptx_node: {str(e)}")
        state['status'] = 'validation_error'
        state['error'] = str(e)
        return state
