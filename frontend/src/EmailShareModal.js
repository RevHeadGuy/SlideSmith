import React, { useState } from "react";
import axios from "axios";
import "./EmailShareModal.css";

function EmailShareModal({ isOpen, onClose, pptxPath, presentationTitle }) {
  const [emails, setEmails] = useState("");
  const [subject, setSubject] = useState(`${presentationTitle} - Presentation from SlideSmith`);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSendEmail = async () => {
    if (!emails.trim()) {
      setError("Please enter at least one email address");
      return;
    }

    // Parse comma-separated emails
    const emailList = emails
      .split(",")
      .map((e) => e.trim())
      .filter((e) => e.length > 0);

    // Simple email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const invalidEmails = emailList.filter((e) => !emailRegex.test(e));

    if (invalidEmails.length > 0) {
      setError(`Invalid email(s): ${invalidEmails.join(", ")}`);
      return;
    }

    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const response = await axios.post("http://localhost:8000/share/email", {
        pptx_path: pptxPath,
        recipient_emails: emailList,
        subject: subject || undefined,
        message: message || undefined,
        presentation_title: presentationTitle,
      });

      if (response.data.sent_to > 0) {
        setSuccess(
          `✅ Presentation sent to ${response.data.sent_to} recipient(s)!`
        );
        setTimeout(() => {
          setEmails("");
          setMessage("");
          setError("");
          onClose();
        }, 2000);
      } else {
        setError("Failed to send email. Please check your email configuration.");
      }
    } catch (err) {
      const errorMsg =
        err.response?.data?.detail || "Failed to send email. Please try again.";
      setError(errorMsg);
      console.error("Email send error:", err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="email-modal-overlay" onClick={onClose}>
      <div className="email-modal" onClick={(e) => e.stopPropagation()}>
        <div className="email-modal-header">
          <h2>📧 Share Presentation via Email</h2>
          <button className="email-modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="email-modal-content">
          <div className="email-form-group">
            <label>Recipient Email(s) *</label>
            <input
              type="text"
              placeholder="email1@example.com, email2@example.com"
              value={emails}
              onChange={(e) => setEmails(e.target.value)}
              disabled={loading}
              className="email-input"
            />
            <small>Separate multiple emails with commas</small>
          </div>

          <div className="email-form-group">
            <label>Subject</label>
            <input
              type="text"
              placeholder={`${presentationTitle} - Presentation from SlideSmith`}
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              disabled={loading}
              className="email-input"
            />
          </div>

          <div className="email-form-group">
            <label>Custom Message (Optional)</label>
            <textarea
              placeholder="Add a personal message to include with the presentation..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              disabled={loading}
              className="email-textarea"
              rows="4"
            />
          </div>

          {error && <div className="email-error">{error}</div>}
          {success && <div className="email-success">{success}</div>}

          <div className="email-modal-footer">
            <button
              className="email-cancel-btn"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              className="email-send-btn"
              onClick={handleSendEmail}
              disabled={loading}
            >
              {loading ? "Sending..." : "Send Email"}
            </button>
          </div>
        </div>

        <div className="email-modal-info">
          <small>
            ℹ️ Make sure your email credentials are configured in the backend
            .env file (SENDER_EMAIL, SENDER_PASSWORD)
          </small>
        </div>
      </div>
    </div>
  );
}

export default EmailShareModal;
