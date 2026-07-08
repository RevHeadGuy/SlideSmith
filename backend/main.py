from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
import os
from pathlib import Path
from datetime import datetime
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    validate_password_strength,
)
from models import User, Presentation
from schemas import UserCreate
from db import engine, Base, AsyncSessionLocal


load_dotenv()

# Import database components
from db import engine, get_db, init_db, close_db, Base
from models import Presentation, PresentationStatus

from outline_node import generate_outline_node, enrich_outline_node, PresentationState
from ppt_node import generate_ppt_node, validate_pptx_node
from pdf_extraction_node import extract_pdf_node, generate_outline_from_pdf, extract_pptx_node, generate_outline_from_pptx
from image_node import fetch_images_node, calculate_image_positions

# Import Sally AI agent
from agent_sally import AgentSally

# Initialize FastAPI app
app = FastAPI(title="SlideSmith API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Build LangGraph workflow
workflow = StateGraph(PresentationState)
workflow.add_node("extract_pdf", extract_pdf_node)
workflow.add_node("extract_pptx", extract_pptx_node)
workflow.add_node("outline", generate_outline_node)
workflow.add_node("outline_from_pdf", generate_outline_from_pdf)
workflow.add_node("outline_from_pptx", generate_outline_from_pptx)
workflow.add_node("enrich", enrich_outline_node)
workflow.add_node("fetch_images", fetch_images_node)
workflow.add_node("ppt", generate_ppt_node)
workflow.add_node("validate", validate_pptx_node)

workflow.set_entry_point("outline")

from fastapi import Depends
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="login"
)

from auth import verify_token

@app.get("/me")
async def get_me(
    token: str = Depends(oauth2_scheme)
):

    user_id = verify_token(token)

    return {
        "user_id": user_id
    }

# Conditional routing from outline
def route_from_outline(state: PresentationState):
    """Route based on whether file was uploaded, its type, or outline is pre-approved."""
    # If outline already injected (pre-approved), skip straight to fetch_images
    if (
        isinstance(state.get("content"), dict)
        and "slides" in state["content"]
        and len(state["content"]["slides"]) > 0
        and not state.get("pdf_path")
    ):
        return "fetch_images"
    if state.get('pdf_path'):
        file_type = state.get('file_type', 'pdf')
        if file_type == 'pptx':
            return "extract_pptx"
        else:
            return "extract_pdf"
    return "fetch_images"

workflow.add_conditional_edges("outline", route_from_outline)
# PDF path: extract_pdf → outline_from_pdf → fetch_images → ppt → validate
workflow.add_edge("extract_pdf", "outline_from_pdf")
workflow.add_edge("outline_from_pdf", "fetch_images")
# PPTX path: extract_pptx → outline_from_pptx → fetch_images → ppt → validate
workflow.add_edge("extract_pptx", "outline_from_pptx")
workflow.add_edge("outline_from_pptx", "fetch_images")
# Topic path: outline → fetch_images → ppt → validate (enrich removed — outline prompt already includes descriptions)
workflow.add_edge("fetch_images", "ppt")
workflow.add_edge("ppt", "validate")
workflow.add_edge("validate", END)

graph = workflow.compile()

# Pydantic models
class OutlineSlide(BaseModel):
    slide_number: int
    title: str
    description: Optional[str] = ""
    key_points: Optional[list] = []

class OutlinePreviewResponse(BaseModel):
    title: str
    slides: list
    topic: str

class PresentationResponse(BaseModel):
    id: str
    topic: str
    status: str
    pptx_path: Optional[str] = None
    generated_at: Optional[str] = None
    error: Optional[str] = None
    slides: Optional[list] = None

# Sally AI Models
class SallyRequest(BaseModel):
    slide_text: str
    language: Optional[str] = "english"
    
class SallyChatRequest(BaseModel):
    user_query: str
    slide_text: Optional[str] = None
    language: Optional[str] = "english"

class AudienceQARequest(BaseModel):
    question: str
    presentation_context: str
    language: Optional[str] = "english"
    
