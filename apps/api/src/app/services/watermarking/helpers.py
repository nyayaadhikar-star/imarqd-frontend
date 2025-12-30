import cv2
import numpy as np
import hashlib
from typing import Iterable, Tuple


def sha256_bits_from_text(text: str) -> np.ndarray:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    return bytes_to_bits(h)

def bytes_to_bits(b: bytes) -> np.ndarray:
    arr = np.unpackbits(np.frombuffer(b, dtype=np.uint8))
    return arr.astype(np.uint8)

def bits_to_bytes(bits: np.ndarray) -> bytes:
    bits = bits.astype(np.uint8)
    # pad to multiple of 8
    pad = (-len(bits)) % 8
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, np.uint8)])
    return np.packbits(bits).tobytes()

def load_grayscale_float32(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {path}")
    return img.astype(np.float32)

def save_grayscale_uint8(path: str, arr: np.ndarray) -> None:
    arr = np.clip(np.round(arr), 0, 255).astype(np.uint8)
    cv2.imwrite(path, arr)

def pad_to_multiple(img: np.ndarray, block: int) -> Tuple[np.ndarray, Tuple[int, int]]:
    h, w = img.shape
    H = (h + (block - h % block) % block)
    W = (w + (block - w % block) % block)
    if (H, W) == (h, w):
        return img, (0, 0)
    padded = np.zeros((H, W), dtype=img.dtype)
    padded[:h, :w] = img
    return padded, (H - h, W - w)

def unpad(img: np.ndarray, pad_hw: Tuple[int, int]) -> np.ndarray:
    ph, pw = pad_hw
    if ph == 0 and pw == 0:
        return img
    return img[: img.shape[0] - ph, : img.shape[1] - pw]

def blocks_view(img: np.ndarray, block: int) -> np.ndarray:
    """Return a 4D view (nH, nW, block, block) without copying."""
    H, W = img.shape
    assert H % block == 0 and W % block == 0
    nH, nW = H // block, W // block
    return img.reshape(nH, block, nW, block).swapaxes(1, 2)

def dct2(block: np.ndarray) -> np.ndarray:
    # OpenCV DCT expects float32
    return cv2.dct(block)

def idct2(block: np.ndarray) -> np.ndarray:
    return cv2.idct(block)

def majority_vote(bits: Iterable[int]) -> int:
    bs = np.array(list(bits), dtype=np.int32)
    ones = np.count_nonzero(bs == 1)
    zeros = len(bs) - ones
    return 1 if ones >= zeros else 0




def load_color_bgr_float32(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {path}")
    return img.astype(np.float32)

def save_color_bgr_uint8(path: str, arr: np.ndarray) -> None:
    arr = np.clip(np.round(arr), 0, 255).astype(np.uint8)
    cv2.imwrite(path, arr)

import cv2
import numpy as np
from typing import Tuple

def bgr_to_ycbcr(bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Use OpenCV's YCrCb (full range) to avoid color shifts.
    Note: OpenCV order is Y, Cr, Cb. We return (Y, Cb, Cr) to match our code.
    Input/Output are float32 in [0,255].
    """
    # Ensure well-formed and in 0..255
    x = np.clip(bgr, 0, 255).astype(np.uint8)
    ycrcb = cv2.cvtColor(x, cv2.COLOR_BGR2YCrCb)  # uint8
    Y  = ycrcb[:, :, 0].astype(np.float32)
    Cr = ycrcb[:, :, 1].astype(np.float32)
    Cb = ycrcb[:, :, 2].astype(np.float32)
    return Y, Cb, Cr  # keep historical return order (Y, Cb, Cr)

def ycbcr_to_bgr(Y: np.ndarray, Cb: np.ndarray, Cr: np.ndarray) -> np.ndarray:
    """
    Inverse of the above using OpenCV (YCrCb).
    Inputs are float32 in [0,255].
    """
    Y8  = np.clip(Y,  0, 255).astype(np.uint8)
    Cb8 = np.clip(Cb, 0, 255).astype(np.uint8)
    Cr8 = np.clip(Cr, 0, 255).astype(np.uint8)

    ycrcb = np.stack([Y8, Cr8, Cb8], axis=-1)  # OpenCV expects Y,Cr,Cb
    bgr = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)  # uint8
    return bgr.astype(np.float32)






# --- Quality metrics on Y (luma) ---
def psnr(img_a: np.ndarray, img_b: np.ndarray, max_val: float = 255.0) -> float:
    """
    Peak Signal-to-Noise Ratio (dB). Expects same shape float32 arrays.
    """
    diff = img_a.astype(np.float32) - img_b.astype(np.float32)
    mse = float(np.mean(diff * diff))
    if mse <= 1e-12:
        return 99.0
    return 10.0 * np.log10((max_val * max_val) / mse)

def _ssim_single_channel(img_a: np.ndarray, img_b: np.ndarray) -> float:
    """
    SSIM for a single channel using a Gaussian kernel.
    """
    a = img_a.astype(np.float32)
    b = img_b.astype(np.float32)

    # Gaussian window (11x11, sigma=1.5)
    gauss = cv2.getGaussianKernel(11, 1.5)
    window = gauss @ gauss.T

    mu1 = cv2.filter2D(a, -1, window)
    mu2 = cv2.filter2D(b, -1, window)

    mu1_sq = mu1 * mu1
    mu2_sq = mu2 * mu2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = cv2.filter2D(a * a, -1, window) - mu1_sq
    sigma2_sq = cv2.filter2D(b * b, -1, window) - mu2_sq
    sigma12 = cv2.filter2D(a * b, -1, window) - mu1_mu2

    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
    return float(np.clip(np.mean(ssim_map), 0.0, 1.0))

def ssim_y(bgr_a: np.ndarray, bgr_b: np.ndarray) -> float:
    """
    SSIM on Y (luma) of two BGR images.
    """
    Y1, _, _ = bgr_to_ycbcr(bgr_a)
    Y2, _, _ = bgr_to_ycbcr(bgr_b)
    return _ssim_single_channel(Y1, Y2)

# --- Pre-WhatsApp preparation ---
def resize_long_edge(bgr: np.ndarray, target: int = 1280) -> np.ndarray:
    h, w = bgr.shape[:2]
    long_edge = max(h, w)
    if long_edge <= target:
        return bgr
    scale = target / long_edge
    new_w, new_h = int(round(w * scale)), int(round(h * scale))
    return cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)

def jpeg_roundtrip(bgr: np.ndarray, quality: int = 85) -> np.ndarray:
    """
    Simulate WhatsApp-ish compression once (dev helper).
    """
    ok, enc = cv2.imencode(".jpg", np.clip(bgr, 0, 255).astype(np.uint8), [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return bgr
    dec = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    return dec.astype(np.float32)

def preprocess_for_whatsapp(bgr: np.ndarray) -> np.ndarray:
    """
    Resize longest edge to ~1280, then light JPEG. Returns float32 BGR in [0,255].
    """
    x = resize_long_edge(bgr, 1280)
    x = jpeg_roundtrip(x, 85)
    return x.astype(np.float32)




def center_crop_to_mod(bgr: np.ndarray, mod: int = 16) -> np.ndarray:
    """
    Center-crop so that both dimensions are multiples of `mod` (default 16).
    This helps keep DCT/MCU alignment through social-media recompression.
    """
    h, w = bgr.shape[:2]
    new_w = w - (w % mod)
    new_h = h - (h % mod)
    if new_w == w and new_h == h:
        return bgr
    x0 = (w - new_w) // 2
    y0 = (h - new_h) // 2
    return bgr[y0:y0 + new_h, x0:x0 + new_w]

def preprocess_generic(bgr: np.ndarray, long_edge: int = 1280, mod: int = 16) -> np.ndarray:
    """
    Generic, platform-agnostic preprocessing:
      1) limit long edge to `long_edge` (default 1280),
      2) center-crop to multiples of `mod` (default 16),
      3) return float32 BGR in [0,255] with NO extra JPEG roundtrip.
    """
    x = resize_long_edge(bgr, long_edge)
    x = center_crop_to_mod(x, mod)
    return x.astype(np.float32)



# --- Generic preset preprocessor ---------------------------------------------

def preprocess_for_preset(
    bgr: np.ndarray,
    long_edge: int | None = None,
    jpeg_quality: int | None = None,
) -> np.ndarray:
    """
    Optionally resize longest edge and do a light JPEG round trip to simulate
    platform compression characteristics.
    """
    x = bgr
    if long_edge and long_edge > 0:
        x = resize_long_edge(x, long_edge)
    if jpeg_quality and 1 <= jpeg_quality <= 100:
        x = jpeg_roundtrip(x, jpeg_quality)
    return x.astype(np.float32)
