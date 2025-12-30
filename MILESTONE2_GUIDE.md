Here’s the **complete README-style document** for **Milestone 2** — ready to be dropped into your repository (e.g. as
`docs/MILESTONE2_GUIDE.md` or appended to your main `README.md`).
It includes every detail and keeps technical clarity consistent with your project tree.

---

# 🧩 Milestone 2 — Blockchain Anchoring & Ownership Registry

**(Part of the Klyvo Project Roadmap)**

---

## 🎯 Objective

Milestone 2 extends Klyvo beyond watermarking and verification by introducing **on-chain ownership anchoring** using **Polygon testnet**.
Every watermarked image or video will now generate a **verifiable proof record** on blockchain and, optionally, an **IPFS metadata entry**.
This ensures permanent, tamper-proof ownership validation.

---

## ✅ Core Deliverables

| # | Deliverable                    | Description                                                                                                                                    |
| - | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | **Smart Contract Registry**    | A minimal `ProofRegistry.sol` smart contract deployed to Polygon testnet (Mumbai / Amoy) to store file-hash + owner ID + timestamp + IPFS CID. |
| 2 | **Backend (Web3 Integration)** | FastAPI service that anchors proofs, verifies existing records, and (optionally) lists user history.                                           |
| 3 | **Frontend Integration**       | Buttons in Image / Video Watermark and Verify pages for “Anchor on-chain” and “Check on-chain”.                                                |
| 4 | **Optional IPFS Storage**      | Uploads metadata JSON (filename, type, sha256, email SHA) to IPFS, storing returned CID on-chain.                                              |
| 5 | **Docs + Testing**             | Full documentation, API examples, and local curl tests for `/anchor` and `/verify`.                                                            |

---

## 🧱 Project Structure Overview

You already have:

```
apps/api/src/app/services/watermarking/   # watermark logic (image/video)
apps/api/src/app/api/routes/              # FastAPI routes
apps/web/src/pages/                       # React UI pages
infra/azure / infra/docker                # deployment setup
```

Milestone 2 adds a **blockchain registry layer** inside
`apps/api/src/app/services/blockchain/`:

```
services/blockchain/
├── __init__.py
├── config.py
├── client.py
├── registry.py
├── ipfs.py                 # optional helper
├── abi/
│   └── ProofRegistry.json  # compiled contract ABI
└── contracts/
    └── ProofRegistry.sol   # Solidity source
```

---

## 🪙 Step-by-Step Guide

### 1️⃣  Smart Contract Creation & Deployment

**File:**
`apps/api/src/app/services/blockchain/contracts/ProofRegistry.sol`