class SallyResponse(BaseModel):
    response: str
    
class SallyExplainWithNotesResponse(BaseModel):
    explanation: str
    speaker_notes: str

# Email Sharing Models
class EmailShareRequest(BaseModel):
    pptx_path: str
    recipient_emails: list[str]
    sender_email: Optional[str] = None
    subject: Optional[str] = "Check out this presentation from SlideSmith!"
    message: Optional[str] = None
    presentation_title: Optional[str] = "Presentation"

class EmailShareResponse(BaseModel):
    status: str
    message: str
    sent_to: int

@app.on_event("startup")
async def startup():
    """Initialize database tables on startup"""
    await init_db()
    print("✓ Database initialized")

@app.on_event("shutdown")
async def shutdown():
    """Close database connections on shutdown"""
    await close_db()
    print("✓ Database closed")

@app.get("/")
async def root():
    return {"message": "SlideSmith API running", "version": "1.0.0"}

@app.post("/generate-outline", response_model=OutlinePreviewResponse)
async def generate_outline_preview(
    slide_count: int = Form(10),
    language: str = Form("english"),
    topic: Optional[str] = Form(None),
    token: str = Depends(oauth2_scheme),
):
    """
    Generate only the presentation outline (slide titles + key points).
    Returns quickly (~10s) so the user can review and edit before full generation.
    """
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    if not topic or not topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required for outline preview")

    initial_state: PresentationState = {
        "topic": topic.strip(),
        "slide_count": slide_count,
        "theme": "modern",
        "language": language,
        "content": [],
        "generated_at": "",
        "status": "processing",
        "pptx_path": None,
        "error": None,
        "pdf_content": None,
        "pdf_path": None,
        "image_urls": [],
        "image_slides": [],
        "image_keywords": [],
        "slides": [],
        "file_type": None,
    }

    # Run only the outline node — no images, no PPT
    # Use asyncio.to_thread to run blocking function without blocking event loop
    state = await asyncio.to_thread(generate_outline_node, initial_state)

    content = state.get("content", {})
    slides = content.get("slides", [])

    # If the outline node stored raw text, try to extract slides from it
    if not slides and content.get("status") == "raw" and content.get("outline"):
        import re as _re
        import json as _j
        raw = content["outline"]

        def _clean(t):
            return _re.sub(r',\s*([\]\}])', r'\1', t)

        def _extract_obj(t):
            s = t.find('{')
            if s == -1: return t
            depth = 0
            for i in range(s, len(t)):
                if t[i] == '{': depth += 1
                elif t[i] == '}':
                    depth -= 1
                    if depth == 0: return t[s:i+1]
            return t[s:]

        # Try JSON extraction first
        for candidate in (raw, _clean(raw), _extract_obj(raw), _clean(_extract_obj(raw))):
            try:
                parsed = _j.loads(candidate)
                if "slides" in parsed:
                    slides = parsed["slides"]
                    content = parsed
                    break
            except Exception:
                pass

        # Fall back to markdown parsing — extract slide titles from **Slide N:** patterns
        if not slides:
            extracted = []
            # Match patterns like "**Slide 1: Title**" or "* Title: ..." or "### Title"
            title_patterns = [
                _re.compile(r'\*\*Slide\s*\d+[:\.]?\s*(.+?)\*\*', _re.IGNORECASE),
                _re.compile(r'^#+\s*Slide\s*\d+[:\.]?\s*(.+)$', _re.MULTILINE),
                _re.compile(r'^\*\s*Title[:\s]+(.+)$', _re.MULTILINE),
                _re.compile(r'^(?:Slide\s*)?\d+[\.:\)]\s*\*{0,2}(.+?)\*{0,2}$', _re.MULTILINE),
            ]
            for pattern in title_patterns:
                matches = pattern.findall(raw)
                if len(matches) >= 2:
                    for idx, title in enumerate(matches[:slide_count]):
                        extracted.append({
                            "slide_number": idx + 1,
                            "title": title.strip().strip('*').strip(),
                            "description": "",
                            "key_points": []
                        })
                    break

            if extracted:
                slides = extracted
                content = {"title": topic, "slides": slides}

    if not slides:
        raise HTTPException(status_code=500, detail="Failed to generate outline. Please try again.")

    return OutlinePreviewResponse(
        title=content.get("title", topic),
        slides=slides,
        topic=topic,
    )


