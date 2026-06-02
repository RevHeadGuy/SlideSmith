import React, { useState } from "react";
import { sallyAPI } from "./services/sallyIntegration";
import "./AudienceQA.css";

function AudienceQA({ slides, presentationTitle, language = "english" }) {
  const [questions, setQuestions] = useState([]);
  const [inputQuestion, setInputQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedIndex, setExpandedIndex] = useState(null);

  // Compile presentation context from all slides
  const getPresentationContext = () => {
    const slidesSummary = slides
      .map(
        (slide, idx) =>
          `Slide ${idx + 1}: ${slide.title}\n${slide.description}\nKey Points: ${
            slide.key_points ? slide.key_points.join(", ") : "N/A"
          }`
      )
      .join("\n\n");
    return `Presentation: "${presentationTitle}"\n\n${slidesSummary}`;
  };

  const handleAskQuestion = async () => {
    if (!inputQuestion.trim()) return;

    const newQuestion = {
      id: Date.now(),
      question: inputQuestion,
      answer: null,
      loading: true,
      timestamp: new Date().toLocaleTimeString(),
    };

    setQuestions([...questions, newQuestion]);
    setInputQuestion("");
    setLoading(true);

    try {
      const presentationContext = getPresentationContext();
      const response = await sallyAPI.audienceQA(
        inputQuestion,
        presentationContext,
        language
      );

      // Update the question with the answer
      setQuestions((prev) =>
        prev.map((q) =>
          q.id === newQuestion.id ? { ...q, answer: response, loading: false } : q
        )
      );
    } catch (error) {
      console.error("Error getting answer from Sally:", error);
      setQuestions((prev) =>
        prev.map((q) =>
          q.id === newQuestion.id
            ? {
                ...q,
                answer: "Sorry, I couldn't get an answer from Sally. Make sure Ollama is running.",
                loading: false,
              }
            : q
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey && !loading) {
      e.preventDefault();
      handleAskQuestion();
    }
  };

  return (
    <div className="audience-qa-container">
      <div className="qa-header">
        <h3>🎯 Audience Q&A</h3>
        <span className="qa-count">{questions.length} questions</span>
      </div>

      {/* Questions List */}
      <div className="qa-list">
        {questions.length === 0 ? (
          <div className="qa-empty">
            <p>No questions yet. Ask Sally anything about this presentation!</p>
          </div>
        ) : (
          questions.map((q, idx) => (
            <div key={q.id} className="qa-item">
              <div
                className="qa-question-header"
                onClick={() =>
                  setExpandedIndex(expandedIndex === idx ? null : idx)
                }
              >
                <div className="qa-question-text">
                  <strong>Q{idx + 1}:</strong> {q.question}
                </div>
                <div className="qa-timestamp">{q.timestamp}</div>
                <span className="qa-expand-icon">
                  {expandedIndex === idx ? "▼" : "▶"}
                </span>
              </div>

              {expandedIndex === idx && (
                <div className="qa-answer">
                  {q.loading ? (
                    <div className="qa-loading">
                      <span className="spinner"></span> Sally is thinking...
                    </div>
                  ) : (
                    <div className="qa-answer-text">
                      <strong>🎤 Sally:</strong> {q.answer}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Question Input */}
      <div className="qa-input-container">
        <textarea
          className="qa-input"
          placeholder="Ask a question about the presentation..."
          value={inputQuestion}
          onChange={(e) => setInputQuestion(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={loading}
          rows="3"
        />
        <button
          className="qa-submit-btn"
          onClick={handleAskQuestion}
          disabled={loading || !inputQuestion.trim()}
        >
          {loading ? "🤔 Waiting..." : "❓ Ask Sally"}
        </button>
      </div>

      {/* Info */}
      <div className="qa-info">
        <small>💡 Tip: Sally can answer questions about any part of the presentation</small>
      </div>
    </div>
  );
}

export default AudienceQA;
