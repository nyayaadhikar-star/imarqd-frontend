// apps/web/src/lib/embedParams.ts
export type EmbedParams = {
  preset?: string | null;
  qim_step?: number;
  repetition?: number;
  ecc_parity_bytes?: number;
  use_y_channel?: boolean;
};

const STORAGE_KEY = "klyvo_last_embed_params";

export function saveLastEmbedParamsFromHeaders(h: Record<string,string>) {
  const get = (k: string) => h[k.toLowerCase()] ?? h[k];
  const params: EmbedParams = {
    preset: get("x-preset") || null,
    qim_step: num(get("x-params-qim")),
    repetition: int(get("x-params-repetition")),
    ecc_parity_bytes: int(get("x-params-ecc-parity")),
    // we don’t return use_y in headers; assume true for our pipeline
    use_y_channel: true,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(params));
}

export function loadLastEmbedParams(): EmbedParams | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw) as EmbedParams; } catch { return null; }
}

// helpers
function num(v?: string) { return v ? Number(v) : undefined; }
function int(v?: string) { return v ? parseInt(v, 10) : undefined; }