@app.post("/generate", response_model=PresentationResponse)
async def generate_presentation(
    slide_count: int = Form(10),
    theme: str = Form("modern"),
    language: str = Form("english"),
    topic: Optional[str] = Form(None),
    outline_json: Optional[str] = Form(None),  # pre-approved outline from preview step
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    user_id = int(verify_token(token))
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    print("CURRENT USER:", user_id)

    """Generate presentation from topic, PDF, or PPTX using LangGraph"""
    presentation = None
    try:
        pdf_path = None
        file_type = None
        
        print(f"DEBUG: Received request - topic: {topic}, file: {file}")
        print(f"DEBUG: slide_count: {slide_count}, theme: {theme}")
        
        # Handle file upload (PDF or PPTX)
        if file is not None:
            print(f"DEBUG: Processing file: {file.filename}, content_type: {file.content_type}")
            
            is_pdf = file.content_type == "application/pdf" or file.filename.lower().endswith(".pdf")
            is_pptx = (
                file.content_type in ["application/vnd.openxmlformats-officedocument.presentationml.presentation", 
                                     "application/vnd.ms-powerpoint"] or
                file.filename.lower().endswith(".pptx") or 
                file.filename.lower().endswith(".ppt")
            )
            
            if not (is_pdf or is_pptx):
                raise HTTPException(status_code=400, detail="Only PDF and PPT/PPTX files are allowed")
            
            file_type = "pdf" if is_pdf else "pptx"
            
            uploads_dir = Path("uploads")
            uploads_dir.mkdir(exist_ok=True)
            
            # Create unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_path = str(uploads_dir / f"{timestamp}_{file.filename}")
            
            with open(pdf_path, "wb") as f:
                f.write(await file.read())
            
            print(f"DEBUG: {file_type.upper()} saved to {pdf_path}")
        
        # Validate that either topic or file is provided
        if not topic and not pdf_path:
            raise HTTPException(status_code=400, detail="Either topic or PDF/PPT file must be provided")
        
        initial_state: PresentationState = {
            "topic": topic or (f"{file_type.upper()} Document" if file_type else ""),
            "slide_count": slide_count,
            "theme": theme,
            "language": language,
            "content": [],
            "generated_at": "",
            "status": "processing",
            "pptx_path": None,
            "error": None,
            "pdf_content": None,
            "pdf_path": pdf_path,
            "image_urls": [],
            "image_slides": [],
            "image_keywords": [],
            "slides": [],
            "file_type": file_type
        }

        # If a pre-approved outline was passed, inject it so the outline node is skipped
        if outline_json and not pdf_path:
            try:
                import json as _json
                parsed_outline = _json.loads(outline_json)
                if isinstance(parsed_outline, dict) and "slides" in parsed_outline:
                    initial_state["content"] = parsed_outline
                    initial_state["status"] = "outline_generated"
                    print(f"DEBUG: Using pre-approved outline with {len(parsed_outline['slides'])} slides")
            except Exception as e:
                print(f"DEBUG: Could not parse outline_json, will regenerate: {e}")

        presentation = Presentation(
            topic=initial_state['topic'],
            slide_count=slide_count,
            theme=theme,
            language=language,
            status=PresentationStatus.PROCESSING,
            file_type=file_type,
            pdf_path=pdf_path,
            user_id=user_id,
        )
        db.add(presentation)
        await db.commit()
        await db.refresh(presentation)
        
        print(f"\n=== Starting presentation generation ===")
        print(f"Topic: {initial_state['topic']}")
        print(f"File Type: {file_type}")
        print(f"PDF Path: {pdf_path}")
        print(f"Slides: {slide_count}")
        
        # Determine which path to take
        if pdf_path:
            print(f"DEBUG: Starting {file_type.upper()} extraction workflow")
        
        result = graph.invoke(initial_state)
        
        print(f"Final status: {result['status']}")
        
        # Extract slides and attach cached image paths for viewer/PDF export
        slides = result.get('slides', []) or []
        image_urls = result.get('image_urls') or []
        if slides and image_urls:
            total_with_extras = len(slides) + 2
            positions = calculate_image_positions(total_with_extras)
            for img_idx, slide_pos in enumerate(positions):
                content_idx = slide_pos - 1
                if img_idx < len(image_urls) and 0 <= content_idx < len(slides):
                    slides[content_idx] = {
                        **slides[content_idx],
                        "image_path": image_urls[img_idx],
                    }

        if presentation is not None:
            final_status = result.get('status', 'failed')
            if final_status in ("completed", "validated"):
                presentation.status = PresentationStatus.COMPLETED
            else:
                presentation.status = PresentationStatus.FAILED

            presentation.pptx_path = result.get('pptx_path')
            presentation.generated_at = datetime.now()
            presentation.error = result.get('error')
            presentation.slides_json = slides
            presentation.content_json = result.get('content')
            await db.commit()

        return PresentationResponse(
            id=str(presentation.id) if presentation is not None else "",
            topic=result['topic'],
            status=result['status'],
            pptx_path=result.get('pptx_path'),
            generated_at=result.get('generated_at'),
            error=result.get('error'),
            slides=slides
        )
    except HTTPException:
        raise
    except Exception as e:
        if presentation is not None:
            try:
                presentation.status = PresentationStatus.FAILED
                presentation.error = str(e)
                await db.commit()
            except Exception:
                pass
        print(f"ERROR in /generate endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/register")
async def register(user: UserCreate):
    # Fix 3: validate password strength before doing anything
    error = validate_password_strength(user.password)
    if error:
        raise HTTPException(status_code=400, detail=error)

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(User).where(
                User.email == user.email
            )
        )

        existing_user = result.scalar_one_or_none()

        if existing_user:

            raise HTTPException(
                status_code=400,
                detail="Email already exists"
            )

        new_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hash_password(
                user.password
            )
        )

        session.add(new_user)

        await session.commit()

        return {
            "message": "User registered"
        }

