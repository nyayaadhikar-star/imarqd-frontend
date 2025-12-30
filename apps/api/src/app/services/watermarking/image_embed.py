from typing import Iterable
import numpy as np
from src.app.services.watermarking.helpers import (
    load_grayscale_float32, save_grayscale_uint8, pad_to_multiple,
    unpad, blocks_view, dct2, idct2, sha256_bits_from_text,
    load_color_bgr_float32, save_color_bgr_uint8, bgr_to_ycbcr, ycbcr_to_bgr
)
from src.app.services.watermarking.schemas import DCTConfig

def _effective_repetition(total_blocks: int, desired_rep: int, payload_bits_len: int) -> int:
    """
    Ensure we have enough capacity: (total_blocks / reps) >= payload_bits_len.
    If not, reduce reps to fit; minimum reps = 1.
    """
    if payload_bits_len <= 0:
        return desired_rep
    max_rep_that_fits = max(1, total_blocks // max(1, payload_bits_len))
    return max(1, min(desired_rep, max_rep_that_fits))


def _qim_embed_coeff(c: float, bit: int, step: float) -> float:
    """
    Dithered QIM: two codebooks centered at +/- step/4.
    c' = k * round((c - d_b)/k) + d_b
    where d_0 = -k/4, d_1 = +k/4
    """
    k = step
    d = -k/4.0 if bit == 0 else +k/4.0
    q = np.round((c - d) / k)
    return q * k + d

def embed_dct_image(
    input_path: str,
    output_path: str,
    payload_bits: np.ndarray,
    cfg: DCTConfig = DCTConfig()
) -> None:
    """
    Embed payload_bits into image using DCT-QIM at a single mid-frequency coefficient.
    Grayscale only for v1.
    """
    img = load_grayscale_float32(input_path)
    padded, pad_hw = pad_to_multiple(img, cfg.block_size)

    blocks = blocks_view(padded, cfg.block_size)  # shape (nH, nW, b, b)
    nH, nW = blocks.shape[:2]
    total_blocks = nH * nW


    # capacity-aware repetition
    reps = _effective_repetition(total_blocks, cfg.repetition, len(payload_bits))
    needed_bits = int(np.ceil(total_blocks / reps))

    if len(payload_bits) < needed_bits:
        tile = int(np.ceil(needed_bits / len(payload_bits)))
        payload_bits = np.tile(payload_bits, tile)[:needed_bits]
    else:
        payload_bits = payload_bits[:needed_bits]

    # Assign each payload bit to `reps` blocks
    bit_idx = 0
    br, bc = cfg.coeff_pos
    for i in range(nH):
        for j in range(nW):
            curr_bit = payload_bits[bit_idx // reps]
            B = blocks[i, j].astype(np.float32)
            D = dct2(B)
            D[br, bc] = _qim_embed_coeff(D[br, bc], int(curr_bit), cfg.qim_step)
            blocks[i, j] = idct2(D)
            bit_idx += 1

    watermarked = blocks.swapaxes(1, 2).reshape(padded.shape)
    result = unpad(watermarked, pad_hw)
    save_grayscale_uint8(output_path, result)

def build_payload_from_text(text: str) -> np.ndarray:
    """256-bit payload from SHA-256(text)."""
    return sha256_bits_from_text(text)



def embed_dct_image_ychannel(
    input_path: str,
    output_path: str,
    payload_bits: np.ndarray,
    cfg: DCTConfig = DCTConfig()
) -> None:
    """
    Embed into the Y channel (luma) of a color image for better visual quality.
    """
    bgr = load_color_bgr_float32(input_path)
    Y, Cb, Cr = bgr_to_ycbcr(bgr)

    # --- reuse grayscale pipeline on Y ---
    img = Y
    padded, pad_hw = pad_to_multiple(img, cfg.block_size)
    blocks = blocks_view(padded, cfg.block_size)
    nH, nW = blocks.shape[:2]
    total_blocks = nH * nW

    # capacity-aware repetition
    reps = _effective_repetition(total_blocks, cfg.repetition, len(payload_bits))
    needed_bits = int(np.ceil(total_blocks / reps))

    if len(payload_bits) < needed_bits:
        tile = int(np.ceil(needed_bits / len(payload_bits)))
        payload_bits = np.tile(payload_bits, tile)[:needed_bits]
    else:
        payload_bits = payload_bits[:needed_bits]

    br, bc = cfg.coeff_pos
    bit_idx = 0
    for i in range(nH):
        for j in range(nW):
            curr_bit = int(payload_bits[bit_idx // reps])
            B = blocks[i, j].astype(np.float32)
            D = dct2(B)
            D[br, bc] = _qim_embed_coeff(D[br, bc], curr_bit, cfg.qim_step)
            blocks[i, j] = idct2(D)
            bit_idx += 1

    Y_wm = blocks.swapaxes(1, 2).reshape(padded.shape)
    Y_wm = unpad(Y_wm, pad_hw)

    # Recombine and save
    bgr_wm = ycbcr_to_bgr(Y_wm, Cb, Cr)
    save_color_bgr_uint8(output_path, bgr_wm)