**Example Solidity Contract:**

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ProofRegistry {
    struct Proof {
        bool exists;
        bytes32 ownerEmailSha;
        uint256 timestamp;
        string ipfsCid;
    }

    mapping(bytes32 => Proof) private proofs;

    event ProofRegistered(bytes32 indexed fileHash, bytes32 indexed emailSha, string ipfsCid, uint256 timestamp);

    function registerProof(bytes32 fileHash, bytes32 emailSha, string calldata ipfsCid) external {
        require(!proofs[fileHash].exists, "Already registered");
        proofs[fileHash] = Proof(true, emailSha, block.timestamp, ipfsCid);
        emit ProofRegistered(fileHash, emailSha, ipfsCid, block.timestamp);
    }

    function getProof(bytes32 fileHash)
        external
        view
        returns (bool exists, bytes32 ownerEmailSha, uint256 timestamp, string memory ipfsCid)
    {
        Proof memory p = proofs[fileHash];
        return (p.exists, p.ownerEmailSha, p.timestamp, p.ipfsCid);
    }
}
```

**Compile & Deploy:**

```bash
npx hardhat compile
npx hardhat run scripts/deploy.js --network polygonMumbai
```

Store in `.env`:

```env
PROOF_CONTRACT_ADDRESS=0xYourDeployedAddress
PROOF_CONTRACT_ABI_PATH=src/app/services/blockchain/abi/ProofRegistry.json
WEB3_RPC_URL=https://polygon-mumbai.infura.io/v3/<KEY>
WEB3_PRIVATE_KEY=0x<PRIVATE_KEY>
WEB3_CHAIN_ID=80001
```

---

### 2️⃣  Backend Integration (FastAPI + Web3)

**Add new service:**
`apps/api/src/app/services/blockchain/registry.py`

Handles:

* connection to Web3
* contract interaction
* proof anchoring / verification / history

**Routes (new file):**
`apps/api/src/app/api/routes/registry.py`

| Endpoint                | Method           | Description                            |
| ----------------------- | ---------------- | -------------------------------------- |
| `/api/registry/anchor`  | `POST`           | Anchors a new proof on blockchain      |
| `/api/registry/verify`  | `GET`            | Checks if a file hash is anchored      |
| `/api/registry/history` | `GET` (optional) | Lists previous proofs for an email SHA |

**Example anchor payload:**

```json
{
  "email_sha": "6c8f1d8a4c...",
  "file_sha256": "b1946ac92492d2347c6235b4d2611184",
  "kind": "image",
  "filename": "watermarked.png"
}
```

**Response:**

```json
{
  "tx_hash": "0x8a9c...",
  "block_number": 4782112,
  "ipfs_cid": "bafybeifkq...",
  "status": "anchored"
}
```

---

### 3️⃣  IPFS Metadata (Optional)

**File:**
`apps/api/src/app/services/blockchain/ipfs.py`

Use Pinata / nft.storage API to upload metadata:

```python
{
  "filename": "watermarked.png",
  "kind": "image",
  "sha256": "b1946ac9249...",
  "email_sha": "6c8f1d8a4c..."
}
```

Return `ipfs_cid` → store on-chain.

`.env` additions:

```env
IPFS_BASE_URL=https://api.nft.storage
IPFS_API_KEY=<your_api_key>
```

---

### 4️⃣  Frontend Enhancements (React + Vite)

**Files to update:**

```
apps/web/src/lib/api.ts
apps/web/src/pages/Watermark.tsx
apps/web/src/pages/VideoWatermark.tsx
apps/web/src/pages/VerifyOwnership.tsx
apps/web/src/pages/VideoVerify.tsx
```

**Workflow:**

1. After successful embed:

   * Compute SHA-256 of output file (already returned from backend).
   * Show **“Anchor on-chain”** button.
   * Call `POST /api/registry/anchor`.

2. Show feedback:

   * Tx hash, IPFS CID, “View on Polygonscan”.

3. On Verify pages:

   * Keep existing watermark verification.
   * Add **“Check on-chain”** → `/api/registry/verify`.
   * Display:

     * Owner Email SHA
     * Timestamp
     * IPFS link
     * Verified status ✅ / ❌

*(All styling can reuse existing gradient buttons and card layout.)*

---

### 5️⃣  Local Testing via Curl

**Anchor:**

```bash
curl -s -X POST http://127.0.0.1:8000/api/registry/anchor \
  -H "Content-Type: application/json" \
  -d '{"email_sha":"<EMAIL_SHA>","file_sha256":"<FILE_SHA>","kind":"image","filename":"test.png"}'
```

**Verify:**

```bash
curl -s "http://127.0.0.1:8000/api/registry/verify?file_sha256=<FILE_SHA>"
```

Expected output:

```json
{
  "exists": true,
  "owner_email_sha": "6c8f1d8a4c...",
  "timestamp": 1733781045,
  "ipfs_cid": "bafybeifkq...",
  "tx_hash": "0x8a9c..."
}
```

---

### 6️⃣  Optional DB Caching

Add `Proof` model in `apps/api/src/app/db/models.py`:

```python
class Proof(Base):
    __tablename__ = "proofs"
    file_hash = Column(String, primary_key=True)
    email_sha = Column(String, nullable=False)
    ipfs_cid = Column(String)
    tx_hash = Column(String)
    chain_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
