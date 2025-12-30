## Klyvo Monorepo

Monorepo for web, mobile, and backend services.

### Structure

- `apps/web`: React (Vite + TypeScript)
- `apps/mobile`: Expo React Native (TypeScript)
- `apps/api`: FastAPI (Python)
- `packages/ui`: Shared UI components
- `packages/tsconfig`: Shared TypeScript config
- `infra/azure`: Azure IaC placeholders
- `infra/docker`: Docker Compose for local dev
  
Root run scripts:

```json
{
  "web:dev": "npm --workspace @klyvo/web run dev",
  "web:build": "npm --workspace @klyvo/web run build",
  "web:preview": "npm --workspace @klyvo/web run preview",
  "mobile:start": "npm --workspace @klyvo/mobile run start"
}
```

### Prerequisites

- Node.js 20+
- npm 9+
- Python 3.11+
- Docker (optional, for containerized runs)

### Getting Started

#### Web

```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:5173`.

#### API (FastAPI)

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
set PYTHONPATH=src
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API docs.

#### Mobile (Expo)

```bash
cd apps/mobile
npm install
npm run start
```

Use the Expo app or emulator to run iOS/Android; `npm run web` to try the web build.

### Workspace scripts

From the repo root (once dependencies are installed):

```bash
npm run web:dev
npm run web:build
npm run web:preview
npm run mobile:start
```

### Environment Variables

- Copy `apps/api/.env.example` to `.env` and edit values as needed.

### Docker

Build and run API in Docker:

```bash
cd apps/api
docker build -t klyvo-api .
docker run -p 8000:8000 klyvo-api
```

### Notes

- The mobile app is scaffolded minimally; install Expo SDK/tooling to run on devices.
- Shared UI lives in `packages/ui` and can be imported as `@klyvo/ui` from web.











## ✅ Current Status — End of Milestone 1

**Goal of Milestone 1:**

> “Upload + watermark pipeline working with pseudonymous user identity (UUID + DCT/FFT + SHA-256 + PGP key flow).”

### 1. Functional Achievements

| Component                   | Status | Notes                                                                                                 |
| --------------------------- | ------ | ----------------------------------------------------------------------------------------------------- |
| **Frontend (React + Vite)** | ✅      | Auth, upload UI, Image & Video WM/Verify pages, clean nav header, color fixes, uses `email_sha` claim |
| **Backend (FastAPI)**       | ✅      | Modular watermarking engine for image + video (DCT/Y-channel + ECC)                                   |
| **PGP Key Flow**            | ✅      | Local PGP pair generation + save + optional upload                                                    |
| **Watermark Identity**      | ✅      | `owner:<email_sha>` (pseudonymous SHA-256 of email ID)                                                |
| **End-to-End Verification** | ✅      | Round-trip tests through WhatsApp/Facebook – ECC OK & hash match                                      |
| **FFmpeg Integration**      | ✅      | Auto resize + preset simulation for WhatsApp/Facebook before embedding                                |
| **CORS / API integration**  | ✅      | Frontend ↔ FastAPI communication verified locally                                                     |

**✅ Result:**
A working prototype that watermarks images and videos with a pseudonymous user claim and verifies authenticity even after social-media recompression.

---

## ⚙️ Technical Deep-Dive (What we built)

* **Video Watermarking:** Frame-wise DCT embedding, ECC (64-byte parity), repetition 240 frames, Y-channel based embedding.
* **Image Watermarking:** FFT/DCT hybrid with text-based payload.
* **Frontend Flow:** Email → SHA256 → claim → embed → verify.
* **Security Layer:** Local PGP pair ensures cryptographic identity binding.
* **Testing Pipeline:** Direct → WhatsApp → download → verify (success ~0.96 similarity).

---

## 🧭 Improvement Opportunities before Milestone 2

1. **Backend Optimization**

   * Convert FFmpeg subprocess calls → async `aiofiles` or background tasks for faster multi-video processing.
   * Add caching for common presets (“whatsapp”, “instagram”).

2. **Robustness & Error Handling**

   * More consistent exception responses (JSON errors for all routes).
   * Auto-cleanup old temp files (`/home/data/tmp*`).

3. **Frontend Enhancements**

   * Progress bar for video upload/encode.
   * Unified UI theme (polish header + buttons to look consistent).

4. **Security**

   * Replace “allow_origins=['*']” CORS with specific domain once Azure deployed.
   * Token-based auth headers for API calls.

5. **Deployment Readiness**

   * Dockerfile finalized ✅ but we still need Azure App Service container config + SWA build workflow.

---

## 🎯 Next Focus — **Milestone 2**

> “ERC-721 Minting on Polygon Testnet  |  IPFS Metadata Storage  |  Ownership Record Viewer”  (25%)

### 🔧 Objective

Extend watermarking to produce an **on-chain ownership record**:

* Each successful watermark upload creates a **minted NFT** (ERC-721) on Polygon Testnet.
* Metadata (JSON) stored on **IPFS** linking to:

  * SHA-256 hash of the file
  * Watermark payload (`owner:<email_sha>`)
  * Timestamp and PGP pubkey (optional)
* A **record viewer page** displays NFT details & verifies ownership on-chain.

### 🪄 Core Components to Build

| Sub-Module                   | Description                                                                   |
| ---------------------------- | ----------------------------------------------------------------------------- |
| **Smart Contract (ERC-721)** | Deploy via Hardhat or Foundry on Polygon Amoy / Mumbai Testnet                |
| **Mint API**                 | FastAPI route (`/api/mint`) → interacts with Web3 provider to mint NFT        |
| **IPFS Integration**         | Pin JSON metadata + preview on Pinata / NFT.storage                           |
| **Ownership Viewer**         | New frontend page that reads NFT metadata & IPFS link, shows ownership record |
| **Wallet Connect**           | Optional MetaMask login for advanced users (matching `email_sha` to wallet)   |

---

## 🔜 Recommended Next Steps

1. ✅ Freeze Milestone 1 code branch (tag v1.0 prototype).
2. 🧩 Create new branch `milestone-2-nft-integration`.
3. ⚙️ Set up Hardhat workspace (`apps/contracts/`).
4. 🎯 Deploy basic ERC-721 contract on Polygon Amoy Testnet.
5. 🧵 Integrate FastAPI mint route + IPFS metadata upload.
6. 🖼 Build “Ownership Record Viewer” page in React.

---

If you want, I can next:

* 📁 Set up the **Hardhat project structure + ERC-721 contract template**, or
* 💻 Start with **FastAPI ↔ Web3.py integration for minting**, or
* 🧠 Design the **metadata schema (JSON + IPFS storage layout)** first.

Which direction do you want to begin with for Milestone 2?
