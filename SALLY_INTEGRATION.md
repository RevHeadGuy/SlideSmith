# 🎤 Sally AI Integration Guide

## Overview
Sally AI is now fully integrated into Presenton MVP! The frontend can call Sally endpoints to explain slides, generate speaker notes, refine content, and chat about topics.

---

## 🔧 Backend Setup (DONE!)

### Sally Endpoints Added to `main.py`:

```
POST   /ai/explain-slide        → Get clear slide explanation
POST   /ai/speaker-notes        → Generate speaker notes
POST   /ai/refine-slide         → Improve slide content
POST   /ai/chat                 → Chat with Sally
POST   /ai/explain-with-notes   → Get both explanation + notes
GET    /ai/health               → Check if Sally is available
```

### Request/Response Format:

**Request:**
```json
{
  "slide_text": "Machine Learning: Training algorithms on data"
}
```

**Response:**
```json
{
  "response": "Machine Learning is a subfield of artificial intelligence..."
}
```

---

## 📱 Frontend Integration (DONE!)

### File Created: `frontend/src/services/sallyIntegration.js`

This file includes:
1. **`sallyAPI` Service** - Reusable functions to call each endpoint
2. **React Components** - Ready-to-use UI components:
   - `SlideExplainerButton` - Simple explanation button
   - `SallySidebar` - Full panel with tabs
   - `SallyChatWidget` - Chat interface
   - `SallyQuickActions` - Quick action buttons

---

## 🚀 Quick Start

### 1. Import the Service in Your Component
```javascript
import { sallyAPI } from "../services/sallyIntegration";
```

### 2. Call Sally Functions
```javascript
// Explain a slide
const explanation = await sallyAPI.explainSlide("Slide content here");

// Generate speaker notes
const notes = await sallyAPI.generateSpeakerNotes("Slide content here");

// Get both at once
const { explanation, speaker_notes } = await sallyAPI.explainWithNotes("Slide content");

// Chat with Sally
const response = await sallyAPI.chat("What is AI?", "slide content");

// Check if Sally is available
const available = await sallyAPI.checkHealth();
```

### 3. Use Pre-Built Components
```javascript
import { SallySidebar, SallyChatWidget } from "../services/sallyIntegration";

function MySlideEditor() {
  return (
    <div>
      <div className="slide-content">
        {/* Your slide */}
      </div>
      <SallySidebar 
        slideTitle="My Slide"
        slideContent="Slide text here"
      />
      <SallyChatWidget slideContent="Slide text here" />
    </div>
  );
}
```

---

## 🎯 Feature Breakdown

### 1. **Explain Slide** 🎤
- **Purpose**: Get Sally to explain slide content clearly
- **Input**: Slide text
- **Output**: Clear, natural explanation (3-5 lines with bullet points)
- **Use Case**: Help audience understand the slide

### 2. **Speaker Notes** 📝
- **Purpose**: Generate natural speaker notes
- **Input**: Slide text
- **Output**: 4-6 lines of conversational notes
- **Use Case**: Help presenter remember what to say

### 3. **Refine Slide** ✍️
- **Purpose**: Improve slide clarity and engagement
- **Input**: Original slide content
- **Output**: Improved version (clearer, more concise, engaging)
- **Use Case**: Make slides better automatically

### 4. **Chat with Sally** 💬
- **Purpose**: Ask Sally questions about slides or topics
- **Input**: Question + optional slide context
- **Output**: Helpful answer
- **Use Case**: Audience Q&A, clarification, deep dives

### 5. **Explain with Notes** 🎁
- **Purpose**: Get both explanation and speaker notes
- **Input**: Slide text
- **Output**: Both explanation AND speaker notes
- **Use Case**: Complete slide preparation in one call

---

## ⚙️ Configuration

### Ollama Running?
Sally requires Ollama service to be running:

```bash
# Start Ollama (terminal 1)
ollama serve

# Then run FastAPI backend (terminal 2)
cd backend
python main.py

# Frontend can now call Sally endpoints
```

### Check Sally Health
```javascript
const isAvailable = await sallyAPI.checkHealth();
if (!isAvailable) {
  console.warn("Sally is offline - start Ollama");
}
```

---

## 📊 API Request Examples

### cURL Examples:
```bash
# Explain a slide
curl -X POST http://localhost:8000/ai/explain-slide \
  -H "Content-Type: application/json" \
  -d '{"slide_text":"Machine Learning basics"}'

# Generate speaker notes
curl -X POST http://localhost:8000/ai/speaker-notes \
  -H "Content-Type: application/json" \
  -d '{"slide_text":"Your slide content"}'

# Check health
curl http://localhost:8000/ai/health
```

---

## 🎨 UI/UX Recommendations

### Placement Ideas:
1. **Right Sidebar** - Shows explanation + speaker notes in tabs
2. **Bottom Panel** - Chat interface for Q&A during presentation
3. **Floating Button** - Quick "Refine Slide" action
4. **Presenter View** - Show speaker notes and chat in presenter mode

### Load States:
- Show "Loading..." while waiting for Sally
- Disable buttons during API calls
- Show error messages if Sally is offline

### Visual Cues:
- 🎤 icon for explanation
- 📝 icon for speaker notes
- ✍️ icon for refine
- 💬 icon for chat

---

## 🔌 Integration Checklist

- [x] Backend: Sally agents setup
- [x] Backend: FastAPI endpoints added
- [x] Backend: CORS enabled (localhost:3000, localhost:5173)
- [x] Frontend: Integration service created
- [x] Frontend: React components provided
- [ ] Frontend: Add to your slide editor UI
- [ ] Frontend: Style components to match your design
- [ ] Frontend: Test all features
- [ ] Frontend: Deploy!

---

## 🎭 Next Steps

1. **Import the service** in your React components
2. **Use the pre-built components** or create your own using `sallyAPI`
3. **Test each endpoint** to make sure they work
4. **Style the components** to match your UI
5. **Add loading/error states** for better UX
6. **Deploy** to production (make sure Ollama is running!)

---

## 💡 Tips & Tricks

### Performance:
- Cache Sally responses to avoid re-generating
- Use `explain_with_notes()` instead of 2 separate calls
- Check `health` endpoint on app start

### User Experience:
- Show "Sally is thinking..." while waiting
- Let users refine results (ask follow-up questions)
- Provide fallback content if Sally is offline

### Error Handling:
```javascript
try {
  const result = await sallyAPI.explainSlide(content);
} catch (error) {
  console.error("Sally error:", error);
  // Show offline message or fallback UI
}
```

---

## 📞 Support
If Sally is not responding:
1. Check if Ollama is running: `ollama serve`
2. Check backend is running: `python main.py`
3. Check CORS settings in main.py
4. Check browser console for network errors
5. Try `/ai/health` endpoint

---

**Sally is ready to make your presentations amazing! 🎉**