```

Populate after every successful anchor to serve `/history`.

---

### 7️⃣  Security & Ops

* Private keys never checked into Git.
* Add `.env` to `.gitignore` (safe by default).
* Rate-limit `/anchor` and log tx hashes.
* Add health-check endpoint:

  ```
  GET /api/registry/health → { "connected": true, "chain_id": 80001 }
  ```
* Use HTTPS when deploying.

---

### 8️⃣  Documentation & Tagging

**Files to update:**

* `README.md` — add section *“Blockchain Anchoring”*
* `infra/azure/README.md` — mention Web3 ENV vars
* `apps/api/requirements.txt` — add `web3`, `python-dotenv`
* Commit:

  ```bash
  git add .
  git commit -m "Milestone 2: Blockchain anchoring + Polygon integration"
  git tag -a v1.1-milestone2 -m "Milestone 2 complete"
  ```

---

## 📦 Milestone 2 Timeline (Recommended)

| Day | Task                                            | Output                  |
| --- | ----------------------------------------------- | ----------------------- |
| 1–2 | Contract creation + deployment (Mumbai/Amoy)    | Contract address + ABI  |
| 3   | Backend Web3 service + anchor/verify routes     | Working API             |
| 4   | Frontend buttons + integration with existing UI | User-visible feature    |
| 5   | Docs + local testing + tag release              | Tagged v1.1 Milestone 2 |

---

## 🧠 Stretch Enhancements (Phase 2.1)

| Feature               | Description                                       |
| --------------------- | ------------------------------------------------- |
| **ERC-721 Minting**   | Each proof mints a lightweight NFT for ownership. |
| **Batch Anchoring**   | Allow multiple proofs in one tx.                  |
| **Meta-transactions** | User signs client-side; backend relays.           |
| **Event listeners**   | Sync on-chain events → local DB.                  |
| **Transfer / Revoke** | Ownership re-assignment logic.                    |

---

## ✅ Acceptance Criteria

* ✅ User can **embed image/video watermark** → compute SHA-256
* ✅ “Anchor on-chain” creates Polygon transaction + optional IPFS CID
* ✅ Verification checks both local watermark + on-chain record
* ✅ Secrets remain server-side
* ✅ Works on Polygon testnet (Mumbai or Amoy)

---

## 🔐 Example .env Configuration

```env
# Blockchain
WEB3_RPC_URL=https://polygon-amoy.g.alchemy.com/v2/<API_KEY>
WEB3_PRIVATE_KEY=0x...
WEB3_CHAIN_ID=80002
PROOF_CONTRACT_ADDRESS=0x...
PROOF_CONTRACT_ABI_PATH=src/app/services/blockchain/abi/ProofRegistry.json

# Optional IPFS
IPFS_BASE_URL=https://api.nft.storage
IPFS_API_KEY=<TOKEN>

