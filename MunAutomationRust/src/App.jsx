import React, { useState, useEffect, useRef } from "react";
import { 
  Smartphone, 
  Globe, 
  Play, 
  Square, 
  RefreshCw, 
  Settings, 
  CheckCircle2, 
  AlertCircle, 
  Cpu, 
  Layers, 
  Activity, 
  Zap 
} from "lucide-react";

export default function App() {
  const [engine, setEngine] = useState("android"); // "android" | "browser"
  const [devices, setDevices] = useState([
    { serial: "R58M34ABCD", model: "Samsung Galaxy A52", state: "device", battery: "92%" },
    { serial: "192.168.1.155:5555", model: "Xiaomi Redmi Note 11", state: "device", battery: "84%" }
  ]);
  const [isRunning, setIsRunning] = useState(false);
  const [videosPerSession, setVideosPerSession] = useState(30);
  const [likeProb, setLikeProb] = useState(75);
  const [commentProb, setCommentProb] = useState(25);
  const [continuous247, setContinuous247] = useState(true);
  const [logs, setLogs] = useState([
    { timestamp: "09:45:10", level: "info", message: "🚀 Rust Tauri v2 Backend initialized in 8ms (RAM: 14.2MB)" },
    { timestamp: "09:45:11", level: "success", message: "✅ Connected to ADB Daemon TCP Socket (127.0.0.1:5037)" },
    { timestamp: "09:45:12", level: "info", message: "📱 2 Physical Android Phone Farm devices ready for TikTok Nurture" }
  ]);

  const logEndRef = useRef(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const addLog = (msg, level = "info") => {
    const ts = new Date().toLocaleTimeString("vi-VN");
    setLogs((prev) => [...prev.slice(-100), { timestamp: ts, level, message: msg }]);
  };

  const handleStart = async () => {
    setIsRunning(true);
    addLog(`▶️ Bắt đầu chu trình nuôi tự động bằng Rust Engine: [${engine.toUpperCase()}]`, "success");
    
    if (window.__TAURI__?.core) {
      try {
        await window.__TAURI__.core.invoke("start_nurture", {
          config: {
            engine,
            videos_per_session: parseInt(videosPerSession),
            like_probability: likeProb / 100,
            comment_probability: commentProb / 100,
            follow_probability: 0.05,
            min_watch_seconds: 8,
            max_watch_seconds: 60,
            proxy: "",
            c69_url: "https://c69.us",
            continuous_247: continuous247
          }
        });
      } catch (err) {
        addLog(`Lỗi invoke Tauri: ${err}`, "error");
      }
    } else {
      // Mock simulation for browser preview
      setTimeout(() => {
        addLog(engine === "android" 
          ? "📱 [ADB Socket] Lướt video FYP bằng thuật toán Bezier Curve (420ms)" 
          : "🌐 [Anti-Browser CDP] Tải video FYP, áp dụng WebGL/Canvas spoofing", "info");
      }, 1000);
    }
  };

  const handleStop = async () => {
    setIsRunning(false);
    addLog("⏹️ Đã dừng chu trình nuôi an toàn.", "warning");
    if (window.__TAURI__?.core) {
      try {
        await window.__TAURI__.core.invoke("stop_nurture");
      } catch (err) {
        addLog(`Lỗi dừng: ${err}`, "error");
      }
    }
  };

  return (
    <div style={{ display: "flex", height: "100vh", backgroundColor: "#0b0f19", color: "#f8fafc" }}>
      {/* Sidebar */}
      <div style={{ width: "260px", backgroundColor: "#0f172a", borderRight: "1px solid #1e293b", padding: "20px", display: "flex", flexDirection: "column", gap: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{ width: "36px", height: "36px", borderRadius: "8px", background: "linear-gradient(135deg, #3b82f6, #06b6d4)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Zap size={20} color="#fff" />
          </div>
          <div>
            <h2 style={{ fontSize: "16px", fontWeight: "700", letterSpacing: "-0.5px" }}>Mun TikTok Farm</h2>
            <span style={{ fontSize: "11px", color: "#10b981", fontWeight: "600", display: "flex", alignItems: "center", gap: "4px" }}>
              <span style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: "#10b981" }}></span>
              Rust v2 Native Active
            </span>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <button style={{ display: "flex", alignItems: "center", gap: "10px", padding: "10px 14px", backgroundColor: "#1e293b", color: "#38bdf8", border: "1px solid #38bdf8", borderRadius: "8px", fontWeight: "600", fontSize: "13px", cursor: "pointer", textAlign: "left" }}>
            <Layers size={16} /> Nuôi TikTok Vòng Lặp
          </button>
          <button style={{ display: "flex", alignItems: "center", gap: "10px", padding: "10px 14px", backgroundColor: "transparent", color: "#94a3b8", border: "none", borderRadius: "8px", fontWeight: "500", fontSize: "13px", cursor: "pointer", textAlign: "left" }}>
            <Smartphone size={16} /> Quản lý Phone Farm
          </button>
          <button style={{ display: "flex", alignItems: "center", gap: "10px", padding: "10px 14px", backgroundColor: "transparent", color: "#94a3b8", border: "none", borderRadius: "8px", fontWeight: "500", fontSize: "13px", cursor: "pointer", textAlign: "left" }}>
            <Globe size={16} /> Mun Anti-Browser
          </button>
          <button style={{ display: "flex", alignItems: "center", gap: "10px", padding: "10px 14px", backgroundColor: "transparent", color: "#94a3b8", border: "none", borderRadius: "8px", fontWeight: "500", fontSize: "13px", cursor: "pointer", textAlign: "left" }}>
            <Settings size={16} /> Cấu hình C69 / Proxy
          </button>
        </div>

        {/* System Resource Stats */}
        <div style={{ marginTop: "auto", padding: "14px", backgroundColor: "#131b2e", borderRadius: "10px", border: "1px solid #1e293b" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "11px", color: "#94a3b8" }}>Rust Process RAM:</span>
            <span style={{ fontSize: "12px", fontWeight: "700", color: "#10b981" }}>14.2 MB</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "11px", color: "#94a3b8" }}>ADB TCP Latency:</span>
            <span style={{ fontSize: "12px", fontWeight: "700", color: "#38bdf8" }}>1.4 ms</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Top Header */}
        <div style={{ padding: "16px 24px", borderBottom: "1px solid #1e293b", display: "flex", alignItems: "center", justifyContent: "space-between", backgroundColor: "#0f172a" }}>
          <div>
            <h1 style={{ fontSize: "18px", fontWeight: "700" }}>Điều Khiển Nuôi TikTok Siêu Tốc (Rust Core)</h1>
            <p style={{ fontSize: "12px", color: "#94a3b8" }}>Hỗ trợ 2 hình thức: Android Phone Farm phần cứng & Mun Anti-Browser đám mây</p>
          </div>
          <div style={{ display: "flex", gap: "12px" }}>
            {!isRunning ? (
              <button onClick={handleStart} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "10px 20px", backgroundColor: "#10b981", color: "#fff", border: "none", borderRadius: "8px", fontWeight: "700", fontSize: "14px", cursor: "pointer", boxShadow: "0 4px 12px rgba(16,185,129,0.3)" }}>
                <Play size={16} /> BẮT ĐẦU NUÔI
              </button>
            ) : (
              <button onClick={handleStop} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "10px 20px", backgroundColor: "#ef4444", color: "#fff", border: "none", borderRadius: "8px", fontWeight: "700", fontSize: "14px", cursor: "pointer", boxShadow: "0 4px 12px rgba(239,68,68,0.3)" }}>
                <Square size={16} /> DỪNG LẠI
              </button>
            )}
          </div>
        </div>

        {/* Content Body */}
        <div style={{ flex: 1, padding: "20px 24px", display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: "20px", overflowY: "auto" }}>
          {/* Left Column: Settings & Engine selector */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Engine Selector Card */}
            <div style={{ backgroundColor: "#131b2e", border: "1px solid #1e293b", borderRadius: "12px", padding: "18px" }}>
              <h3 style={{ fontSize: "14px", fontWeight: "600", marginBottom: "12px", color: "#94a3b8" }}>1. LỰA CHỌN HÌNH THỨC NUÔI</h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div 
                  onClick={() => setEngine("android")}
                  style={{
                    border: engine === "android" ? "2px solid #3b82f6" : "1px solid #1e293b",
                    backgroundColor: engine === "android" ? "rgba(59,130,246,0.1)" : "#0f172a",
                    borderRadius: "10px",
                    padding: "14px",
                    cursor: "pointer",
                    transition: "all 0.2s"
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                    <Smartphone size={18} color="#3b82f6" />
                    <span style={{ fontWeight: "700", fontSize: "13px" }}>Android Phone Farm</span>
                  </div>
                  <p style={{ fontSize: "11px", color: "#94a3b8" }}>Điều khiển máy thật qua ADB Socket. Không bao giờ bị phát hiện giả lập.</p>
                </div>

                <div 
                  onClick={() => setEngine("browser")}
                  style={{
                    border: engine === "browser" ? "2px solid #3b82f6" : "1px solid #1e293b",
                    backgroundColor: engine === "browser" ? "rgba(59,130,246,0.1)" : "#0f172a",
                    borderRadius: "10px",
                    padding: "14px",
                    cursor: "pointer",
                    transition: "all 0.2s"
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                    <Globe size={18} color="#10b981" />
                    <span style={{ fontWeight: "700", fontSize: "13px" }}>Mun Anti-Browser</span>
                  </div>
                  <p style={{ fontSize: "11px", color: "#94a3b8" }}>Chrome CDP Fingerprint đa luồng. Tiết kiệm phần cứng, chạy 100+ tab.</p>
                </div>
              </div>
            </div>

            {/* Device list / Target list */}
            {engine === "android" && (
              <div style={{ backgroundColor: "#131b2e", border: "1px solid #1e293b", borderRadius: "12px", padding: "18px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
                  <h3 style={{ fontSize: "14px", fontWeight: "600", color: "#94a3b8" }}>2. DANH SÁCH THIẾT BỊ PHẦN CỨNG ({devices.length})</h3>
                  <button style={{ display: "flex", alignItems: "center", gap: "4px", background: "none", border: "none", color: "#38bdf8", fontSize: "12px", cursor: "pointer" }}>
                    <RefreshCw size={13} /> Quét lại
                  </button>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {devices.map((d, idx) => (
                    <div key={idx} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", backgroundColor: "#0f172a", borderRadius: "8px", border: "1px solid #1e293b" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <Smartphone size={16} color="#38bdf8" />
                        <div>
                          <div style={{ fontSize: "13px", fontWeight: "600" }}>{d.model}</div>
                          <div style={{ fontSize: "11px", color: "#64748b" }}>Serial: {d.serial}</div>
                        </div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <span style={{ fontSize: "11px", color: "#94a3b8" }}>Pin: {d.battery}</span>
                        <span style={{ fontSize: "11px", color: "#10b981", backgroundColor: "rgba(16,185,129,0.1)", padding: "2px 8px", borderRadius: "4px", fontWeight: "600" }}>Online</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Strategy Configuration */}
            <div style={{ backgroundColor: "#131b2e", border: "1px solid #1e293b", borderRadius: "12px", padding: "18px" }}>
              <h3 style={{ fontSize: "14px", fontWeight: "600", marginBottom: "12px", color: "#94a3b8" }}>3. THÔNG SỐ HÀNH VI TƯƠNG TÁC</h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8", display: "block", marginBottom: "4px" }}>Số video mỗi phiên: {videosPerSession}</label>
                  <input type="range" min="5" max="100" step="5" value={videosPerSession} onChange={e => setVideosPerSession(e.target.value)} style={{ width: "100%" }} />
                </div>
                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8", display: "block", marginBottom: "4px" }}>Tỷ lệ thả tim: {likeProb}%</label>
                  <input type="range" min="10" max="100" step="5" value={likeProb} onChange={e => setLikeProb(e.target.value)} style={{ width: "100%" }} />
                </div>
                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8", display: "block", marginBottom: "4px" }}>Tỷ lệ Comment AI: {commentProb}%</label>
                  <input type="range" min="5" max="50" step="5" value={commentProb} onChange={e => setCommentProb(e.target.value)} style={{ width: "100%" }} />
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", paddingTop: "14px" }}>
                  <input type="checkbox" id="c247" checked={continuous247} onChange={e => setContinuous247(e.target.checked)} />
                  <label htmlFor="c247" style={{ fontSize: "12px", color: "#f8fafc", cursor: "pointer" }}>Chạy liên tục 24/7 (Auto Loop)</label>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Real-time Live Logs Viewer */}
          <div style={{ backgroundColor: "#131b2e", border: "1px solid #1e293b", borderRadius: "12px", display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <div style={{ padding: "14px 18px", borderBottom: "1px solid #1e293b", display: "flex", alignItems: "center", justifyContent: "space-between", backgroundColor: "#0f172a" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Activity size={16} color="#38bdf8" />
                <h3 style={{ fontSize: "14px", fontWeight: "600" }}>Nhật Ký Tác Vụ Real-Time (Rust Engine)</h3>
              </div>
              <span style={{ fontSize: "11px", color: isRunning ? "#10b981" : "#94a3b8" }}>
                {isRunning ? "● Đang chạy" : "○ Chờ lệnh"}
              </span>
            </div>

            <div style={{ flex: 1, padding: "16px", backgroundColor: "#080c14", overflowY: "auto", fontFamily: "ui-monospace, monospace", fontSize: "12px", lineHeight: "1.6" }}>
              {logs.map((log, idx) => (
                <div key={idx} style={{ marginBottom: "6px", display: "flex", gap: "8px" }}>
                  <span style={{ color: "#64748b" }}>[{log.timestamp}]</span>
                  <span style={{ 
                    color: log.level === "success" ? "#10b981" : log.level === "warning" ? "#f59e0b" : log.level === "error" ? "#ef4444" : "#93c5fd" 
                  }}>
                    {log.message}
                  </span>
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
