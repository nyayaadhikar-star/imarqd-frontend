Awesome—here’s a crisp, reality-checked plan for taking your **image watermark** to **video**. I’m laying it out like an engineering brief so you can see scope, complexity, and clean milestones.





# Activate your venv if needed
# cd apps/api

python -m app.services.watermarking.video_embed `
  --in  "C:\Users\Bhaskar Pathak\OneDrive\Desktop\klyvo\video_trial2_pre.mp4" `
  --out "C:\Users\Bhaskar Pathak\OneDrive\Desktop\klyvo\video_trial2_post.mp4" `
  --text "klyvo video" `
  --preset whatsapp `
  --qim 28.0 `
  --rep 240 `
  --ecc 64 `
  --frame-step 1




python -m app.services.watermarking.video_extract `
  --in "C:\Users\Bhaskar Pathak\OneDrive\Desktop\klyvo\video_trial2_post_wa.mp4" `
  --qim 28.0 `
  --rep 240 `
  --frame-step 1 `
  --use-ecc `
  --ecc 64 `
  --check-text "klyvo video"




# Windows PowerShell (no backslashes needed), adjust paths
curl -fS -D - \
  -o wm_out.mp4 \
  -F "file=@C:\Users\Bhaskar Pathak\OneDrive\Desktop\klyvo\video_trial2_pre.mp4" \
  -F "text=klyvo video" \
  -F "preset=whatsapp" \
  -F "frame_step=1" \
  -F "use_ecc=true" \
  -F "ecc_parity_bytes=64" \
  http://127.0.0.1:8000/api/watermark/video




# verify the file you just watermarked (or the WA-downloaded copy)
curl -s -X POST http://127.0.0.1:8000/api/watermark/video/extract \
  -F "file=@C:\Users\Bhaskar Pathak\OneDrive\Desktop\klyvo\video_post_wa.mp4" \
  -F "qim_step=28.0" \
  -F "repetition=240" \
  -F "frame_step=1" \
  -F "use_ecc=true" \
  -F "ecc_parity_bytes=64" \
  -F "check_text=klyvo video"





---

# Goals (what “success” looks like)

* **Claim**: same as images — `owner:{email_sha}` (+ optional PGP signature stored off-media).
* **Robustness v1**: survive common **re-encoding**, **bitrate changes**, **resizing**, and **moderate noise** on social platforms (WhatsApp/Instagram/FB/TikTok/Twitter).
* **Speed**: 1080p clips up to ~60–90s should process within practical time on CPU; GPU optional later.
* **UX**: upload → embed → preview → download; verify on any later upload of the shared video.

---

# Threat Model (video-specific)

Platforms routinely:

* transcode to **H.264/H.265/VP9/AV1** (lossy quantization; variable GOP)
* **resize** (long edge caps: 720p/1080p/4K depending)
* change **fps** (e.g., 60 → 30)
* **re-sample audio** (we’re not touching audio v1)
* possibly **crop/aspect** (less common for standard posts; more for stories/reels)

We’ll target robustness to **codec and size/fps changes** v1. (Crop/rotation robustness → later sync-template work, like we scoped for images.)

---

# Payload Design (unchanged conceptually)

* **Core payload**: `ECC(SHA256(claim_text))` (claim text = `owner:{email_sha}`).
* **Size**: 32 bytes + parity (e.g., 64–96 parity bytes).
* **Tiling**: repeat across many **spatial blocks** and **frames** to survive drops.

---

# Embedding Approach (video)

**Per-frame, block-DCT** on luma (Y-channel), with **temporal redundancy**:

1. **Decode** to frames (FFmpeg).
2. Convert to **YCbCr**; take **Y** plane.
3. For each frame:

   * split into 8×8 or 16×16 blocks;
   * pick mid-frequency DCT coeffs (QIM or spread-spectrum) to embed bits;
   * **partial frame rate embedding** (e.g., every 2–3 frames) for speed/robustness.
4. Reassemble frames → encode (FFmpeg) with a **sane bitrate** to avoid pre-social quality loss.

**Why this works:** Transcoding hits high frequencies first; mid-band DCT survives. Temporal repetition handles dropped/IDR/keyframe differences.

---

# Extraction Approach (video)

1. Decode to frames.
2. For each processed frame, read blocks → DCT → collect embedded bits.
3. **Temporal majority vote** (across frames) + **spatial voting** (across blocks).
4. **ECC decode** → compare to expected `SHA256(claim_text)` during verification.

---

# Robustness Tactics v1 (practical + simple)

* **Platform presets** (like images): pre-resize/bitrate before embedding to match likely platform caps.
* **Temporal sampling** (e.g., embed on 1 frame out of N) to speed up and spread payload.
* **ECC with more parity** than images (e.g., 64–128 bytes).
* **Adaptive QIM step**: a bit higher than images (video will be re-encoded harder).

*(Crop/scale/rotation sync templates → future milestone, similar to image plan.)*

---

# Architecture Changes

## Backend

* **New service**: `services/watermarking/video_embed.py` + `video_extract.py`

  * Decode/encode via **ffmpeg-python** or subprocess FFmpeg.
  * Shared helpers (YCbCr, DCT, QIM) reused from images where possible.
* **Routes**:

  * `POST /watermark/video` → returns MP4 (H.264 baseline/high, AAC passthrough or silent audio).
  * `POST /watermark/video/extract` → JSON result (similar fields to images + frame stats).
* **Presets** (extend existing):

  * e.g., `facebook`, `instagram`, `tiktok`, `whatsapp`, with `(target_res, target_fps, target_bitrate)`.
* **Job model (optional v1)**:

  * For >60s clips, run as background job (RQ/Celery) and stream progress; v1 can be synchronous for short clips.

## Data Model

* Extend `MediaAsset` with:

  * `media_type: "image"|"video"`
  * `duration_secs`, `width`, `height`, `fps`, `codec`, `bitrate_kbps`
  * `wm_params` (json): `qim_step`, `repetition_spatial`, `repetition_temporal`, `ecc_parity_bytes`, `preset`, etc.
  * thumbnails (first frame) for UI.

*(You can add columns later via migration; for now, JSON `params` is fine.)*

## Frontend

* New **Watermark (Video)** tab & **Verify (Video)** tab:

  * **Upload video** → pick social preset → show estimated processing time → progress bar.
  * After embedding, render a **thumbnail** and a short **N-sec preview**.
  * Verify page: upload received video → choose preset used (or “auto”) → extract → show verdict.

---

# Complexity & Performance

* **Compute**: per-frame DCT on HD is heavy on CPU; consider:

  * Downscaling to preset long-edge before embedding to reduce blocks.
  * Embedding every 2nd/3rd frame.
  * Optionally: **GPU** later (cuFFT/cuDNN is overkill initially; OpenCV + NumPy is fine).
* **I/O**: FFmpeg transcode dominates run time; tune threads and CRF/bitrate.
* **Memory**: stream frames (don’t load entire video).

---

# Test Matrix (v1)

1. **Local roundtrip**: embed → extract (no re-encode).
2. **Self re-encode**: re-encode to target H.264 CRF values (e.g., CRF 23/28/32).
3. **Preset resize**: 4K→1080p; 1080p→720p; fps 60→30.
4. **Platform simulation**:

   * WhatsApp: H.264 720pish, ~1–2 Mbps.
   * Instagram feed: 1080p, H.264 ~3–5 Mbps.
   * Facebook: 720/1080p ladder; longer GOP.
5. **Edge**: short clips (<3s), muted audio, variable frame-rate input.

---

# Milestones

**M1 – MVP embed/extract (2–4 days)**

* FFmpeg decode/encode, per-frame Y-DCT QIM embedding, temporal repetition, ECC across time.
* API endpoints + minimal UI, local verification.

**M2 – Presets & robustness (2–3 days)**

* Platform presets (res/fps/bitrate), adaptive QIM step, stronger ECC.
* Quick self-reencode tests.

**M3 – UX + background jobs (2–4 days)**

* Progress, thumbnails, short preview, background workers for long clips.

**M4 – Hardening (later)**

* Sync template for crop/rotation/scale; model-based recovery.

---

# Concrete Technical Choices (recommended)

* **FFmpeg**: `ffmpeg` CLI via `subprocess` (reliable, fast) or `ffmpeg-python` wrapper.
* **Codecs**: H.264 baseline/high; `-pix_fmt yuv420p`; CRF-based control.
* **Frame access**: pipe raw frames to Python (RGB24 or YUV) or write temp PNGs (slower, simpler v0).
* **Embedding**: reuse image **8×8 DCT** code; multiply repetition across **blocks × frames**.
* **ECC**: Reed–Solomon (your current), parity 64–128 bytes.

---

# Risks & Mitigations

* **Severe platform compression** → increase repetition & ECC; embed only mid-band coeffs.
* **Long clips** → background jobs, stream results.
* **Audio changes** → ignore audio in v1.

---

If you’re happy with this plan, I can draft:

1. the **backend route signatures** and scaffolding for `video_embed.py`/`video_extract.py`,
2. the **FFmpeg command lines** we’ll use for decode/encode, and
3. a minimal **Verify Video** page that mirrors your image flow.
