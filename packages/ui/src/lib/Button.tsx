import React from "react";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

export function Button({ variant = "primary", children, style, ...props }: ButtonProps) {
  const baseStyle: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    borderRadius: 8,
    padding: "10px 16px",
    fontSize: 14,
    fontWeight: 600,
    transition: "background-color 120ms ease, color 120ms ease, border-color 120ms ease",
    border: "1px solid transparent",
  };
  const primaryStyle: React.CSSProperties = {
    backgroundColor: "#2563eb",
    color: "#fff",
  };
  const secondaryStyle: React.CSSProperties = {
    backgroundColor: "#f3f4f6",
    color: "#111827",
    borderColor: "#e5e7eb",
  };
  const combined: React.CSSProperties = {
    ...baseStyle,
    ...(variant === "primary" ? primaryStyle : secondaryStyle),
    ...(style || {}),
  };
  return (
    <button style={combined} {...props}>
      {children}
    </button>
  );
}


