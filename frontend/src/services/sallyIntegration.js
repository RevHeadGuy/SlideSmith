/**
 * 🎤 Sally AI Integration - Frontend Guide
 * 
 * This file shows how to integrate Sally AI endpoints in your React frontend
 * Sally provides AI-powered slide assistance: explanations, speaker notes, content refinement
 */

import React from 'react';

// API SERVICE - Call Sally endpoints from the backend


const API_BASE = "http://localhost:8000";

// Service for Sally API calls
export const sallyAPI = {
  /**
   * Get Sally to explain a slide
   * @param {string} slideText - The slide content
   * @param {string} language - The language code (default: "english")
   * @returns {Promise<string>} - Sally's explanation
   */
  async explainSlide(slideText, language = "english") {
    try {
      const response = await fetch(`${API_BASE}/ai/explain-slide`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slide_text: slideText, language }),
      });
      
      if (!response.ok) throw new Error("Failed to explain slide");
      const data = await response.json();
      return data.response;
    } catch (error) {
      console.error("Error explaining slide:", error);
      throw error;
    }
  },

  /**
   * Generate speaker notes for a slide
   * @param {string} slideText - The slide content
   * @param {string} language - The language code (default: "english")
   * @returns {Promise<string>} - Speaker notes
   */
  async generateSpeakerNotes(slideText, language = "english") {
    try {
      const response = await fetch(`${API_BASE}/ai/speaker-notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slide_text: slideText, language }),
      });
      
      if (!response.ok) throw new Error("Failed to generate speaker notes");
      const data = await response.json();
      return data.response;
    } catch (error) {
      console.error("Error generating speaker notes:", error);
      throw error;
    }
  },

  /**
   * Ask Sally to improve slide content
   * @param {string} slideText - The original slide content
   * @param {string} language - The language code (default: "english")
   * @returns {Promise<string>} - Improved slide content
   */
  async refineSlide(slideText, language = "english") {
    try {
      const response = await fetch(`${API_BASE}/ai/refine-slide`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slide_text: slideText, language }),
      });
      
      if (!response.ok) throw new Error("Failed to refine slide");
      const data = await response.json();
      return data.response;
    } catch (error) {
      console.error("Error refining slide:", error);
      throw error;
    }
  },

  /**
   * Chat with Sally about a topic
   * @param {string} userQuery - Your question
   * @param {string} [slideText] - Optional: slide context
   * @param {string} language - The language code (default: "english")
   * @returns {Promise<string>} - Sally's response
   */
  async chat(userQuery, slideText = null, language = "english") {
    try {
      const response = await fetch(`${API_BASE}/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_query: userQuery,
          slide_text: slideText,
          language,
        }),
      });
      
      if (!response.ok) throw new Error("Chat failed");
      const data = await response.json();
      return data.response;
    } catch (error) {
      console.error("Error in chat:", error);
      throw error;
    }
  },

  /**
   * Get both explanation and speaker notes in one call
   * @param {string} slideText - The slide content
   * @param {string} language - The language code (default: "english")
   * @returns {Promise<{explanation: string, speaker_notes: string}>}
   */
  async explainWithNotes(slideText, language = "english") {
    try {
      const response = await fetch(`${API_BASE}/ai/explain-with-notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slide_text: slideText, language }),
      });
      
      if (!response.ok) throw new Error("Failed to generate explanation and notes");
      const data = await response.json();
      return {
        explanation: data.explanation,
        speaker_notes: data.speaker_notes,
      };
    } catch (error) {
      console.error("Error generating explanation and notes:", error);
      throw error;
    }
  },

  /**
   * Check if Sally (Ollama) is available
   * @returns {Promise<boolean>} - True if Sally is available
   */
  async checkHealth() {
    try {
      const response = await fetch(`${API_BASE}/ai/health`);
      const data = await response.json();
      return data.status === "available";
    } catch (error) {
      console.error("Error checking Sally health:", error);
      return false;
    }
  },

  /**
   * Answer audience questions based on presentation context
   * @param {string} question - The audience question
   * @param {string} presentationContext - Full presentation summary
   * @param {string} language - The language code (default: "english")
   * @returns {Promise<string>} - Sally's answer
   */
  async audienceQA(question, presentationContext, language = "english") {
    try {
      const response = await fetch(`${API_BASE}/ai/audience-qa`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          presentation_context: presentationContext,
          language,
        }),
      });

      if (!response.ok) throw new Error("Failed to get answer from Sally");
      const data = await response.json();
      return data.response;
    } catch (error) {
      console.error("Error getting audience Q&A response:", error);
      throw error;
    }
  },
};

// REACT COMPONENT EXAMPLES


/**
 * Example 1: Simple Explanation Button
 */
export function SlideExplainerButton({ slideContent }) {
  const [explanation, setExplanation] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  const handleExplain = async () => {
    setLoading(true);
    try {
      const result = await sallyAPI.explainSlide(slideContent);
      setExplanation(result);
    } catch (error) {
      alert("Error: Could not get explanation from Sally");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button onClick={handleExplain} disabled={loading}>
        {loading ? "Getting explanation..." : "🎤 Explain This Slide"}
      </button>
      {explanation && (
        <div className="explanation-box">
          <h3>Sally's Explanation</h3>
          <p>{explanation}</p>
        </div>
      )}
    </div>
  );
}

/**
 * Example 2: Complete Slide Companion Panel
 */
export function SallySidebar({ slideTitle, slideContent, language = "english" }) {
  const [activeTab, setActiveTab] = React.useState("explanation");
  const [explanation, setExplanation] = React.useState("");
  const [speakerNotes, setSpeakerNotes] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [sallyAvailable, setSallyAvailable] = React.useState(true);

  React.useEffect(() => {
    // Check if Sally is available when component mounts
    sallyAPI.checkHealth().then(setSallyAvailable);
  }, []);

  const handleGenerateAll = async () => {
    setLoading(true);
    try {
      const result = await sallyAPI.explainWithNotes(slideContent, language);
      setExplanation(result.explanation);
      setSpeakerNotes(result.speaker_notes);
      setActiveTab("explanation");
    } catch (error) {
      alert("Error: Could not generate content from Sally");
    } finally {
      setLoading(false);
    }
  };

  if (!sallyAvailable) {
    return (
      <div className="sally-panel">
        <p>⚠️ Sally is offline. Start Ollama to use AI features.</p>
      </div>
    );
  }

  return (
    <div className="sally-sidebar">
      <h2>🎤 Sally AI Presenter</h2>
      <p>Slide: {slideTitle}</p>

      <button onClick={handleGenerateAll} disabled={loading}>
        {loading ? "Generating..." : "Generate All"}
      </button>

      <div className="tabs">
        <button
          onClick={() => setActiveTab("explanation")}
          className={activeTab === "explanation" ? "active" : ""}
        >
          Explanation
        </button>
        <button
          onClick={() => setActiveTab("notes")}
          className={activeTab === "notes" ? "active" : ""}
        >
          Speaker Notes
        </button>
      </div>

      <div className="tab-content" style={{ flex: 1, overflowY: 'auto', padding: '12px', fontSize: '14px', lineHeight: '1.6' }}>
        {activeTab === "explanation" && (
          <div>{explanation || "Generate to see explanation"}</div>
        )}
        {activeTab === "notes" && (
          <div>{speakerNotes || "Generate to see speaker notes"}</div>
        )}
      </div>
    </div>
  );
}

/**
 * Example 3: Chat Interface
 */
export function SallyChatWidget({ slideContent, language = "english" }) {
  const [messages, setMessages] = React.useState([]);
  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    // Add user message to chat
    setMessages([...messages, { role: "user", content: input }]);
    setInput("");
    setLoading(true);

    try {
      const response = await sallyAPI.chat(input, slideContent, language);
      setMessages((prev) => [...prev, { role: "sally", content: response }]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "system", content: "Error: Could not get response from Sally" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="sally-chat">
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <strong>{msg.role === "sally" ? "🎤 Sally:" : "You:"}</strong>
            <p>{msg.content}</p>
          </div>
        ))}
      </div>
      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
          placeholder="Ask Sally a question..."
          disabled={loading}
        />
        <button onClick={handleSendMessage} disabled={loading}>
          Send
        </button>
      </div>
    </div>
  );
}

/**
 * Example 4: Quick Action Buttons
 */
export function SallyQuickActions({ slideContent, onRefineClick }) {
  const [loading, setLoading] = React.useState(false);

  const handleRefine = async () => {
    setLoading(true);
    try {
      const improved = await sallyAPI.refineSlide(slideContent);
      onRefineClick(improved);
    } catch (error) {
      alert("Error refining slide");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="quick-actions">
      <button 
        onClick={handleRefine} 
        disabled={loading}
        className="action-btn"
      >
        ✍️ {loading ? "Improving..." : "Improve Content"}
      </button>
    </div>
  );
}

// ============================================================================
// USAGE IN YOUR APP
// ============================================================================

/*
Example integration in your main slide editor:

import { SlideExplainerButton, SallySidebar, SallyChatWidget } from "./sally-integration";

function SlideEditor() {
  const [currentSlide, setCurrentSlide] = React.useState({
    title: "Machine Learning",
    content: "Training algorithms on data..."
  });

  return (
    <div className="slide-editor">
      <div className="main-content">
        <h1>{currentSlide.title}</h1>
        <p>{currentSlide.content}</p>
      </div>
      
      <div className="sidebar">
        <SallySidebar 
          slideTitle={currentSlide.title}
          slideContent={currentSlide.content}
        />
        
        <SallyChatWidget slideContent={currentSlide.content} />
      </div>
    </div>
  );
}
*/
