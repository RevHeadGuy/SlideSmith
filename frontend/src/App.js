import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import "./App.css";
import SlideViewer from "./SlideViewer";
function App() {
  const [input, setInput] = useState("");
  const [theme, setTheme] = useState("modern");
  const [language, setLanguage] = useState("english");
  const [slideCount, setSlideCount] = useState(10);
  const [loading, setLoading] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [stats, setStats] = useState({
    presentationsGenerated: 0,
    slidesCreated: 0,
    executionTime: 0,
  });
  const [recent, setRecent] = useState([]);
  const [myPresentations, setMyPresentations] = useState([]);
  const [myPresLoading, setMyPresLoading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [outlinePreview, setOutlinePreview] = useState(null);   // { title, slides, topic }
  const [outlineLoading, setOutlineLoading] = useState(false);
  const [editedSlides, setEditedSlides] = useState([]);          // user-editable copy
  const [uploadedFile, setUploadedFile] = useState(null);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [currentSlides, setCurrentSlides] = useState([]);
  const [currentTitle, setCurrentTitle] = useState("");
  const [currentPptxPath, setCurrentPptxPath] = useState("");
  const [authMode, setAuthMode] = useState("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authToken, setAuthToken] = useState(() => {
    // Fix 4: check expiry on load — auto-logout if token is expired
    const stored =
      localStorage.getItem("slidesmith_token") ||
      sessionStorage.getItem("slidesmith_token") ||
      "";
    if (stored) {
      try {
        const payload = JSON.parse(atob(stored.split(".")[1]));
        if (payload.exp && payload.exp * 1000 < Date.now()) {
          // Token expired — clear storage silently
          localStorage.removeItem("slidesmith_token");
          localStorage.removeItem("slidesmith_user");
          sessionStorage.removeItem("slidesmith_token");
          sessionStorage.removeItem("slidesmith_user");
          return "";
        }
      } catch (_) {
        // Malformed token — clear it
        localStorage.removeItem("slidesmith_token");
        sessionStorage.removeItem("slidesmith_token");
        return "";
      }
    }
    return stored;
  });
  const [userEmail, setUserEmail] = useState(
    localStorage.getItem("slidesmith_user") ||
    sessionStorage.getItem("slidesmith_user") ||
    ""
  );
  const [rememberMe, setRememberMe] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false); // resolved after expiry check below

  const addNotification = (message, type = "info") => {
    const id = Date.now();
    setNotifications((prev) => [...prev, { id, message, type }]);
  };

  const handleLogout = () => {
    localStorage.removeItem("slidesmith_token");
    localStorage.removeItem("slidesmith_user");
    sessionStorage.removeItem("slidesmith_token");
    sessionStorage.removeItem("slidesmith_user");
    setAuthToken("");
    setUserEmail("");
    setIsAuthenticated(false);
    setMyPresentations([]);
    addNotification("Logged out successfully", "success");
  };

  useEffect(() => {
    const savedStats = localStorage.getItem("slidesmith_stats");
    const savedRecent = localStorage.getItem("slidesmith_recent");
    if (savedStats) setStats(JSON.parse(savedStats));
    if (savedRecent) setRecent(JSON.parse(savedRecent));
  }, []);

  // Apply theme to document
  useEffect(() => {
    document.body.className = theme === "dark" ? "theme-dark" : "";
  }, [theme]);

  const fetchMyPresentations = useCallback(async () => {
    if (!authToken) return;
    setMyPresLoading(true);
    try {
      const res = await axios.get("http://localhost:8000/my-presentations");
      const sorted = [...(res.data || [])].sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      );
      setMyPresentations(sorted);
    } catch (err) {
      console.error("Failed to fetch presentations:", err);
    } finally {
      setMyPresLoading(false);
    }
  }, [authToken]);

  const deletePresentation = async (id) => {
    setDeletingId(id);
    try {
      await axios.delete(`http://localhost:8000/presentations/${id}`);
      setMyPresentations((prev) => prev.filter((p) => p.id !== id));
      addNotification("Presentation deleted", "success");
    } catch (err) {
      addNotification(
        err.response?.data?.detail || "Failed to delete presentation",
        "error"
      );
    } finally {
      setDeletingId(null);
      setConfirmDeleteId(null);
    }
  };

  useEffect(() => {
    if (authToken) {
      axios.defaults.headers.common.Authorization = `Bearer ${authToken}`;
      setIsAuthenticated(true);
      fetchMyPresentations();
    } else {
      delete axios.defaults.headers.common.Authorization;
      setIsAuthenticated(false);
    }
  }, [authToken, fetchMyPresentations]);

  useEffect(() => {
    if (notifications.length > 0) {
      const timer = setTimeout(() => {
        setNotifications((prev) => prev.slice(1));
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [notifications]);

  const handleAuthSubmit = async (event) => {
    event.preventDefault();
    if (authMode === "login") {
      if (!email || !password) {
        addNotification("Please enter email and password", "error");
        return;
      }
      try {
        const params = new URLSearchParams();
        params.append("username", email);
        params.append("password", password);

        const response = await axios.post(
          "http://localhost:8000/login",
          params,
          {
            headers: {
              "Content-Type": "application/x-www-form-urlencoded",
            },
          }
        );

        const token = response.data.access_token;
        // Remember me: localStorage persists, sessionStorage clears on tab close
        const storage = rememberMe ? localStorage : sessionStorage;
        storage.setItem("slidesmith_token", token);
        storage.setItem("slidesmith_user", email);
        setAuthToken(token);
        setUserEmail(email);
        setPassword("");
        addNotification("Login successful", "success");
      } catch (err) {
        console.error(err);
        addNotification(
          err.response?.data?.detail || "Login failed. Please check your credentials.",
          "error"
        );
      }
    } else {
      if (!username || !email || !password) {
        addNotification("Please enter username, email, and password", "error");
        return;
      }
      try {
        await axios.post("http://localhost:8000/register", {
          username,
          email,
          password,
        });

        addNotification("Registration successful. You can now log in.", "success");
        setAuthMode("login");
        setPassword("");
      } catch (err) {
        console.error(err);
        addNotification(
          err.response?.data?.detail || "Registration failed. Please try again.",
          "error"
        );
      }
    }
  };

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];
    if (file) {
      const isPDF = file.type === "application/pdf" || file.name.endsWith(".pdf");
      const isPPT = file.type === "application/vnd.openxmlformats-officedocument.presentationml.presentation" || 
                    file.type === "application/vnd.ms-powerpoint" ||
                    file.name.endsWith(".pptx") || 
                    file.name.endsWith(".ppt");
      
      if (isPDF || isPPT) {
        setUploadedFile(file);
        addNotification(`File uploaded: ${file.name}`, "success");
      } else {
        addNotification("Please upload a PDF/PPT file", "error");
      }
    }
  };

  const generatePPT = async (approvedOutline = null) => {
    if (!isAuthenticated) {
      addNotification("Please login before generating a presentation", "error");
      return;
    }

    if (!input.trim() && !uploadedFile) {
      addNotification("Please enter a presentation topic or upload a PDF/PPT file", "error");
      return;
    }

    // For topic-only (no file), show outline preview first unless already approved
    if (!uploadedFile && !approvedOutline) {
      setOutlineLoading(true);
      try {
        const fd = new FormData();
        fd.append("topic", input.trim());
        fd.append("slide_count", parseInt(slideCount));
        fd.append("language", language);
        const res = await axios.post("http://localhost:8000/generate-outline", fd);
        setOutlinePreview(res.data);
        setEditedSlides(res.data.slides.map((s) => ({ ...s })));
      } catch (err) {
        addNotification(
          err.response?.data?.detail || "Failed to generate outline. Please try again.",
          "error"
        );
      } finally {
        setOutlineLoading(false);
      }
      return; // wait for user approval
    }

    // Proceed to full generation
    setLoading(true);
    const startTime = performance.now();

    try {
      const formData = new FormData();
      
      if (uploadedFile) {
        formData.append("file", uploadedFile);
      }
      
      if (input.trim()) {
        formData.append("topic", input);
      }

      // Pass pre-approved outline so backend skips Llama3 outline generation
      if (approvedOutline) {
        formData.append("outline_json", JSON.stringify(approvedOutline));
      }
      
      formData.append("slide_count", parseInt(slideCount));
      formData.append("theme", theme);
      formData.append("language", language);

      console.log("Sending to backend with FormData");
      console.log("Form data contents:");
      for (let [key, value] of formData.entries()) {
        console.log(`  ${key}:`, value);
      }

      const response = await axios.post("http://localhost:8000/generate", formData);

      const endTime = performance.now();
      const executionTime = ((endTime - startTime) / 1000).toFixed(2);

      console.log("Backend response:", response.data);

      if (response.data.status === "validated" && response.data.pptx_path) {
        const newStats = {
          presentationsGenerated: stats.presentationsGenerated + 1,
          slidesCreated: stats.slidesCreated + parseInt(slideCount),
          executionTime: parseFloat(executionTime),
        };
        setStats(newStats);
        localStorage.setItem("slidesmith_stats", JSON.stringify(newStats));

        const title = uploadedFile
          ? uploadedFile.name.substring(0, 50)
          : input.substring(0, 50) + (input.length > 50 ? "..." : "");

        const newRecent = [
          {
            id: response.data.id,
            title: title,
            theme: theme,
            slides: parseInt(slideCount),
            timestamp: new Date().toLocaleString(),
            pptxPath: response.data.pptx_path,
          },
          ...recent.slice(0, 4),
        ];
        setRecent(newRecent);
        localStorage.setItem("slidesmith_recent", JSON.stringify(newRecent));

        addNotification(
          `✅ Presentation generated in ${executionTime}s with ${slideCount} slides!`,
          "success"
        );

        if (response.data.slides && response.data.slides.length > 0) {
          setCurrentTitle(response.data.topic || title);
          setCurrentSlides(response.data.slides);
          setCurrentPptxPath(response.data.pptx_path || "");
          setViewerOpen(true);
          if (response.data.pptx_path) {
            setTimeout(() => downloadPresentation(response.data.pptx_path), 500);
          }
        } else {
          if (response.data.pptx_path) {
            downloadPresentation(response.data.pptx_path);
          }
        }

        setInput("");
        setUploadedFile(null);
        setOutlinePreview(null);
        setEditedSlides([]);
        fetchMyPresentations();
      } else {
        addNotification(
          `Generation failed: ${response.data.error || "unknown error"}`,
          "error"
        );
      }
    } catch (err) {
      console.error("Error details:", err);
      
      let errorMessage = "Failed to generate presentation. Please try again.";
      
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      addNotification(errorMessage, "error");
    } finally {
      setLoading(false);
    }
  };

  const downloadPresentation = (pptxPath) => {
    const downloadUrl = `http://localhost:8000/download/${encodeURIComponent(pptxPath)}`;
    const downloadLink = document.createElement("a");
    downloadLink.href = downloadUrl;
    const filename = pptxPath.split("/").pop() || `SlideSmith_${Date.now()}.pptx`;
    downloadLink.setAttribute("download", filename);
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
  };

  const handleKeyPress = (e) => {
    if (e.ctrlKey && e.key === "Enter") {
      generatePPT();
    }
  };

  return (
    <div className="app-wrapper">
      {/* NAVBAR */}
      <nav className="navbar">
        <div className="navbar-content">
          <div className="logo">
            <span className="logo-icon">✨</span>
            <span>SlideSmith</span>
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
            Presentations Crafted: <strong>{stats.presentationsGenerated}</strong>
          </div>
        </div>
      </nav>

      {/*MAIN CONTAINER*/}
      <div className="container">
        {/*HEADER*/}
        <div className="header">
          <div className="tagline">Enterprise-Grade Presentations</div>
          <h1>SlideSmith</h1>
          <p>Generate executive-grade presentations with AI-powered insights</p>
        </div>

        <div className="stats">
          <div className="stat-card">
            <div className="stat-value">{stats.presentationsGenerated}</div>
            <div className="stat-label">Presentations Generated</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.slidesCreated}</div>
            <div className="stat-label">Total Slides Created</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.executionTime}s</div>
            <div className="stat-label">Last Generation Time</div>
          </div>
        </div>

        <div className="auth-card">
          <div className="auth-header">
            <div>
              {isAuthenticated ? (
                <>
                  <div className="auth-status">Signed in as <strong>{userEmail || "User"}</strong></div>
                  <button className="auth-logout" onClick={handleLogout}>
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <div className="auth-status">Please login or register to use SlideSmith</div>
                  <div className="auth-switch">
                    <button
                      className={authMode === "login" ? "active" : ""}
                      onClick={() => setAuthMode("login")}
                    >
                      Login
                    </button>
                    <button
                      className={authMode === "register" ? "active" : ""}
                      onClick={() => setAuthMode("register")}
                    >
                      Register
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>

          {!isAuthenticated && (
            <form className="auth-form" onSubmit={handleAuthSubmit}>
              {authMode === "register" && (
                <div className="form-row">
                  <label>Username</label>
                  <input
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter username"
                    className="auth-input"
                  />
                </div>
              )}

              <div className="form-row">
                <label>Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter email"
                  className="auth-input"
                />
              </div>

              <div className="form-row">
                <label>Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  className="auth-input"
                />
                {authMode === "register" && (
                  <small style={{ color: "var(--text-secondary)", fontSize: "11px", marginTop: "4px", display: "block" }}>
                    Min 8 chars, 1 uppercase letter, 1 number
                  </small>
                )}
              </div>

              {/* Remember Me — only shown on login */}
              {authMode === "login" && (
                <div className="form-row" style={{ flexDirection: "row", alignItems: "center", gap: "8px" }}>
                  <input
                    type="checkbox"
                    id="rememberMe"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    style={{ width: "16px", height: "16px", cursor: "pointer" }}
                  />
                  <label htmlFor="rememberMe" style={{ fontSize: "13px", cursor: "pointer", margin: 0 }}>
                    Remember me
                  </label>
                  <span style={{ fontSize: "11px", color: "var(--text-secondary)", marginLeft: "4px" }}>
                    {rememberMe ? "Stays logged in across sessions" : "Logs out when tab closes"}
                  </span>
                </div>
              )}

              <button type="submit" className="generate-btn">
                {authMode === "login" ? "Login" : "Register"}
              </button>
            </form>
          )}
        </div>

        {/* Fix 7: only show generator when authenticated */}
        {isAuthenticated && (
          <div className="card">
            {/* TEMPLATE SELECTION */}
            <div className="section">
              <label>📋 Presentation Template</label>
              <div className="theme-group">
                {["dark", "modern", "minimal"].map((t) => (
                  <button
                    key={t}
                    className={`theme-btn ${theme === t ? "active" : ""}`}
                    onClick={() => setTheme(t)}
                    disabled={loading}
                  >
                    {t === "dark" && "🌙"}
                    {t === "modern" && "🚀"}
                    {t === "minimal" && "⚪"} {t}
                  </button>
                ))}
              </div>
              <p className="section-hint">
                Choose a template style that matches your brand identity
              </p>
            </div>

            {/* LANGUAGE SELECTION */}
            <div className="section">
              <label>🌍 Presentation Language</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                disabled={loading}
                className="language-select"
              >
                <option value="english">English</option>
                <option value="spanish">Spanish (Español)</option>
                <option value="french">French (Français)</option>
                <option value="german">German (Deutsch)</option>
                <option value="italian">Italian (Italiano)</option>
                <option value="portuguese">Portuguese (Português)</option>
                <option value="chinese">Chinese (中文)</option>
                <option value="japanese">Japanese (日本語)</option>
                <option value="korean">Korean (한국어)</option>
                <option value="arabic">Arabic (العربية)</option>
                <option value="hindi">Hindi (हिंदी)</option>
                <option value="russian">Russian (Русский)</option>
                <option value="dutch">Dutch (Nederlands)</option>
                <option value="swedish">Swedish (Svenska)</option>
                <option value="turkish">Turkish (Türkçe)</option>
              </select>
              <p className="section-hint">
                Generate presentations and interact with Sally in your preferred language
              </p>
            </div>

            {/* FILE UPLOAD */}
            <div className="section">
              <label>Optional: Upload Research PDF or PPT</label>
              <div className="file-upload">
                <input
                  type="file"
                  accept=".pdf,.ppt,.pptx"
                  onChange={handleFileUpload}
                  disabled={loading}
                  id="fileInput"
                />
                <label htmlFor="fileInput" style={{ cursor: "pointer" }}>
                  <div className="file-upload-icon">📁</div>
                  <div>
                    {uploadedFile ? (
                      <strong>{uploadedFile.name}</strong>
                    ) : (
                      <>
                        <strong>Click to upload or drag and drop</strong>
                        <p style={{ margin: "4px 0 0 0", fontSize: "12px" }}>
                          PDF or PPT files
                        </p>
                      </>
                    )}
                  </div>
                </label>
              </div>
            </div>

            {/* INPUT */}
            <div className="section">
              <label>Presentation Brief</label>
              <textarea
                placeholder="Example: &quot;AI in Healthcare - Market trends, ROI projections, implementation roadmap, competitive landscape&quot;&#10;&#10;Tip: Include specific topics, metrics, or focus areas for better results. Press Ctrl+Enter to generate."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={loading}
                maxLength={2000}
              />
              <p className="section-hint">
                {2000 - input.length} characters remaining
              </p>
            </div>

            {/* SLIDE COUNT SLIDER */}
            <div className="section">
              <label>
                Number of Slides: <span className="slider-value">{slideCount}</span>
              </label>
              <input
                type="range"
                min="5"
                max="20"
                value={slideCount}
                onChange={(e) => setSlideCount(parseInt(e.target.value))}
                disabled={loading}
              />
              <p className="section-hint">Recommended: 12-15 slides for executive presentations</p>
            </div>

            {/* GENERATE BUTTON */}
            <button
              className="generate-btn"
              onClick={() => generatePPT()}
              disabled={loading || outlineLoading || (!input.trim() && !uploadedFile)}
            >
              {outlineLoading
                ? "⏳ Generating Outline..."
                : loading
                ? "🔨 Building Presentation..."
                : uploadedFile
                ? "Generate Presentation"
                : "Preview Outline →"}
            </button>

            {/* LOADING STATE */}
            {outlineLoading && (
              <div className="loading">
                <p>🤖 Asking AI to plan your presentation...</p>
                <p>📋 Generating slide outline...</p>
              </div>
            )}
            {loading && (
              <div className="loading">
                <p>📊 Structuring narrative and data flow...</p>
                <p>🎨 Generating slides with professional formatting...</p>
                <p>🖼️ Fetching relevant images...</p>
                <p>✅ Finalizing presentation and preparing download...</p>
              </div>
            )}
          </div>
        )}

        {/* MY PRESENTATIONS — from DB, per user */}
        {isAuthenticated && (
          <div className="card" style={{ marginTop: "30px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ margin: 0, color: "var(--text-primary)" }}>
                📚 My Presentations
              </h3>
              <button
                onClick={fetchMyPresentations}
                disabled={myPresLoading}
                style={{
                  padding: "6px 14px",
                  background: "var(--primary)",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "12px",
                  opacity: myPresLoading ? 0.6 : 1,
                }}
              >
                {myPresLoading ? "Loading..." : "↻ Refresh"}
              </button>
            </div>

            {myPresLoading && myPresentations.length === 0 ? (
              <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>Loading your presentations...</p>
            ) : myPresentations.length === 0 ? (
              <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                No presentations yet. Generate your first one above!
              </p>
            ) : (
              myPresentations.map((item) => (
                <div
                  key={item.id}
                  style={{
                    padding: "14px 12px",
                    borderBottom: "1px solid var(--border-color)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "12px",
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: "14px", color: "var(--text-primary)", marginBottom: "4px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {item.topic || "Untitled"}
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                      {item.slide_count} slides • {item.theme} • {item.language}
                      {item.created_at && (
                        <> • {new Date(item.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</>
                      )}
                      {" "}
                      <span style={{
                        display: "inline-block",
                        padding: "1px 7px",
                        borderRadius: "10px",
                        fontSize: "11px",
                        fontWeight: 600,
                        background: item.status === "completed" || item.status === "COMPLETED" ? "#dcfce7" : "#fee2e2",
                        color: item.status === "completed" || item.status === "COMPLETED" ? "#16a34a" : "#dc2626",
                      }}>
                        {item.status}
                      </span>
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
                    {/* View slides if slides_json is available */}
                    {item.slides_json && item.slides_json.length > 0 && (
                      <button
                        onClick={() => {
                          setCurrentTitle(item.topic || "Presentation");
                          setCurrentSlides(item.slides_json);
                          setCurrentPptxPath(item.pptx_path || "");
                          setViewerOpen(true);
                        }}
                        style={{
                          padding: "5px 12px",
                          background: "#667eea",
                          color: "white",
                          border: "none",
                          borderRadius: "5px",
                          cursor: "pointer",
                          fontSize: "12px",
                        }}
                      >
                        👁 View
                      </button>
                    )}

                    {/* Download if pptx_path exists */}
                    {item.pptx_path && (
                      <button
                        onClick={() => downloadPresentation(item.pptx_path)}
                        style={{
                          padding: "5px 12px",
                          background: "var(--primary)",
                          color: "white",
                          border: "none",
                          borderRadius: "5px",
                          cursor: "pointer",
                          fontSize: "12px",
                        }}
                      >
                        ⬇️ Download
                      </button>
                    )}

                    {/* Delete — with inline confirmation */}
                    {confirmDeleteId === item.id ? (
                      <>
                        <button
                          onClick={() => deletePresentation(item.id)}
                          disabled={deletingId === item.id}
                          style={{
                            padding: "5px 12px",
                            background: "#dc2626",
                            color: "white",
                            border: "none",
                            borderRadius: "5px",
                            cursor: "pointer",
                            fontSize: "12px",
                            opacity: deletingId === item.id ? 0.6 : 1,
                          }}
                        >
                          {deletingId === item.id ? "Deleting..." : "Confirm"}
                        </button>
                        <button
                          onClick={() => setConfirmDeleteId(null)}
                          style={{
                            padding: "5px 10px",
                            background: "#e5e7eb",
                            color: "#374151",
                            border: "none",
                            borderRadius: "5px",
                            cursor: "pointer",
                            fontSize: "12px",
                          }}
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => setConfirmDeleteId(item.id)}
                        style={{
                          padding: "5px 10px",
                          background: "transparent",
                          color: "#dc2626",
                          border: "1px solid #dc2626",
                          borderRadius: "5px",
                          cursor: "pointer",
                          fontSize: "12px",
                        }}
                      >
                        🗑 Delete
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}


        {/*FOOTER*/}
        <footer className="footer">
          <div className="footer-links">
            <a href="#features">Features</a>
            <a href="#about">About</a>
          </div>
          <p>© 2026 SlideSmith. Crafting Excellence in Every Presentation.</p>
        </footer>
      </div>


      {/*TOAST NOTIFICATIONS*/}
      <div>
        {notifications.map((notif) => (
          <div key={notif.id} className={`toast ${notif.type}`}>
            {notif.message}
          </div>
        ))}
      </div>

      {/* OUTLINE PREVIEW MODAL */}
      {outlinePreview && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
          display: "flex", alignItems: "center", justifyContent: "center",
          zIndex: 1000, padding: "20px",
        }}>
          <div style={{
            background: "white", borderRadius: "12px", width: "100%",
            maxWidth: "640px", maxHeight: "85vh", display: "flex",
            flexDirection: "column", boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
          }}>
            {/* Header */}
            <div style={{ padding: "20px 24px 16px", borderBottom: "1px solid #e5e7eb" }}>
              <h2 style={{ margin: 0, fontSize: "18px", color: "#111827" }}>
                📋 Review Your Outline
              </h2>
              <p style={{ margin: "6px 0 0", fontSize: "13px", color: "#6b7280" }}>
                Edit slide titles if needed, then click Build Presentation.
              </p>
            </div>

            {/* Slide list */}
            <div style={{ flex: 1, overflowY: "auto", padding: "16px 24px" }}>
              {editedSlides.map((slide, idx) => (
                <div key={idx} style={{
                  display: "flex", alignItems: "center", gap: "12px",
                  padding: "10px 0", borderBottom: "1px solid #f3f4f6",
                }}>
                  <span style={{
                    minWidth: "28px", height: "28px", borderRadius: "50%",
                    background: "linear-gradient(135deg, #667eea, #764ba2)",
                    color: "white", display: "flex", alignItems: "center",
                    justifyContent: "center", fontSize: "12px", fontWeight: 700,
                    flexShrink: 0,
                  }}>
                    {idx + 1}
                  </span>
                  <input
                    value={slide.title}
                    onChange={(e) => {
                      const updated = [...editedSlides];
                      updated[idx] = { ...updated[idx], title: e.target.value };
                      setEditedSlides(updated);
                    }}
                    style={{
                      flex: 1, border: "1px solid #e5e7eb", borderRadius: "6px",
                      padding: "7px 10px", fontSize: "14px", color: "#111827",
                      outline: "none",
                    }}
                    onFocus={(e) => e.target.style.borderColor = "#667eea"}
                    onBlur={(e) => e.target.style.borderColor = "#e5e7eb"}
                  />
                </div>
              ))}
            </div>

            {/* Footer */}
            <div style={{
              padding: "16px 24px", borderTop: "1px solid #e5e7eb",
              display: "flex", gap: "10px", justifyContent: "flex-end",
            }}>
              <button
                onClick={() => { setOutlinePreview(null); setEditedSlides([]); }}
                style={{
                  padding: "9px 18px", background: "#f3f4f6", color: "#374151",
                  border: "none", borderRadius: "7px", cursor: "pointer",
                  fontSize: "14px", fontWeight: 500,
                }}
              >
                ✕ Cancel
              </button>
              <button
                onClick={() => {
                  const approved = {
                    title: outlinePreview.title,
                    slides: editedSlides,
                    summary: outlinePreview.summary || "",
                  };
                  setOutlinePreview(null);
                  generatePPT(approved);
                }}
                style={{
                  padding: "9px 20px",
                  background: "linear-gradient(135deg, #667eea, #764ba2)",
                  color: "white", border: "none", borderRadius: "7px",
                  cursor: "pointer", fontSize: "14px", fontWeight: 600,
                }}
              >
                🚀 Build Presentation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SLIDE VIEWER MODAL */}
      {viewerOpen && (
        <SlideViewer
          slides={currentSlides}
          presentationTitle={currentTitle}
          onClose={() => setViewerOpen(false)}
          pptxPath={currentPptxPath}
          onDownload={downloadPresentation}
          language={language}
          onNotify={addNotification}
        />
      )}
    </div>
  );
}

export default App;