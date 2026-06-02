import React, { useState } from "react";
import { SallySidebar } from "./services/sallyIntegration";
import AudienceQA from "./AudienceQA";
import EmailShareModal from "./EmailShareModal";
import "./SlideViewer.css";

function SlideViewer({
  slides,
  onClose,
  presentationTitle,
  pptxPath,
  onDownload,
  language = "english",
  onNotify,
}) {
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [isSallyOpen, setIsSallyOpen] = useState(false);
  const [isQAOpen, setIsQAOpen] = useState(false);
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);

  if (!slides || slides.length === 0) {
    return <div className="error">No slides to display</div>;
  }

  const notify = (message, type = "info") => {
    if (onNotify) onNotify(message, type);
  };

  const handleExportPPT = () => {
    if (pptxPath && onDownload) {
      onDownload(pptxPath);
    } else {
      notify("PPTX file not available", "error");
    }
  };

  const currentSlide = slides[currentSlideIndex];

  const nextSlide = () => {
    if (currentSlideIndex < slides.length - 1) {
      setCurrentSlideIndex(currentSlideIndex + 1);
    }
  };

  const prevSlide = () => {
    if (currentSlideIndex > 0) {
      setCurrentSlideIndex(currentSlideIndex - 1);
    }
  };

  const goToSlide = (index) => {
    setCurrentSlideIndex(index);
  };

  const slideContent = `${currentSlide.title}\n\n${currentSlide.description}\n\nKey Points:\n${
    currentSlide.key_points ? currentSlide.key_points.join("\n") : ""
  }`;

  return (
    <div className="slide-viewer-container">
      <div className="viewer-header">
        <h2>{presentationTitle}</h2>
        <div className="header-actions">
          <button
            type="button"
            className="share-email-btn"
            onClick={() => setIsEmailModalOpen(true)}
            title="Share presentation via email"
          >
            📧 Share
          </button>
          <button
            type="button"
            className="export-btn"
            onClick={handleExportPPT}
            title="Download presentation as PPTX"
          >
            📥 Export PPT
          </button>
          <button className="close-btn" onClick={onClose}>
            ✕
          </button>
        </div>
      </div>

      <div className="viewer-content">
        <div className={`main-slide-area ${isSallyOpen ? "with-sally" : ""}`}>
          <div className="slide-display">
            <div className="slide-number">{currentSlideIndex + 1}</div>

            <div className="slide-inner">
              <h1 className="slide-title">{currentSlide.title}</h1>

              <div className="slide-description">{currentSlide.description}</div>

              {currentSlide.key_points && currentSlide.key_points.length > 0 && (
                <div className="slide-key-points">
                  <h3>Key Points:</h3>
                  <ul>
                    {currentSlide.key_points.map((point, idx) => (
                      <li key={idx}>{point}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Images are embedded in the PPTX — not shown in web viewer */}
          </div>

          <div className="slide-navigation">
            {/* Left: Previous */}
            <button
              className="nav-btn"
              onClick={prevSlide}
              disabled={currentSlideIndex === 0}
            >
              ← Previous
            </button>

            <span className="slide-counter">
              Slide {currentSlideIndex + 1} of {slides.length}
            </span>

            {/* Right: Ask Sally + Audience Q&A + Next */}
            <div className="nav-right">
              <button
                className={`sally-toggle ${isSallyOpen ? "active" : ""}`}
                onClick={() => setIsSallyOpen(!isSallyOpen)}
                title="Ask Sally about this slide"
              >
                🎤 {isSallyOpen ? "Hide Sally" : "Ask Sally"}
              </button>

              <button
                className={`qa-toggle ${isQAOpen ? "active" : ""}`}
                onClick={() => setIsQAOpen(!isQAOpen)}
                title="Audience Q&A with Sally"
              >
                ❓ {isQAOpen ? "Hide Q&A" : "Audience Q&A"}
              </button>

              <button
                className="nav-btn"
                onClick={nextSlide}
                disabled={currentSlideIndex === slides.length - 1}
              >
                Next →
              </button>
            </div>
          </div>
        </div>

        {isSallyOpen && (
          <div className="sally-sidebar-wrapper">
            <SallySidebar
              slideTitle={currentSlide.title}
              slideContent={slideContent}
              language={language}
            />
          </div>
        )}

        {isQAOpen && (
          <div className="qa-sidebar-wrapper">
            <AudienceQA
              slides={slides}
              presentationTitle={presentationTitle}
              language={language}
            />
          </div>
        )}
      </div>

      <div className="slide-thumbnails">
        <h4>Slides</h4>
        <div className="thumbnails-scroll">
          {slides.map((slide, idx) => (
            <div
              key={idx}
              className={`thumbnail ${idx === currentSlideIndex ? "active" : ""}`}
              onClick={() => goToSlide(idx)}
              title={slide.title}
            >
              <div className="thumb-number">{idx + 1}</div>
              <div className="thumb-title">{slide.title}</div>
            </div>
          ))}
        </div>
      </div>

      <EmailShareModal
        isOpen={isEmailModalOpen}
        onClose={() => setIsEmailModalOpen(false)}
        pptxPath={pptxPath}
        presentationTitle={presentationTitle}
      />
    </div>
  );
}

export default SlideViewer;