# Database
SQLALCHEMY_DATABASE_URL=sqlite:///./klyvo_dev.db
```

---

## 🧩 Final Outcome

After completing Milestone 2:

* Klyvo users can **prove ownership** of any watermarked file on blockchain.
* Each proof is **immutable, timestamped, and verifiable**.
* The registry is **auditable via Polygonscan** and optionally linked to IPFS metadata.
* The system remains **privacy-preserving**, storing only SHA-256 hashes + email SHA identifiers.

---

> **Milestone 3 Preview:**
> Introduce AI-based watermark resilience (EfficientNet-B7 decoder + adversarial robustness testing) to recover altered media and re-verify ownership even after compression, cropping, or editing.

---

✅ **End of Milestone 2 README Guide**
*(Drop this file as `docs/MILESTONE2_GUIDE.md` and commit before starting implementation.)*



















Perfect — here’s your **complete “from-zero to working” guide** for everything you did in **Milestone 2**, with special focus on *setting up Polygon Amoy, faucet funding, wallet, and contract deployment*.
This captures **every real-world action you performed** in the correct order — so you can reproduce it later or document it for your repo README.

---

# 🚀 Milestone 2 – Web3 Integration (End-to-End Working Steps)

---

## **STEP 1 – Polygon Amoy Environment Setup**

### 1️⃣ Create a Wallet

* You used [**MetaMask**](https://metamask.io/).
* On install/open → click **“Create a new wallet”**.
* Save the 12-word seed phrase safely (offline).
* Copy your public address → it starts with `0x…`.

---

### 2️⃣ Add the Polygon Amoy Test Network

> Amoy replaced the old Mumbai testnet.

**Automatic:**

* Visit 👉 [https://amoy.polygonscan.com/](https://amoy.polygonscan.com/) and click **“Add Network to MetaMask”**.

**Manual (if needed):**

```
Network Name: Polygon Amoy
RPC URL: https://rpc-amoy.polygon.technology/
Chain ID: 80002
Currency Symbol: POL
Block Explorer: https://amoy.polygonscan.com/
```

MetaMask → Networks dropdown → Add network → Custom → enter above details → Save.

---

### 3️⃣ Get Test POL Tokens (from Faucet)

* Visit 👉 [https://faucet.polygon.technology/](https://faucet.polygon.technology/)
* Connect your MetaMask wallet → select **Polygon Amoy**.
* Click **“Request tokens”** → you’ll get ≈ 0.2–0.5 POL for testing.
* Confirm in MetaMask → you should see `0.2 POL` balance.

---

### 4️⃣ Create an Environment File for Hardhat and Backend

In `apps/api/.env`:

```
WEB3_RPC_URL=https://rpc-amoy.polygon.technology/
WEB3_CHAIN_ID=80002
WEB3_PRIVATE_KEY=0x<private_key_of_your_test_wallet>
PROOF_CONTRACT_ABI_PATH=src/app/services/blockchain/abi/ProofRegistry.json
```

> ⚠️ Use a **throwaway wallet** for tests — never store real keys in code.

---

### 5️⃣ Verify RPC Connection (quick test)

```bash
npx hardhat console --network amoy
> (await ethers.provider.getBlockNumber()).toString()
```

If you see a block number → your RPC and wallet are working.

---

## **STEP 2 – Smart Contract Creation and Deployment**

### 1️⃣ Smart Contract

You wrote `ProofRegistry.sol` to store file and email hash proofs and emit events.

---

### 2️⃣ Hardhat Setup

```bash
cd apps/api/chain
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox
```

Configured `hardhat.config.ts` for Amoy network and private key.

---

### 3️⃣ Deploy Script

`npm run deploy:amoy`
→ compiled → deployed to Amoy.
Output showed:

```
✅ Deployed at: 0xF320F6E81045506379a875747588E8B3e280FEB7
📝 ABI written: .../ProofRegistry.json (bytes > 0)
🗂 Address written: .../ProofRegistry.address.json
```

Contract appeared on [amoy.polygonscan.com](https://amoy.polygonscan.com).

---

### 4️⃣ Verify (Explorer)

Optional Polygonscan API key lets you auto-verify; otherwise skip and check manually by address.

---

## **STEP 3 – Backend Integration**

### 1️⃣ Dependencies

Installed in `.venv`:

```bash
pip install web3 eth-account python-dotenv fastapi uvicorn
```

---

### 2️⃣ Smart Contract Binding

* The ABI and address from Hardhat deployment were copied to:

  ```
  apps/api/src/app/services/blockchain/abi/
      ProofRegistry.json
      ProofRegistry.address.json
  ```
* `client.py` loads them and creates a `Web3Client`.

---

### 3️⃣ Backend Environment

Same `.env` used by both Hardhat and FastAPI:

```
WEB3_RPC_URL=…
WEB3_CHAIN_ID=80002
WEB3_PRIVATE_KEY=0x…
PROOF_CONTRACT_ADDRESS=0xF320F6E81045506379a875747588E8B3e280FEB7
PROOF_CONTRACT_ABI_PATH=src/app/services/blockchain/abi/ProofRegistry.json
```

---

### 4️⃣ Run the Backend

```bash
uvicorn app.main:app --reload
```

---

### 5️⃣ Test Endpoints (via Swagger UI or cURL)

**Anchor a proof:**

```bash
curl -X POST "http://127.0.0.1:8000/api/registry/anchor" \
  -H "Content-Type: application/json" \
  -d '{
   "email_sha": "b27db98bcebf…",
   "file_sha256": "b27db98bcebf…",
   "kind": "image",
   "filename": "fb_post_water.png",
   "ipfs_cid": ""
  }'
