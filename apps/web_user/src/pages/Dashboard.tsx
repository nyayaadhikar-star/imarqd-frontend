// src/pages/Dashboard.tsx
import React, { useEffect, useMemo, useState } from "react";
import { fetchUserMedia } from "../lib/api"; // adjust path if your structure differs

type MediaRow = {
  id?: number;
  owner_email?: string | null;
  owner_email_sha: string;
  media_id: string;
  user_uuid?: string | null;
  label?: string | null;
  active: boolean;
  created_at?: string | null;
  revoked_at?: string | null;
};

const formatDateTime = (iso?: string | null) => {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso; // fallback raw
  return d.toLocaleString();
};

const clip = (s: string, left = 10, right = 8) => {
  if (!s) return "";
  if (s.length <= left + right + 3) return s;
  return `${s.slice(0, left)}…${s.slice(-right)}`;
};

const Dashboard: React.FC = () => {
  const [rows, setRows] = useState<MediaRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // Pull auth/session info from localStorage (aligned to your existing app)
  const email = useMemo(
    () =>
      localStorage.getItem("email") ||
      localStorage.getItem("user_email") ||
      "",
    []
  );
  const emailSha = useMemo(
    () =>
      localStorage.getItem("email_sha") ||
      localStorage.getItem("owner_email_sha") ||
      "",
    []
  );

  useEffect(() => {
    let mounted = true;

    const goLogin = () => {
      // No email_sha – send to login
      window.location.hash = "#/login";
    };

    const load = async () => {
      try {
        if (!emailSha) {
          goLogin();
          return;
        }
        setLoading(true);
        setErr(null);
        const res = await fetchUserMedia(emailSha);
        if (!mounted) return;

        // Expecting array; if backend wraps, adapt here
        const data = Array.isArray(res) ? res : res?.items || [];
        setRows(data as MediaRow[]);
      } catch (e: any) {
        if (!mounted) return;
        setErr(e?.message || "Failed to load media.");
      } finally {
        if (mounted) setLoading(false);
      }
    };

    load();
    return () => {
      mounted = false;
    };
  }, [emailSha]);

  const onClickWatermark = () => {
    window.location.hash = "#/watermark";
  };

  const onClickVerify = (mediaId?: string) => {
    // Pre-fill verify page with media_id
    if (mediaId) {
      window.location.hash = `#/verify-ownership?media_id=${encodeURIComponent(
        mediaId
      )}`;
    } else {
      window.location.hash = "#/verify-ownership";
    }
  };

  return (
    <div className="container mx-auto max-w-5xl px-4 py-6">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Your Dashboard</h1>
          <p className="text-sm text-gray-600">
            {email ? (
              <>
                Signed in as <span className="font-medium">{email}</span>{" "}
                <span className="text-gray-400">({clip(emailSha, 8, 8)})</span>
              </>
            ) : (
              <>Signed in</>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="rounded-xl bg-black px-4 py-2 text-white hover:opacity-90"
            onClick={onClickWatermark}
          >
            + Watermark Image
          </button>
          <button
            className="rounded-xl border border-gray-300 px-4 py-2 hover:bg-gray-50"
            onClick={() => onClickVerify(undefined)}
          >
            Verify Uploaded Image
          </button>
        </div>
      </div>

      {/* States */}
      {loading && (
        <div className="rounded-xl border border-gray-200 p-4">
          <div className="animate-pulse text-gray-600">Loading your media…</div>
        </div>
      )}

      {err && !loading && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {err}
        </div>
      )}

      {!loading && !err && rows.length === 0 && (
        <div className="rounded-xl border border-gray-200 p-6 text-center">
          <p className="mb-2 text-gray-700">
            You don’t have any saved Media IDs yet.
          </p>
          <p className="text-sm text-gray-500">
            Use <span className="font-medium">Watermark Image</span> to embed a
            payload and (optionally) auto-save a <code>media_id</code> for
            future verification.
          </p>
        </div>
      )}

      {!loading && !err && rows.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50 text-left text-xs uppercase tracking-wider text-gray-600">
              <tr>
                <th className="px-4 py-3">Label</th>
                <th className="px-4 py-3">Media ID</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white text-sm">
              {rows.map((r) => (
                <tr key={`${r.media_id}-${r.created_at ?? ""}`}>
                  <td className="px-4 py-3">
                    {r.label ? (
                      <span className="font-medium">{r.label}</span>
                    ) : (
                      <span className="text-gray-500">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    {clip(r.media_id, 12, 10)}
                  </td>
                  <td className="px-4 py-3">
                    {formatDateTime(r.created_at)}
                  </td>
                  <td className="px-4 py-3">
                    {r.active ? (
                      <span className="inline-flex items-center rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">
                        Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center rounded-full bg-gray-50 px-2.5 py-0.5 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-400/30">
                        Revoked
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs hover:bg-gray-50"
                        onClick={() => onClickVerify(r.media_id)}
                        title="Go to Verify with this media prefilled"
                      >
                        Verify
                      </button>
                      <button
                        className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs hover:bg-gray-50"
                        onClick={() =>
                          navigator.clipboard.writeText(r.media_id)
                        }
                        title="Copy media_id"
                      >
                        Copy ID
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
