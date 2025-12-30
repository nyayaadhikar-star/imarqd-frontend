// src/App.tsx
import { useEffect, useState } from "react";

// Header is a NAMED export
import { Header } from "./components/Header";

// Pages (all default exports in your repo)
import Login from "./pages/Login";
import Watermark from "./pages/Watermark";
import Verify from "./pages/Verify";
import VideoWatermark from "./pages/VideoWatermark";
import VideoVerify from "./pages/VideoVerify";

// Auth helpers
import { loadAuth, clearAllAuth } from "./lib/auth";

type View = "login" | "watermark" | "verify" | "vwatermark" | "vverify";

export default function App() {
  const [authed, setAuthed] = useState<boolean>(false);
  const [view, setView] = useState<View>("login");

  // Initialize auth + default landing
  useEffect(() => {
    const a = loadAuth();
    const isAuthed = !!a?.token;
    setAuthed(isAuthed);
    setView(isAuthed ? "watermark" : "login");
  }, []);

  // Keep auth status in sync if other tabs/pages change localStorage
  useEffect(() => {
    const onStorage = () => {
      const a = loadAuth();
      const isAuthed = !!a?.token;
      setAuthed(isAuthed);
      if (!isAuthed) setView("login");
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const handleNav = (to: View) => {
    // If not authed, restrict to login
    if (!authed && to !== "login") {
      setView("login");
      return;
    }
    setView(to);
  };

  const handleLogout = () => {
    clearAllAuth();
    setAuthed(false);
    setView("login");
  };

  return (
    <div className="app-shell">
      <Header authed={authed} current={view} onNav={handleNav} onLogout={handleLogout} />

      <main className="page-container">
        {!authed ? (
          <Login />
        ) : (
          <>
            {view === "watermark" && <Watermark />}
            {view === "verify" && <Verify />}
            {view === "vwatermark" && <VideoWatermark />}
            {view === "vverify" && <VideoVerify />}
          </>
        )}
      </main>
    </div>
  );
}
