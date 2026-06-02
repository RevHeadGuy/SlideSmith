"""
Language Translation and Multilingual Support Module
Uses Ollama/Llama3 for local translations
"""

import ollama

# Language mappings
LANGUAGE_NAMES = {
    "english": "English",
    "spanish": "Spanish",
    "french": "French",
    "german": "German",
    "italian": "Italian",
    "portuguese": "Portuguese",
    "chinese": "Chinese (Simplified)",
    "japanese": "Japanese",
    "korean": "Korean",
    "arabic": "Arabic",
    "hindi": "Hindi",
    "russian": "Russian",
    "dutch": "Dutch",
    "swedish": "Swedish",
    "turkish": "Turkish"
}

def translate_text(text: str, source_language: str = "english", target_language: str = "english") -> str:
    """
    Translate text from source language to target language using Llama3
    
    Args:
        text: Text to translate
        source_language: Source language (default: english)
        target_language: Target language (default: english)
    
    Returns:
        Translated text
    """
    if source_language == target_language:
        return text
    
    try:
        source_lang_name = LANGUAGE_NAMES.get(source_language, source_language.capitalize())
        target_lang_name = LANGUAGE_NAMES.get(target_language, target_language.capitalize())
        
        prompt = f"""Translate the following text from {source_lang_name} to {target_lang_name}.
Provide ONLY the translation, no additional explanation or commentary.

Text to translate:
{text}

Translation in {target_lang_name}:"""

        response = ollama.generate(
            model="llama3",
            prompt=prompt,
            stream=False
        )
        
        translated_text = response['response'].strip()
        print(f"DEBUG: Translated to {target_lang_name}")
        return translated_text
        
    except Exception as e:
        print(f"ERROR: Translation failed from {source_language} to {target_language}: {str(e)}")
        return text


def get_language_prompt_prefix(language: str) -> str:
    """
    Get language instruction prefix for LLM prompts
    """
    lang_name = LANGUAGE_NAMES.get(language, language.capitalize())
    return f"Provide your response in {lang_name}. "


def translate_slides(slides: list, target_language: str = "english") -> list:
    """
    Translate all slide content to target language
    
    Args:
        slides: List of slide dictionaries
        target_language: Target language for translation
    
    Returns:
        Slides with translated content
    """
    if target_language == "english":
        return slides
    
    translated_slides = []
    
    for slide in slides:
        translated_slide = slide.copy()
        
        # Translate title
        if "title" in translated_slide:
            translated_slide["title"] = translate_text(
                translated_slide["title"],
                source_language="english",
                target_language=target_language
            )
        
        # Translate description
        if "description" in translated_slide:
            translated_slide["description"] = translate_text(
                translated_slide["description"],
                source_language="english",
                target_language=target_language
            )
        
        # Translate key points
        if "key_points" in translated_slide and translated_slide["key_points"]:
            translated_slide["key_points"] = [
                translate_text(
                    point,
                    source_language="english",
                    target_language=target_language
                )
                for point in translated_slide["key_points"]
            ]
        
        translated_slides.append(translated_slide)
    
    return translated_slides


def get_multilingual_prompt(base_prompt: str, language: str = "english") -> str:
    """
    Enhance prompt with language instruction
    """
    if language == "english":
        return base_prompt
    
    lang_name = LANGUAGE_NAMES.get(language, language.capitalize())
    language_instruction = f"\n\nIMPORTANT: Provide ALL content in {lang_name}. Translate every part of your response to {lang_name}."
    
    return base_prompt + language_instruction
