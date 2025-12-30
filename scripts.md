# 1) Embed
python -m apps.api.src.modules.watermarking.cli_embed --in sample.jpg --out watermarked.png --text "klyvo-demo" --qim 8 --rep 20

# 2) (Optionally) modify the image slightly: resize or add light JPEG compression

# 3) Extract & compare
python -m apps.api.src.modules.watermarking.cli_extract --in watermarked.png --bitlen 256 --qim 8 --rep 20 --check-text "klyvo-demo"



# in apps/api (venv active)
uvicorn app.main:app --reload

http://127.0.0.1:8000/docs

# 1) Embed
# 1) Embed (returns image)
curl -X POST http://127.0.0.1:8000/api/watermark/image \
  -F "file=@apps/api/src/app/services/watermarking/sample.png" \
  -F "text=klyvo-demo" \
  -F "qim_step=8.0" \
  -F "repetition=20" \
  --output watermarked.png


# 2) Extract
curl -X POST http://127.0.0.1:8000/api/watermark/image/extract \
  -F "file=@watermarked.png" \
  -F "payload_bitlen=256" \
  -F "qim_step=8.0" -F "repetition=20" \
  -F "check_text=klyvo-demo"


# Embed (Y-channel + ECC)
curl -X POST http://127.0.0.1:8000/api/watermark/image \
  -F "file=@apps/api/src/app/services/watermarking/color.png" \
  -F "text=klyvo-demo" \
  -F "qim_step=8.0" -F "repetition=20" \
  -F "use_y_channel=true" \
  -F "use_ecc=true" -F "ecc_parity_bytes=24" \
  --output watermarked_color_ecc.png

# Extract (auto payload size from ecc_parity_bytes)
# Extract (ECC on, with similarity vs the ECC codeword)
curl -X POST http://127.0.0.1:8000/api/watermark/image/extract \
  -F "file=@WhatsApp_test.jpeg" \
  -F "qim_step=8.0" -F "repetition=20" \
  -F "use_y_channel=true" \
  -F "use_ecc=true" -F "ecc_parity_bytes=24" \
  -F "check_text=klyvo-demo"



# Embed (pre-resize your input in any editor first to ~1280px long edge)
curl -X POST http://127.0.0.1:8000/api/watermark/image \
  -F "file=@xxxl_trial.JPG" \
  -F "text=klyvo-demo" \
  -F "qim_step=14.0" -F "repetition=60" \
  -F "use_y_channel=true" \
  -F "use_ecc=true" -F "ecc_parity_bytes=48" \
  --output wm_stronger_new.png

# Send wm_stronger.png via WhatsApp as an image; download the received JPEG

# Extract
curl -X POST http://127.0.0.1:8000/api/watermark/image/extract \
  -F "file=@wm_pgp.png" \
  -F "qim_step=14.0" -F "repetition=60" \
  -F "use_y_channel=true" \
  -F "use_ecc=true" -F "ecc_parity_bytes=48" \
  -F "check_text=klyvo-demo"





# ############## PGP




# generate a key (if not already done)
gpg --quick-gen-key "user@example.com" rsa4096 sign 1y

// klyvo1234

# export public key to a file
gpg --armor --export "user@example.com" > pubkey.asc

ls pubkey.asc


curl -X POST http://127.0.0.1:8000/api/pgp/register \
  -F "public_key_armored=$(cat pubkey.asc)" \
  -F "email=user@example.com" \
  -F "display_name=Test User"



curl -i -X POST http://127.0.0.1:8000/api/pgp_debug/verify \
  -F "text=klyvo-demo" \
  -F "pgp_public_key=$(cat pubkey.asc)" \
  -F "pgp_signature=$(cat sig.asc)"


curl -s -D - -o wm_pgp.png http://127.0.0.1:8000/api/watermark/image \
  -F "file=@D:/Teaching/Upwork/KLYVO/WhatsApp_trial.jpeg" \
  -F "text=klyvo-demo" \
  -F "pre_whatsapp=true" \
  -F "pgp_public_key=$(cat pubkey.asc)" \
  -F "pgp_signature=$(cat sig.asc)"