```

✅ Response:

```json
{
 "tx_hash": "0x4be8d76d...",
 "block_number": 27613977,
 "status": "anchored"
}
```

→ confirmed transaction on Polygonscan.

**Verify proof:**

```bash
curl "http://127.0.0.1:8000/api/registry/verify?file_sha256=<same_hash>"
```

✅ Response:

```json
{
 "exists": true,
 "owner_email_sha": "0xb27d…",
 "timestamp": 169xxyyzz,
 "ipfs_cid": ""
}
```

If you query a different hash → `exists:false` (as you observed).

---

## **STEP 4 – Confirm on Explorer**

* Visit **[https://amoy.polygonscan.com/tx/](https://amoy.polygonscan.com/tx/)<tx_hash>**
* You’ll see your deployer address and ProofRegistry event.
* Contract events confirm that `registerProof` executed and stored the hashes.

---

# ✅ Summary – What’s Achieved Now

| Layer          | Component                                        | Status |
| :------------- | :----------------------------------------------- | :----- |
| Blockchain     | Polygon Amoy network + wallet funded from faucet | ✅      |
| Smart Contract | ProofRegistry.sol compiled and deployed          | ✅      |
| Backend        | FastAPI + Web3 client connected to Amoy          | ✅      |
| Anchoring      | `/api/registry/anchor` writes on-chain proofs    | ✅      |
| Verification   | `/api/registry/verify` reads on-chain proofs     | ✅      |
| Explorer       | Polygonscan shows tx and events                  | ✅      |

---

# 💡 Next Milestone Preview

**Step 3 (IPFS metadata + storage):**

* Upload metadata JSON to Pinata or nft.storage and store CID in `ipfs_cid` field.
* Include CID in `anchor` payload so it’s recorded on-chain.

**Step 4 (Frontend integration):**

* Connect UI buttons for “Anchor on Chain” and “Verify Proof” → show tx hash and Polygonscan link.

---

Would you like me to document the **exact wallet-funding and key-export steps** you used inside MetaMask (exporting PK for .env safely, verifying balance, etc.) so it’s audit-ready for your internal README?















| Priority | Task                               | Description                                                                                                          |
| -------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| ⭐ Next   | **Frontend wiring**                | Build “My Media” dashboard → List media IDs via `/api/media/owner/{sha}` and trigger verify via `/api/verify/auto`.  |
| ✅        | **Add audit logging**              | Save each `/verify/auto` run in a `verification_logs` table (owner, media_id, preset, ecc_ok, timestamp, client_ip). |
| ⚙️       | **Add revoke/deactivate endpoint** | Allow marking a media_id inactive (PATCH `/api/media/{id}` → `{active:false}`).                                      |
| 🧱       | **Add server-side indexing**       | Add DB indexes on `owner_email_sha`, `media_id` for faster lookups.                                                  |
| 🧪       | **Unit tests**                     | Add pytest suite for watermark/verify/sha endpoints.                                                                 |












Awesome—here’s a clean plan to refactor the frontend into the flow you want, re-using your existing patterns and backend endpoints. I’m not writing code yet; this is the “what & how” so we can implement step-by-step next.

# What you already have (why this will be easy)

* **Auth pattern is in place.** `Login.tsx` logs in, normalizes email, computes `email_sha`, saves `{token, uuid, email, email_sha}` to local storage, and redirects (currently to `#/watermark`). 
* **Fetch + form-data flow is in place.** `Home.tsx` shows how you build `FormData`, call an API, and read JSON/headers; it even demonstrates a “watermark digest build” call pattern we can mimic. 

# Target UX

1. **Login → Dashboard**

   * After login, route to **`#/dashboard`** (instead of `#/watermark`).
   * Dashboard shows **“My Media IDs”** (list the user’s saved `media_ids` with label, created_at, active/revoked, and last verified).

2. **Watermark page**

   * Upload image → choose preset (keep your current list), optional label.
   * On submit, hit **`POST /watermark/image`** with `auto_register_media=true`, `media_label`, and (by default) the logged-in user’s `owner_email_sha`.
   * Show the result (download link + headers like `X-Params-*`, and the `media_id` we computed from `text=<owner:...|media:...>`).

3. **Verify page**

   * Upload an image + choose preset → call **`POST /api/verify/auto?owner_email_sha=…`**.
   * Render the result clearly: ✅ exists + matched `media_id` (or ❌ with similarity/help text).

# Minimal architecture changes

## 1) Routes & Layout

* Add a **top-level `AppLayout`** with a slim header (brand, “Dashboard”, “Watermark”, “Verify”, user email, Sign out).
* Routes:

  * `#/login`
  * `#/dashboard` (default after login)
  * `#/watermark`
  * `#/verify`

## 2) Central auth helper (reuse what you have)

You already store `{token, uuid, email, email_sha}` on login. We’ll:

* Keep those in a tiny `auth.ts` (already present per your code) and expose:

  * `getAuth()` → `{ token, uuid, email, email_sha } | null`
  * `requireAuthOrRedirect()` (guard routes)
* Every API call will include `Authorization: Bearer ${token}` if present (you’re already doing similar patterns).

(Confirmed by your `Login.tsx` flow: it normalizes email, computes `email_sha`, saves auth, and redirects. We’ll only change redirect to `#/dashboard`.) 

## 3) API helpers (thin wrappers)

Create or extend `lib/api.ts` with these thin calls:

* **List media IDs (Dashboard):**
  `GET /media/owner/{email_sha}` → returns array of `{ id, owner_email_sha, media_id, label, active, created_at, revoked_at }`

