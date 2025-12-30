import { useEffect, useState } from "react";
import { POLYGON_EXPLORER } from "../config";

type Props = {
  /** Transaction hash (0x... or raw hex) */
  txHash: string;
  /** Optional known block number */
  blockNumber?: number | null;
  /** Optional short label override */
  label?: string;
  /** Optional compact mode (smaller font) */
  compact?: boolean;
};

/**
 * TxLink component — shows a clickable Polygonscan link for a Polygon transaction.
 * Auto-checks its status every few seconds until confirmed.
 */
export default function TxLink({ txHash, blockNumber, label, compact }: Props) {
  const [status, setStatus] = useState<"pending" | "confirmed" | "failed" | null>(null);
  const [block, setBlock] = useState<number | null>(blockNumber ?? null);
  const [error, setError] = useState<string | null>(null);

  // --- NEW: ensure the hash we use for href/polling always has 0x ---
  const fullHash = txHash?.startsWith("0x") ? txHash : (txHash ? `0x${txHash}` : "");

  // Auto-poll the transaction status via Polygonscan API
  useEffect(() => {
    if (!fullHash) return;

    let timer: NodeJS.Timeout | null = null;
    let cancelled = false;

    async function fetchStatus() {
      try {
        // ⚠️ Polygonscan's free API endpoint (for Amoy testnet) can be used if you have an API key.
        // Otherwise, just mark it pending until explorer indexes it.
        const apiUrl = `https://api-amoy.polygonscan.com/api?module=transaction&action=gettxreceiptstatus&txhash=${fullHash}`;
        const resp = await fetch(apiUrl);
        const json = await resp.json().catch(() => ({}));

        if (cancelled) return;

        if (json?.status === "1" && json?.result?.status === "1") {
          setStatus("confirmed");
        } else if (json?.status === "1" && json?.result?.status === "0") {
          setStatus("failed");
        } else {
          setStatus("pending");
        }
      } catch (e: any) {
        setError(e.message || "Failed to check transaction status");
      }
    }

    // Immediately fetch, then repeat every 10s until confirmed or failed
    fetchStatus();
    timer = setInterval(fetchStatus, 10000);

    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [fullHash]);

  // Show a short hash without the 0x prefix
  const raw = (fullHash || "").replace(/^0x/, "");
  const shortHash = raw ? `${raw.slice(0, 6)}…${raw.slice(-4)}` : "(no hash)";

  const baseStyle: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    fontSize: compact ? 12 : 14,
    marginTop: compact ? 2 : 6,
  };

  const dotStyle: React.CSSProperties = {
    width: 8,
    height: 8,
    borderRadius: "50%",
    backgroundColor:
      status === "confirmed" ? "#10B981" :
      status === "failed" ? "#EF4444" :
      "#FACC15",
    flexShrink: 0,
  };

  const labelText =
    label ??
    (status === "confirmed"
      ? "Confirmed"
      : status === "failed"
      ? "Failed"
      : "Pending…");

  // Robust explorer base (no trailing slash), and always use fullHash (with 0x) in href
  const explorerBase = POLYGON_EXPLORER.replace(/\/$/, "");
  const href = `${explorerBase}/tx/${fullHash}`;

  return (
    <div style={baseStyle}>
      <div style={dotStyle} title={status ?? "unknown"} />
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className="underline text-blue-600"
        style={{ textDecorationThickness: 1 }}
      >
        {labelText} ({shortHash})
      </a>
      {block && (
        <span style={{ color: "#6B7280", fontSize: compact ? 11 : 13 }}>
          · Block {block}
        </span>
      )}
      {error && (
        <span style={{ color: "red", marginLeft: 4, fontSize: compact ? 11 : 12 }}>
          {error}
        </span>
      )}
    </div>
  );
}
