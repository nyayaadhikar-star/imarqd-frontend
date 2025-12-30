import { useEffect, useState } from "react";
import { Header } from "./components/Header";
import LoginPage from "./pages/Login";
import WatermarkPage from "./pages/Watermark";
import VerifyOwnership from "./pages/VerifyOwnership";
import { loadAuth, clearAllAuth } from "./lib/auth";

// ▼ NEW: import video pages
import VideoWatermark from "./pages/VideoWatermark";
import VideoVerify from "./pages/VideoVerify";

// ▼ UPDATED: include video views
type View = "login" | "watermark" | "verify" | "vwatermark" | "vverify";

function getViewFromHash(): View {
  const h = (window.location.hash || "").replace(/^#\/?/, "");
  if (h === "watermark") return "watermark";
  if (h === "verify") return "verify";
  // ▼ NEW:
  if (h === "vwatermark") return "vwatermark";
  if (h === "vverify") return "vverify";
  return "login";
}

export default function App() {
  const [auth, setAuth] = useState(loadAuth());
  const [view, setView] = useState<View>(auth ? "watermark" : "login");

  useEffect(() => {
    const onHash = () => setView(getViewFromHash());
    window.addEventListener("hashchange", onHash);
    if (auth && !window.location.hash) window.location.hash = "#/watermark";
    return () => window.removeEventListener("hashchange", onHash);
  }, [auth]);

  function handleNav(to: View) {
    window.location.hash = `#/${to}`;
  }

  function handleLogout() {
    clearAllAuth();
    setAuth(null);
    window.location.hash = "#/login";
  }

  return (
    <div className="app">
      <Header
        authed={!!auth}
        current={view}
        onNav={handleNav}
        onLogout={handleLogout}
      />

      <main className="container">
        {view === "login" && <LoginPage />}
        {view === "watermark" && <WatermarkPage />}
        {view === "verify" && <VerifyOwnership />}
        {/* ▼ NEW: video routes */}
        {view === "vwatermark" && <VideoWatermark />}
        {view === "vverify" && <VideoVerify />}
      </main>
    </div>
  );
}