* **Watermark (Watermark page):**
  `POST /watermark/image` (multipart form):
  fields: `file`, `text` *(we’ll build it as `owner:{email}|media:{media_id}`)*, `preset`, `auto_register_media=true`, `media_label`, (`override_owner_email_sha` only if user wants to force a different email).
  Response: PNG file download; read response headers for params + payload size; we can compute `media_id` deterministically the same way you’re doing now and also show it.

* **Auto-verify (Verify page):**
  `POST /api/verify/auto?owner_email_sha=…&preset=…&use_ecc=true` (multipart form with `file`).
  Response JSON: `{ exists: boolean, ecc_ok?: boolean, match_text_hash?: boolean, similarity?: number, matched_media_id?: string, checked_media_ids: number, payload_bits: number, used_repetition: number, preset: string }`

* **Server SHA helper (already added):**
  `POST /api/hash/email-sha` with `{ email }` → `{ email_sha }`
  (Optional in UI; we can still compute locally like `Login.tsx` does today. )

## 4) Pages—what they render & fetch

### A) Dashboard (`#/dashboard`)

* On mount: read `email_sha` from auth.
* Fetch `GET /media/owner/{email_sha}`.
* Render a table:

  * **Media ID** (mono) • **Label** • **Active** • **Created** • **Last Verified?** (if you store it later)
* Empty state: “No media yet. Go to Watermark to create one.”

### B) Watermark (`#/watermark`)

* UI:

  * File input
  * Preset dropdown (your current set)
  * Text label (optional)
  * Checkbox “Auto-register media id = ON” (default true)
* On submit:

  * Build `text` as:
    `owner:${auth.email}|media:${computedMediaIdHex}`
    (We’ll compute `media_id` from the watermark digest logic you’re already using in `Watermark.tsx` / `Home.tsx`. `Home.tsx` shows the digest preview pattern—same approach, but now standardized.) 
  * POST to `/watermark/image` with the fields above.
  * Show:

    * Download button for the returned file
    * Headers: `X-PSNR-Y`, `X-SSIM-Y`, `X-Payload-Bits`, `X-Params-*` (pretty list)
    * The **computed `media_id`** (and a link “View on Dashboard”).

### C) Verify (`#/verify`)

* UI:

  * File input
  * Preset dropdown
* On submit:

  * Call `/api/verify/auto?owner_email_sha=${auth.email_sha}&preset=${preset}&use_ecc=true`
  * Show:

    * If `exists===true`: big ✅ “Verified” + matched `media_id`
    * Else: ❌ “No match found” + `similarity`, `checked_media_ids` to help users debug

## 5) Small code shifts we’ll make now (no actual code pasted yet)

* **Change Login redirect** to `#/dashboard`. (Minor tweak in `Login.tsx` setTimeout target.) 
* **Add a `Dashboard.tsx`** (new page) that calls the “list my media” endpoint and renders a table.
* **Tidy Watermark page** to:

  * Always include `auto_register_media=true` by default
  * Include `media_label`
  * Build `text` consistently as `owner:${email}|media:${media_id}`
* **Verify page**: switch to the new `/api/verify/auto` call and show the structured result.

# Data flow (end-to-end)

* **Auth**: `Login.tsx` → save `{token, email, email_sha}` → route to Dashboard. 
* **Dashboard**: loads with `email_sha` → `GET /media/owner/{email_sha}` → render list.
* **Watermark**: submit → `/watermark/image` (auto-register on) → user gets download + computed `media_id` → Dashboard list now includes the new one.
* **Verify**: submit → `/api/verify/auto?owner_email_sha=…` → render result.

# Testing checklist (front-to-back)

1. **Login** with any email → lands on **Dashboard** (empty state first time).
2. Go to **Watermark**, upload, choose preset, keep **Auto-register ON**, enter a label → submit.
3. You should:

   * Get a downloadable watermarked image.
   * See `media_id` displayed.
4. Go back to **Dashboard** → the new **media_id** row should appear.
5. Go to **Verify**, upload that watermarked image, same preset → should return **`exists: true`** and show the matched `media_id`.

# What I’ll need from you before I write code

Nothing else right now—you’ve shared enough. I’ll implement this in small PR-sized chunks (Layout/Routes → Dashboard → Watermark flow tweaks → Verify page wiring), keeping styling consistent with your current components and CSS.

Want me to start with the **Dashboard page** and route changes first?
