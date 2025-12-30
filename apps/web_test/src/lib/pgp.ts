import * as openpgp from 'openpgp';

// Force classic prefs so server-side 'pgpy' can parse the key (no SHA-3/AEAD-only)
(openpgp.config as any).hashAlgorithm = openpgp.enums.hash.sha256;                  // used for signatures
(openpgp.config as any).preferredHashAlgorithm = openpgp.enums.hash.sha256;         // self-sig prefs
(openpgp.config as any).preferredSymmetricAlgorithm = openpgp.enums.symmetric.aes256;
(openpgp.config as any).preferredCompressionAlgorithm = openpgp.enums.compression.zlib;
(openpgp.config as any).showVersion = false;                                        // optional: reduce metadata



/** Apply classic prefs so server-side PGP (pgpy) parses keys cleanly. */
function initOpenPGPLegacyPrefs() {
  // TypeScript types for config are strict; use 'any' to set allowed runtime fields.
  const cfg: any = (openpgp as any).config;
  const enums: any = (openpgp as any).enums;

  // Use SHA-256 for signatures; avoid SHA-3 only prefs that pgpy can’t parse.
  cfg.hashAlgorithm = enums.hash.sha256;
  cfg.preferredHashAlgorithm = enums.hash.sha256;

  // Symmetric & compression preferences commonly supported by gpg/pgpy.
  cfg.preferredSymmetricAlgorithm = enums.symmetric.aes256;
  cfg.preferredCompressionAlgorithm = enums.compression.zlib;

  // Optional: reduce extra metadata in self-sig.
  cfg.showVersion = false;
}
initOpenPGPLegacyPrefs();

// ---------------------------------------------------------------------------

export type GeneratedKeys = {
  publicKeyArmored: string;
  privateKeyArmored: string;
  revocationCertificate: string;
};

export async function generateKeypair(
  email: string,
  name?: string,
  passphrase?: string
): Promise<GeneratedKeys> {
  const { privateKey, publicKey, revocationCertificate } = await openpgp.generateKey({
    type: 'rsa',               // broad compatibility with gpg/pgpy
    rsaBits: 4096,
    userIDs: [{ name: name ?? email.split('@')[0], email }],
    passphrase: passphrase || undefined,
    keyExpirationTime: 365 * 24 * 60 * 60, // 1 year (optional)
    format: 'armored',
  });
  return {
    publicKeyArmored: publicKey,
    privateKeyArmored: privateKey,
    revocationCertificate,
  };
}

export async function signText(
  privateKeyArmored: string,
  text: string,
  passphrase?: string
): Promise<string> {
  const privKey = await openpgp.readPrivateKey({ armoredKey: privateKeyArmored });
  const unlocked = passphrase
    ? await openpgp.decryptKey({ privateKey: privKey, passphrase })
    : privKey;

  const sig = await openpgp.sign({
    message: await openpgp.createMessage({ text }), // literal data packet
    signingKeys: unlocked,
    detached: true,
    format: 'armored',
  });

  return sig as string; // ASCII-armored detached signature
}

// --- naive local storage for MVP (existing) ---
const KEYS_STORAGE = 'klyvo_pgp_keys';

export function saveKeysToLocal(keys: GeneratedKeys & { email: string }) {
  localStorage.setItem(KEYS_STORAGE, JSON.stringify(keys));
}

export function loadKeysFromLocal(): (GeneratedKeys & { email: string }) | null {
  const raw = localStorage.getItem(KEYS_STORAGE);
  return raw ? JSON.parse(raw) : null;
}

export function clearKeys() {
  localStorage.removeItem(KEYS_STORAGE);
}

/** Optional slim helpers used in the login flow (store only pub/priv). */
const SLIM_PGP = 'klyvo_pgp';
export function savePGP(pub: string, priv: string) {
  localStorage.setItem(SLIM_PGP, JSON.stringify({ pub, priv }));
}
export function loadPGP(): { pub: string; priv: string } | null {
  const raw = localStorage.getItem(SLIM_PGP);
  return raw ? JSON.parse(raw) : null;
}