curl -X POST http://127.0.0.1:8000/api/watermark/image/extract \
  -F "file=@D:/Teaching/Upwork/KLYVO/WhatsApp_pgp_final.jpeg" \
  -F "use_y_channel=true" \
  -F "use_ecc=true" -F "ecc_parity_bytes=24" \
  -F "qim_step=18.0" -F "repetition=100" \
  -F "check_text=klyvo-demo"



# dump headers to stdout, save body to file
curl -s -D - -o wm_pgp.png http://127.0.0.1:8000/api/watermark/image \
  -F "file=@D:/Teaching/Upwork/KLYVO/WhatsApp_trial.jpeg" \
  -F "text=klyvo-demo" \
  -F "profile=robust_whatsapp" \
  -F "pre_whatsapp=true" \
  -F "pgp_public_key=$(cat pubkey.asc)" \
  -F "pgp_signature=$(cat sig.asc)"


curl -s -D - -o wm_general.png http://127.0.0.1:8000/api/watermark/image \
  -F "file=@D:/Teaching/Upwork/KLYVO/WhatsApp_trial.jpeg" \
  -F "text=klyvo-demo" \
  -F "use_y_channel=true" \
  -F "qim_step=16.0" -F "repetition=80" \
  -F "use_ecc=true" -F "ecc_parity_bytes=24" \
  --output wm_pgp_new.png

  curl -i -X POST http://127.0.0.1:8000/api/watermark/image \
  -F "file=@D:/Teaching/Upwork/KLYVO/WhatsApp_trial.jpeg" \
  -F "text=klyvo-demo" \
  -F "profile=robust_whatsapp" \
  -F "pre_whatsapp=false" \
  -F "use_y_channel=true" \
  --output wm_stronger_new.png



python - << "PY"
import sqlite3, json
c=sqlite3.connect("klyvo_dev.db")
print("PGP Keys:", c.execute("select id,fingerprint from pgp_keys").fetchall())
print("Assets  :", c.execute("select id,original_filename,pgp_fingerprint,sha256_hex from media_assets order by id desc limit 3").fetchall())
print("Params  :", c.execute("select params from media_assets order by id desc limit 1").fetchone())
PY









PGP command kit (Windows Git Bash friendly)

Adjust the D:/… paths as needed. On PowerShell, prefer Get-Content -Raw instead of $(cat …); I include both variants where it matters.

0) Generate a signing key (once)
# Create a signing key (1-year validity)
gpg --quick-gen-key "puneet@klyvo.com" rsa4096 sign 1y

1) Export your public key (ASCII-armored)
gpg --armor --export "puneet@klyvo.com" > pubkey.asc

2) Create a detached signature over the exact claim text
# No trailing newline with -n. Must match the text you send to the API.
echo -n "klyvo-demo" | gpg --armor --detach-sign --local-user "puneet@klyvo.com" > sig.asc

3) Verify PGP via API (isolation test)

Git Bash (safe multiline form syntax):

curl -i -X POST http://127.0.0.1:8000/api/pgp_debug/verify \
  -F "text=klyvo-demo" \
  -F "pgp_public_key=$(cat pubkey.asc)" \
  -F "pgp_signature=$(cat sig.asc)"


Expected: 200 OK and {"ok":true,"fingerprint":"<40-hex>"}

