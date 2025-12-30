import io
from pathlib import Path
from PIL import Image
import numpy as np
from fastapi.testclient import TestClient

# import the FastAPI app
from apps.api.src.app.main import app

client = TestClient(app)

def _make_gray_image(w=256, h=256):
    arr = np.linspace(0, 255, num=w*h, dtype=np.uint8).reshape(h, w)
    im = Image.fromarray(arr, mode="L")
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    buf.seek(0)
    return buf

def test_watermark_and_extract_roundtrip():
    # 1) Create synthetic grayscale image
    img_buf = _make_gray_image()

    # 2) Call watermark endpoint
    text = "klyvo-demo"
    files = {"file": ("synthetic.png", img_buf, "image/png")}
    data = {"text": text, "qim_step": "8.0", "repetition": "20"}
    resp = client.post("/watermark/image", files=files, data=data)
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("image/")

    # Save the returned file to re-upload for extraction
    wm_bytes = resp.content

    # 3) Call extract endpoint with check_text
    files = {"file": ("wm.png", io.BytesIO(wm_bytes), "image/png")}
    data = {"payload_bitlen": "256", "qim_step": "8.0", "repetition": "20", "check_text": text}
    x = client.post("/watermark/image/extract", files=files, data=data)
    assert x.status_code == 200
    body = x.json()
    assert body["payload_bitlen"] == 256
    assert body["recovered_hex"]  # non-empty
    # similarity should be well above random; allow some slack
    assert body["similarity"] is None or body["similarity"] >= 0.6




def _make_color_image(w=256, h=256):
    # simple gradient RGB image
    x = np.linspace(0, 255, w, dtype=np.uint8)
    y = np.linspace(0, 255, h, dtype=np.uint8)
    X, Y = np.meshgrid(x, y)
    R = X
    G = Y
    B = ((X + Y) // 2).astype(np.uint8)
    arr = np.stack([R, G, B], axis=-1)
    im = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    buf.seek(0)
    return buf

def test_color_y_channel_roundtrip():
    img_buf = _make_color_image()
    text = "klyvo-demo"

    # embed using Y-channel
    files = {"file": ("color.png", img_buf, "image/png")}
    data = {"text": text, "qim_step": "8.0", "repetition": "20", "use_y_channel": "true"}
    resp = client.post("/api/watermark/image", files=files, data=data)
    assert resp.status_code == 200
    wm_bytes = resp.content

    # extract
    files = {"file": ("wm.png", io.BytesIO(wm_bytes), "image/png")}
    data = {
        "payload_bitlen": "256",
        "qim_step": "8.0",
        "repetition": "20",
        "check_text": text,
        "use_y_channel": "true",
    }
    x = client.post("/api/watermark/image/extract", files=files, data=data)
    assert x.status_code == 200
    body = x.json()
    assert body["payload_bitlen"] == 256
    assert body["recovered_hex"]
    assert body["similarity"] is None or body["similarity"] >= 0.6