@app.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends()
):

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(User).where(
                User.email == form_data.username
            )
        )

        db_user = result.scalar_one_or_none()

        if not db_user:

            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        if not verify_password(
            form_data.password,
            db_user.hashed_password
        ):

            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        access_token = create_access_token({
            "sub": str(db_user.id)
        })

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    
@app.get("/my-presentations")
async def my_presentations(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    user_id = int(verify_token(token))
    result = await db.execute(
        select(Presentation).where(Presentation.user_id == user_id)
    )
    return result.scalars().all()


@app.delete("/presentations/{presentation_id}")
async def delete_presentation(
    presentation_id: int,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Delete a presentation owned by the current user."""
    user_id = int(verify_token(token))

    result = await db.execute(
        select(Presentation).where(
            Presentation.id == presentation_id,
            Presentation.user_id == user_id,
        )
    )
    presentation = result.scalar_one_or_none()

    if not presentation:
        raise HTTPException(status_code=404, detail="Presentation not found")

    # Delete the PPTX file from disk if it exists
    if presentation.pptx_path and os.path.exists(presentation.pptx_path):
        try:
            os.remove(presentation.pptx_path)
        except OSError as e:
            print(f"WARNING: Could not delete file {presentation.pptx_path}: {e}")

    await db.delete(presentation)
    await db.commit()

    return {"message": "Presentation deleted successfully", "id": presentation_id}


@app.get("/presentations/{presentation_id}")
async def get_presentation(
    presentation_id: int,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Get a single presentation — only accessible by its owner."""
    user_id = int(verify_token(token))

    result = await db.execute(
        select(Presentation).where(
            Presentation.id == presentation_id,
            Presentation.user_id == user_id,
        )
    )
    presentation = result.scalar_one_or_none()

    if not presentation:
        raise HTTPException(status_code=404, detail="Presentation not found")

    return presentation

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Handle PDF uploads for content extraction"""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    
    file_path = uploads_dir / file.filename
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    return {"status": "success", "filename": file.filename, "size": file.size}

@app.get("/image/{filename}")
async def serve_image(filename: str):
    """Serve cached images for the slide viewer."""
    from urllib.parse import unquote
    filename = unquote(filename)
    # Prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=403, detail="Invalid filename")
    image_path = Path("image_cache") / filename
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(image_path))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/download/{presentation_id}")
async def download_presentation(presentation_id: str):
    """Download generated presentation by ID"""
    file_path = f"presentations/{presentation_id}.pptx"
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=f"{presentation_id}.pptx")
    raise HTTPException(status_code=404, detail="Presentation not found")

@app.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """Download presentation by file path."""
    from urllib.parse import unquote

    decoded_path = unquote(file_path)

    if not decoded_path.endswith(".pptx"):
        raise HTTPException(status_code=400, detail="Only PPTX files can be downloaded")

    if ".." in decoded_path:
        raise HTTPException(status_code=403, detail="Invalid file path")

    if os.path.exists(decoded_path):
        filename = decoded_path.split("/")[-1]
        print(f"DEBUG: Downloading file from {decoded_path}")
        return FileResponse(path=decoded_path, filename=filename)

    raise HTTPException(status_code=404, detail=f"File not found: {decoded_path}")


# ============================================================================
# 🎤 SALLY AI PRESENTER ENDPOINTS
# ============================================================================

# Initialize Sally
sally = AgentSally()

@app.post("/ai/explain-slide", response_model=SallyResponse)
async def explain_slide(request: SallyRequest):
    """Get Sally to explain a slide clearly"""
    try:
        if not request.slide_text or not request.slide_text.strip():
            raise HTTPException(status_code=400, detail="Slide text is required")
        
        sally_agent = AgentSally(language=request.language)
        explanation = sally_agent.explain_slide(request.slide_text)
        return SallyResponse(response=explanation)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error explaining slide: {str(e)}")

@app.post("/ai/speaker-notes", response_model=SallyResponse)
async def get_speaker_notes(request: SallyRequest):
    """Generate speaker notes for a slide"""
    try:
        if not request.slide_text or not request.slide_text.strip():
            raise HTTPException(status_code=400, detail="Slide text is required")
        
        sally_agent = AgentSally(language=request.language)
        notes = sally_agent.generate_speaker_notes(request.slide_text)
        return SallyResponse(response=notes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating speaker notes: {str(e)}")

@app.post("/ai/refine-slide", response_model=SallyResponse)
async def refine_slide(request: SallyRequest):
    """Ask Sally to improve slide content"""
    try:
        if not request.slide_text or not request.slide_text.strip():
            raise HTTPException(status_code=400, detail="Slide text is required")
        
        sally_agent = AgentSally(language=request.language)
        improved = sally_agent.refine_slide(request.slide_text)
        return SallyResponse(response=improved)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refining slide: {str(e)}")

@app.post("/ai/chat", response_model=SallyResponse)
async def chat_with_sally(request: SallyChatRequest):
    """Chat with Sally about any topic (optionally about a slide)"""
    try:
        if not request.user_query or not request.user_query.strip():
            raise HTTPException(status_code=400, detail="Question is required")
        
        sally_agent = AgentSally(language=request.language)
        response = sally_agent.chat(request.user_query, request.slide_text)
        return SallyResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}")

@app.post("/ai/explain-with-notes", response_model=SallyExplainWithNotesResponse)
async def explain_with_notes(request: SallyRequest):
    """Get both explanation and speaker notes for a slide"""
    try:
        if not request.slide_text or not request.slide_text.strip():
            raise HTTPException(status_code=400, detail="Slide text is required")
        
        sally_agent = AgentSally(language=request.language)
        result = sally_agent.explain_with_notes(request.slide_text)
        return SallyExplainWithNotesResponse(
            explanation=result["explanation"],
            speaker_notes=result["speaker_notes"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating explanation and notes: {str(e)}")

@app.post("/ai/audience-qa", response_model=SallyResponse)
async def audience_qa(request: AudienceQARequest):
    """Answer audience questions based on presentation context"""
    try:
        if not request.question or not request.question.strip():
            raise HTTPException(status_code=400, detail="Question is required")
        
        if not request.presentation_context or not request.presentation_context.strip():
            raise HTTPException(status_code=400, detail="Presentation context is required")
        
        sally_agent = AgentSally(language=request.language)
        
        # Build context-aware prompt for Sally
        context_prompt = f"""Based on the following presentation content, answer the audience's question clearly and concisely.

PRESENTATION CONTENT:
{request.presentation_context}

AUDIENCE QUESTION: {request.question}

Provide a direct, informative answer based on the presentation. If the question is not related to the presentation, politely mention that."""
        
        answer = sally_agent.chat(request.question, request.presentation_context)
        return SallyResponse(response=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")

@app.get("/ai/health")
async def sally_health():
    """Check if Sally (Ollama) is available"""
    is_available = sally.is_ollama_available()
    return {
        "status": "available" if is_available else "unavailable",
        "message": "Sally is ready to help!" if is_available else "Ollama service is not reachable"
    }

@app.post("/share/email", response_model=EmailShareResponse)
async def share_presentation_via_email(request: EmailShareRequest):
    """
    Send presentation via email to one or more recipients
    Requires SMTP credentials in environment variables
    """
    try:
        # Get SMTP configuration from environment
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        sender_email = request.sender_email or os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("SENDER_PASSWORD")
        
        if not sender_email or not sender_password:
            raise HTTPException(
                status_code=400, 
                detail="Email credentials not configured. Set SENDER_EMAIL and SENDER_PASSWORD in .env"
            )
        
        # Verify PPTX file exists
        pptx_file = request.pptx_path
        if not os.path.exists(pptx_file):
            raise HTTPException(status_code=404, detail=f"Presentation file not found: {pptx_file}")
        
        # Prepare email message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["Subject"] = request.subject or f"{request.presentation_title} - Presentation from SlideSmith"
        
        # Email body
        email_body = request.message or f"""
Hello,

I'd like to share a presentation with you created using SlideSmith.

{request.presentation_title}

The presentation file is attached below.

Best regards,
Presenton
"""
        message.attach(MIMEText(email_body, "plain"))
        
        # Attach PPTX file
        try:
            with open(pptx_file, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            filename = os.path.basename(pptx_file)
            part.add_header("Content-Disposition", f"attachment; filename= {filename}")
            message.attach(part)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to attach file: {str(e)}")
        
        # Send emails
        sent_count = 0
        errors = []
        
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            
            for recipient in request.recipient_emails:
                try:
                    message["To"] = recipient
                    server.send_message(message)
                    sent_count += 1
                    print(f"DEBUG: Email sent to {recipient}")
                except Exception as e:
                    error_msg = f"Failed to send to {recipient}: {str(e)}"
                    errors.append(error_msg)
                    print(f"ERROR: {error_msg}")
            
            server.quit()
            
            return EmailShareResponse(
                status="success" if sent_count > 0 else "failed",
                message=f"Sent to {sent_count} recipient(s)" + (f". Errors: {', '.join(errors)}" if errors else ""),
                sent_to=sent_count
            )
            
        except smtplib.SMTPAuthenticationError:
            raise HTTPException(status_code=401, detail="Email authentication failed. Check your credentials.")
        except smtplib.SMTPException as e:
            raise HTTPException(status_code=500, detail=f"SMTP error: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in /share/email endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)