PowerShell alternative:

Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/pgp_debug/verify" `
  -Method Post `
  -Form @{
    text = "klyvo-demo";
    pgp_public_key = (Get-Content "pubkey.asc" -Raw);
    pgp_signature  = (Get-Content "sig.asc" -Raw)
  } | Select-Object -ExpandProperty Content

4) Register public key in backend (optional but good for audit)
curl -i -X POST http://127.0.0.1:8000/api/pgp/register \
  -F "public_key_armored=$(cat pubkey.asc)" \
  -F "email=puneet@klyvo.com" \
  -F "display_name=Puneet"


Expected: {"fingerprint":"<…>","user_id":<n>}

5) Embed with PGP verification + general profile (PNG out)
curl -s -D - -o D:/tmp/wm_pgp.png http://127.0.0.1:8000/api/watermark/image \
  -F "file=@D:/Teaching/Upwork/KLYVO/WhatsApp_trial.jpeg" \
  -F "text=klyvo-demo" \
  -F "use_y_channel=true" \
  -F "qim_step=16.0" -F "repetition=80" \
  -F "use_ecc=true" -F "ecc_parity_bytes=24" \
  -F "pgp_public_key=$(cat pubkey.asc)" \
  -F "pgp_signature=$(cat sig.asc)"


Check headers printed above the binary:

X-PSNR-Y, X-SSIM-Y, X-Params-*, X-Payload-Bits (= 448 for 32+24)

6) Send the PNG via WhatsApp; download received JPEG
7) Extract & verify after WhatsApp
curl -X POST http://127.0.0.1:8000/api/watermark/image/extract \
  -F "file=@D:/path/WhatsApp_received.jpg" \
  -F "use_y_channel=true" \
  -F "use_ecc=true" -F "ecc_parity_bytes=24" \
  -F "qim_step=16.0" -F "repetition=80" \
  -F "check_text=klyvo-demo"


If not matching: retry with stronger settings:

repetition=100

qim_step=18.0

ecc_parity_bytes=32 (payload 512 bits; keep repetition ≥80)

8) Quick DB checks (SQLite)

List assets & fingerprints (Python one-liner):

python - << "PY"
import sqlite3
c=sqlite3.connect("klyvo_dev.db")
print("PGP keys:", c.execute("select id,fingerprint from pgp_keys").fetchall())
print("Assets   :", c.execute("select id,original_filename,pgp_fingerprint,substr(stored_path,1,60) from media_assets order by id desc limit 5").fetchall())
row = c.execute("select params from media_assets order by id desc limit 1").fetchone()
print("Last params:", row[0] if row else None)
PY


(Optional) Inspect the last asset’s stored PGP signature:

python - << "PY"
import sqlite3, textwrap
c=sqlite3.connect("klyvo_dev.db")
sig = c.execute("select pgp_signature_armored from media_assets order by id desc limit 1").fetchone()
print(textwrap.shorten(sig[0], width=200)) if sig and sig[0] else print("No signature stored")
PY

Troubleshooting quick hits







curl -s -D - -o wm_generic.png http://127.0.0.1:8000/api/watermark/image \
  -F "file=@D:/Teaching/Upwork/KLYVO/WA_pgp_pre.jpeg" \
  -F "text=klyvo-demo" \
  -F "use_y_channel=true" \
  -F "qim_step=18.0" \
  -F "repetition=120" \
  -F "use_ecc=true" -F "ecc_parity_bytes=32" \
  -F "pre_generic=true"



curl -X POST http://127.0.0.1:8000/api/watermark/image/extract \
  -F "file=@D:/Teaching/Upwork/KLYVO/WA_pgp_final.jpeg" \
  -F "use_y_channel=true" \
  -F "use_ecc=true" -F "ecc_parity_bytes=32" \
  -F "qim_step=18.0" -F "repetition=120" \
  -F "check_text=klyvo-demo"



curl -s -D - -o wm_generic.png http://127.0.0.1:8000/api/watermark/image \
  -F "file=@/path/to/image.jpg" \
  -F "text=owner:<YOUR_EMAIL_SHA>" \
  -F "use_y_channel=true" \
  -F "qim_step=18.0" -F "repetition=120" \
  -F "use_ecc=true" -F "ecc_parity_bytes=32"





# terminal 1
cd apps/api
uvicorn app.main:app --reload

# terminal 2
cd apps/web
npm run dev




✅ What we have achieved so far
1. Input / Modification

You uploaded an image (color.png).

System converted it into YCbCr color space, and took only the Y (luma) channel.

A SHA-256 hash of "klyvo-demo" was computed (32 bytes).

We ran Reed–Solomon ECC on it, adding 24 parity bytes → 56 bytes total.

Those 448 bits were embedded invisibly into mid-frequency DCT coefficients across 8×8 blocks of the Y channel, using QIM quantization with repetition.

So the modified thing is: your image now has hidden 448 bits (ECC-encoded SHA-256 of your text) in its Y channel.

2. Extraction

You uploaded the watermarked image back to the API.

System again split into YCbCr and took the Y channel.

Extracted the same 8×8 DCT coefficients, and decoded the 448 bits back.

So the extracted thing is: a noisy or perfect 448-bit stream that should equal the ECC codeword.

3. ECC Decoding

The extracted 448 bits were grouped into bytes.

Reed–Solomon decoding was applied:

If some bits were wrong, RS would fix them (up to its error correction limit).

If too many were wrong, decoding would fail (ecc_ok=false).

In your case, ECC decoding succeeded (ecc_ok=true).

4. Comparison

Two levels of comparison were done:

Bit similarity: recovered codeword vs expected ECC codeword.
→ 100% match, hence similarity=1.0.

Text hash match: after ECC decoding, we got the original 32-byte SHA-256.
→ Compared to SHA256("klyvo-demo").
→ They matched exactly (match_text_hash=true).

So what’s compared:

At the bit level: the entire ECC codeword (expected vs recovered).

At the semantic level: decoded 32-byte SHA-256 vs recomputed hash of your text.

🧭 Summary in plain English

You gave us "klyvo-demo".

We computed its SHA-256, then added ECC redundancy, then hid it invisibly in the Y channel of your image.

You sent the image back.

We pulled the hidden bits out, ECC-decoded them, and verified that they match exactly the original SHA-256 of "klyvo-demo".

Since there was no bit corruption this time, similarity = 1.0, ECC decoding succeeded, and the text hash matched.

📋 Progress Tracker

Completed:

Grayscale + Y-channel invisible watermarking (DCT + QIM).

ECC layer (Reed–Solomon) for robustness.

API endpoints fully functional (embed, extract).

Verified with curl → perfect recovery.

Next steps (choose path):

PSNR/SSIM metrics: return image quality numbers in /image response to prove watermark is invisible.

Profile modes: light/medium/strong watermark settings (auto-tune QIM step & repetition).

Extend to video (frame-wise Y-channel DCT embed).

Or shift to blockchain/IPFS minting.






















curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"temp@temp.com","password":"secret"}'
# -> {"token":"...","uuid":"<uuid5>","email":"temp@temp.com"}
























Love this pivot. Here’s a clean, production-minded blueprint for your **“prove ownership of my image”** flow using the modules you’ve already built—plus exactly how to treat email/PII so you’re private by design.

---

# 1) What “ownership” means in your MVP

An image belongs to a user if all three check out:

1. **Integrity claim** embedded: the watermark decodes to `ECC(SHA256(claim_text))` and matches the user’s claim.
2. **Identity binding (optional but strong):** the same `claim_text` is **PGP-signed** by the user’s public key, and the server has that public key registered.
3. **Account linkage:** the asset record in DB ties the decoded claim → the user account (by a stable, privacy-preserving identifier).

This gives you:

* “I can extract a claim from pixels” (watermark)
* “I can prove *who* authored that claim” (PGP)
* “I can link that claim to a logged-in user” (account)

---

# 2) End-to-end user journeys

## A) Register & publish (owner flow)

1. **Create account** (email + password or OAuth).

   * Store **email\_hash = SHA256(lower(email))**. Do **not** store raw email in asset rows.
2. **(Optional, recommended) Register PGP key**

   * User uploads ASCII-armored public key → backend stores: `{fingerprint, public_key, user_id}`.
   * You already have `/api/pgp/register`.
3. **Watermark upload**

   * User selects **claim\_text** (default = `“owner:<email_hash>”` or `“owner:<user_uuid>”`).
   * Client (or server) signs `claim_text` with the user’s PGP **private** key (client-side preferred).
   * Call `/api/watermark/image` with: file, `claim_text`, and optional `pgp_public_key` + `pgp_signature`.
   * Backend embeds `ECC(SHA256(claim_text))`, verifies PGP if present, and stores a **MediaAsset** row:

     ```
     { asset_id, user_id, email_hash, pgp_fingerprint?, params, sha256_file, created_at }
     ```
   * Return watermarked PNG to the user for sharing.

## B) Prove later (verification flow)

1. **User uploads a candidate image** (downloaded from social media, or found on the web).
2. Backend **extracts payload** → `ECC(SHA256(claim_text*))` and tries to recover the hash.
3. It then **looks up** the original **claim\_text** by checking:

   * If the user supplies a candidate claim (e.g., `owner:<email_hash>`), compare directly.
   * Or search your DB for assets whose `claim_text` hash matches the recovered payload (store the **hash of claim\_text** with each asset to make this exact match O(1)).
4. If the asset is found:

   * Check DB link to `user_id` (ownership).
   * If the asset has a `pgp_fingerprint`, show **“PGP-verified author”**.
5. Return a **verdict**: owned / likely owned / not owned, with confidence and metadata.

---

# 3) PII & privacy-by-design

### What to store

* **Accounts table**: `id`, `email_hash` (SHA256 of normalized email), `created_at`, **raw email** only if you must send emails. If stored, keep it separate and encrypted at rest.
* **PGP keys**: `fingerprint`, `public_key_armored`, `user_id`, `created_at`.
* **Assets**:

  * `asset_id`, `user_id`, `email_hash` (copy for quick filter),
  * `claim_text_hash` = SHA256(claim\_text),
  * `pgp_fingerprint?`, `sha256_file`, `params (json)`, `stored_path` (local dev only), `created_at`.

> **Do not store raw PII inside the watermark.** Use `claim_text = "owner:<email_hash>"` or `"owner:<user_uuid>"`. This is stable, non-identifying on its own, and easily matchable.

### Data retention

* Keep **raw uploads** only while processing. Store **only** finished, watermarked outputs that users choose to keep.
* Allow **delete** on keys and assets; cascade deletes.

### Consent & transparency

* On “Register Key” and “Watermark” pages: state what is stored (hashes, fingerprints, file hashes) and why.

---

# 4) Security & abuse controls

* **PGP signing:** Always verify detached signature **server-side** against the exact `claim_text`. Store only fingerprint + signature blob for audit.
* **Rate limits:** per account/IP for “verify” and “register” endpoints.
* **File hygiene:** accept images up to X MB; re-encode to PNG; reject malicious content types.
* **Audit logs:** `who`, `what`, `when` for watermarking and verification actions.
* **Integrity:** store `sha256_file` of watermarked output; helpful for later legal workflows.

---

# 5) Minimal UI to make this “feel complete”

### Watermark page

* Inputs: image file, “Link ownership to” (default `My account`), advanced box: custom `claim_text` and “Attach PGP signature” (auto-sign with local key if present).
* Output: download watermarked image + JSON receipt (asset\_id, claim\_text\_hash, pgp\_fingerprint?, params, psnr/ssim).

### Verify page

* Inputs: candidate image; optional “I think the claim is X” (pre-filled with `owner:<my_email_hash>`).
* Output:

  * ✅ **Owned**: shows matched asset, date, PGP badge (if any).
  * ⚠️ **Likely owned**: recovered but not in DB (e.g., older export) → let user submit the original claim text to prove.
  * ❌ **Not owned**: explanation and next steps.

---

# 6) Concrete backend glue you may still add (very small)

1. **Claim text hashing at ingest** (store for fast lookup):

```python
claim_text_hash = hashlib.sha256(claim_text.encode("utf-8")).hexdigest()
# persist in MediaAsset.claim_text_hash
```

2. **Verify route** (search by recovered payload → claim\_text\_hash):

* After ECC decode, compare to `SHA256(claim_text)` for all user assets, or accept `claim_text` input and compare directly.
* If match found, return `{owned: true, asset_id, user_id, pgp_verified: bool}`.

3. **Email hash helper**

```python
def email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()
```

Use `claim_text = f"owner:{email_hash(user.email)}"` by default.

---

# 7) Threat model (quick)

* **Replay / scraping:** Someone could re-share your watermarked image—that’s fine; it still proves your claim.
* **Key compromise:** If a PGP private key is compromised, the attacker could sign new claims; allow key revocation and re-registration.
* **False positives:** Use ECC\_ok + high bit similarity threshold + DB lookup → “owned” only when all align.
* **Targeted edits:** Crops/resizes recompress; your generic pre-processing + Y-channel QIM + repetition≥120 keeps robustness. Add tiling if needed later.

---

# 8) What to test now (no more code, just validation)

1. **Default claim = email hash**

   * Register, watermark with `owner:<email_hash>`, share via WhatsApp/IG, verify from a different device/account.
2. **PGP-bound claim**

   * Register PGP, sign `claim_text`, watermark with signature attached, verify later and ensure DB shows fingerprint and verification badge.
3. **Cross-account check**

   * Upload a stranger’s image → verify → should not match your assets.

---

# 9) Why this is “proper”

* **PII minimized**: only hashes in watermarks & asset rows; raw email isolated.
* **Ownership = (pixels + identity + account)**: each orthogonal, together very strong.
* **MVP-ready**: uses your current modules; only light DB field additions and one small verify search.

If you want, I can write the tiny `verify` API that accepts an image and (optionally) a `claim_text`, and returns the ownership verdict exactly as described.











curl -X POST http://127.0.0.1:8000/api/watermark/image/extract \
  -F "file=@D:/Teaching/Upwork/KLYVO/IMG_5966.JPG" \
  -F "use_y_channel=true" \
  -F "use_ecc=true" \
  -F "ecc_parity_bytes=64" \
  -F "qim_step=24.0" \
  -F "repetition=240" \
  -F "check_text=owner:b6606a0ac49b39edbe86b7607602ce5990d2f63b7e93d97395e5dcf56b85f6ad"


b6606a0ac49b39edbe86b7607602ce5990d2f63b7e9



curl -s http://127.0.0.1:8000/api/auth/me \
  -H "Authorization: Bearer ZtV6fNrMxYSiOcEAGAr8YayMJOIzcDiJ"




  curl -s -D - -o fb_post_water4.png http://127.0.0.1:8000/api/watermark/image \
  -F "file=@D:/Teaching/Upwork/KLYVO/resized_2.png" \
  -F "text=klyvo demo" \
  -F "use_y_channel=true" \
  -F "qim_step=24.0" -F "repetition=160" \
  -F "use_ecc=true" -F "ecc_parity_bytes=64"


  curl -X POST http://127.0.0.1:8000/api/watermark/image/extract \
  -F "file=@fb_post_water4.png" \
  -F "use_y_channel=true" \
  -F "use_ecc=true" \
  -F "ecc_parity_bytes=64" \
  -F "qim_step=24.0" \
  -F "repetition=160" \
  -F "check_text=klyvo demo"


curl -X POST http://127.0.0.1:8000/api/watermark/image/extract \
  -F "file=@D:/Teaching/Upwork/KLYVO/fb_post_download5.jpg" \
  -F "use_y_channel=true" \
  -F "use_ecc=true" \
  -F "ecc_parity_bytes=64" \
  -F "qim_step=24.0" \
  -F "repetition=160" \
  -F "check_text=klyvo demo"