import React from "react";

type View = "login" | "watermark" | "verify" | "vwatermark" | "vverify";

export function Header({
  authed,
  current,
  onNav,
  onLogout,
}: {
  authed: boolean;
  current: View;
  onNav: (to: View) => void;
  onLogout: () => void;
}) {
  const NavBtn: React.FC<{ to: View; label: string }> = ({ to, label }) => (
    <button
      type="button"
      onClick={() => onNav(to)}
      className={`nav-link ${current === to ? "is-active" : ""}`}
      aria-current={current === to ? "page" : undefined}
    >
      {label}
    </button>
  );

  return (
    <header className="topbar">
      <div className="topbar__inner">
        {/* Brand */}
        <div className="brand" onClick={() => onNav(authed ? "watermark" : "login")}>
          <span className="brand__logo">Klyvo</span>
        </div>

        {/* Left nav */}
        <nav className="nav">
          <NavBtn to="watermark"  label="Image WM" />
          <NavBtn to="verify"      label="Image Verify" />
          <div className="divider" aria-hidden="true" />
          <NavBtn to="vwatermark" label="Video WM" />
          <NavBtn to="vverify"    label="Video Verify" />
        </nav>

        {/* Right side actions */}
        <div className="actions">
          {!authed ? (
            <button type="button" className="btn btn-primary" onClick={() => onNav("login")}>
              Login
            </button>
          ) : (
            <button type="button" className="btn btn-danger" onClick={onLogout}>
              Logout
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
