import requests
from typing import Optional
from language_utils import LANGUAGE_NAMES


SALLY_PERSONA = """
You are Sally, a confident and engaging AI presenter.

Your behavior:
- Explain slides like a human presenter
- Keep explanations clear, structured, and concise
- Use simple language
- Sound natural and friendly (not robotic)
- When helpful, use bullet points

Always focus on making content easy to understand.
"""


class AgentSally:
    """
    Sally - An AI presenter agent for explaining slides and generating speaker notes.
    Uses Ollama's Llama3 model for natural, conversational explanations.
    Supports multilingual interaction.
    """
    
    def __init__(self, model: str = "llama3", ollama_url: str = "http://localhost:11434", language: str = "english"):
        """
        Initialize Sally agent.
        
        Args:
            model: Ollama model to use (default: "llama3")
            ollama_url: Base URL for Ollama API (default: "http://localhost:11434")
            language: Language for Sally's responses (default: "english")
        """
        self.model = model
        self.url = f"{ollama_url}/api/generate"
        self.timeout = 120  # Increased to 120 seconds for better reliability
        self.language = language
        self.lang_name = LANGUAGE_NAMES.get(language, language.capitalize())

    def _call_ollama(self, prompt: str, timeout: Optional[int] = None) -> str:
        """
        Internal method to call Ollama API.
        
        Args:
            prompt: The prompt to send to Ollama
            timeout: Optional custom timeout (uses default if not specified)
            
        Returns:
            Response text from Ollama, or error message if request fails
        """
        request_timeout = timeout or self.timeout
        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=request_timeout
            )

            response.raise_for_status()
            data = response.json()

            return data.get("response", "").strip()

        except requests.exceptions.Timeout:
            return f"[Sally Error] Request timed out after {request_timeout} seconds. Try again or ask a simpler question."
        except requests.exceptions.ConnectionError as e:
            return f"[Sally Error] Cannot connect to Ollama. Make sure it's running on {self.url}: {str(e)}"
        except requests.exceptions.RequestException as e:
            return f"[Sally Error] Unable to connect to Ollama: {str(e)}"
        except (KeyError, ValueError) as e:
            return f"[Sally Error] Invalid response from Ollama: {str(e)}"

    def _get_language_instruction(self) -> str:
        """Get language instruction for prompts"""
        if self.language.lower() == "english":
            return ""
        return f"\nIMPORTANT: Respond entirely in {self.lang_name}. Do not use English."

    # 🎤 1. Explain Slide
    def explain_slide(self, slide_text: str) -> str:
        """
        Generate a clear explanation of slide content.
        
        Args:
            slide_text: The content/text of the slide
            
        Returns:
            Natural language explanation of the slide
        """
        if not slide_text or not slide_text.strip():
            return "[Sally] Please provide slide content to explain."
            
        lang_instruction = self._get_language_instruction()
        
        prompt = f"""
{SALLY_PERSONA}

Explain the following slide clearly.

Slide Content:
{slide_text}

Format:
- Short explanation (3–5 lines)
- Use bullet points if helpful{lang_instruction}
"""
        return self._call_ollama(prompt)

    # 💬 2. Chat with Sally
    def chat(self, user_query: str, slide_text: Optional[str] = None) -> str:
        """
        Have a conversation with Sally about a question (optionally about a slide).
        
        Args:
            user_query: Question or topic to discuss
            slide_text: Optional slide content for context
            
        Returns:
            Sally's response to the query
        """
        if not user_query or not user_query.strip():
            return "[Sally] Please ask me a question!"
            
        context = f"\nSlide Content:\n{slide_text}" if slide_text else ""
        lang_instruction = self._get_language_instruction()

        prompt = f"""
{SALLY_PERSONA}

User Question:
{user_query}
{context}

Answer helpfully and clearly.{lang_instruction}
"""
        # Use longer timeout for large context (e.g., audience Q&A with full presentation)
        context_length = len(slide_text) if slide_text else 0
        custom_timeout = 180 if context_length > 1000 else self.timeout  # 180s for large context
        
        return self._call_ollama(prompt, timeout=custom_timeout)

    # ✍️ 3. Refine Slide Content
    def refine_slide(self, slide_text: str) -> str:
        """
        Improve slide content for clarity, engagement, and conciseness.
        
        Args:
            slide_text: The original slide content
            
        Returns:
            Improved version of the slide
        """
        if not slide_text or not slide_text.strip():
            return "[Sally] Please provide slide content to refine."
        
        lang_instruction = self._get_language_instruction()
            
        prompt = f"""
{SALLY_PERSONA}

Improve the following slide content.

Goals:
- Make it clearer
- Make it more engaging
- Keep it concise
- Use bullet points if needed{lang_instruction}

Original Slide:
{slide_text}
"""
        return self._call_ollama(prompt)

    # 🎯 4. Generate Speaker Notes
    def generate_speaker_notes(self, slide_text: str) -> str:
        """
        Generate natural speaker notes for presenting a slide.
        
        Args:
            slide_text: The slide content
            
        Returns:
            Speaker notes in natural, conversational style
        """
        if not slide_text or not slide_text.strip():
            return "[Sally] Please provide slide content for speaker notes."
        
        lang_instruction = self._get_language_instruction()
            
        prompt = f"""
{SALLY_PERSONA}

Generate speaker notes for this slide.

Slide:
{slide_text}

Format:
- Natural speaking style
- 4–6 lines
- Sounds like a real presenter{lang_instruction}
"""
        return self._call_ollama(prompt)

    # 🎯 5. Bonus: Complete presentation helper
    def explain_with_notes(self, slide_text: str) -> dict:
        """
        Generate both explanation and speaker notes for a slide.
        
        Args:
            slide_text: The slide content
            
        Returns:
            Dictionary with 'explanation' and 'speaker_notes' keys
        """
        if not slide_text or not slide_text.strip():
            return {
                "explanation": "[Sally] Please provide slide content.",
                "speaker_notes": "[Sally] Please provide slide content."
            }
            
        return {
            "explanation": self.explain_slide(slide_text),
            "speaker_notes": self.generate_speaker_notes(slide_text)
        }

    def is_ollama_available(self) -> bool:
        """
        Check if Ollama service is available.
        
        Returns:
            True if Ollama is reachable, False otherwise
        """
        try:
            response = requests.get(
                self.url.replace("/api/generate", ""),
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
