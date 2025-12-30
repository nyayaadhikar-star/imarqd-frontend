import numpy as np



from src.app.services.watermarking.helpers import (
    load_grayscale_float32, pad_to_multiple, unpad, blocks_view, dct2, majority_vote,
    load_color_bgr_float32, bgr_to_ycbcr
)
from src.app.services.watermarking.schemas import DCTConfig

# ... keep existing _qim_guess_bit and extract_dct_image ...

def _effective_repetition(total_blocks: int, desired_rep: int, payload_bits_len: int) -> int:
    if payload_bits_len <= 0:
        return desired_rep
    max_rep_that_fits = max(1, total_blocks // max(1, payload_bits_len))
    return max(1, min(desired_rep, max_rep_that_fits))


def _qim_guess_bit(c: float, step: float) -> int:
    k = step
    d0 = -k/4.0
    d1 = +k/4.0
    # distance to nearest quantization point in each codebook
    r0 = abs((c - d0) - k * round((c - d0) / k))
    r1 = abs((c - d1) - k * round((c - d1) / k))
    return 0 if r0 <= r1 else 1

def extract_dct_image(
    input_path: str,
    payload_bitlen: int,
    cfg: DCTConfig = DCTConfig()
) -> np.ndarray:
    """
    Recover payload bits of length `payload_bitlen` using majority vote over repeated blocks.
    """
    img = load_grayscale_float32(input_path)
    padded, _ = pad_to_multiple(img, cfg.block_size)
    blocks = blocks_view(padded, cfg.block_size)
    nH, nW = blocks.shape[:2]
    total_blocks = nH * nW

    # compute the same effective repetition used at embed time
    reps = _effective_repetition(total_blocks, cfg.repetition, payload_bitlen)
    needed_bits = min(int(np.ceil(total_blocks / reps)), payload_bitlen)


    votes = [[] for _ in range(needed_bits)]
    br, bc = cfg.coeff_pos

    bit_idx = 0
    for i in range(nH):
        for j in range(nW):
            bslot = bit_idx // reps
            if bslot >= needed_bits:
                break
            B = blocks[i, j].astype(np.float32)
            D = dct2(B)
            bit = _qim_guess_bit(float(D[br, bc]), cfg.qim_step)
            votes[bslot].append(bit)
            bit_idx += 1

    recovered = np.array([majority_vote(v) if v else 0 for v in votes], dtype=np.uint8)
    # If fewer than payload_bitlen, pad zeros; if more, truncate
    if len(recovered) < payload_bitlen:
        recovered = np.concatenate([recovered, np.zeros(payload_bitlen - len(recovered), dtype=np.uint8)])
    else:
        recovered = recovered[:payload_bitlen]
    return recovered



def extract_dct_image_ychannel(
    input_path: str,
    payload_bitlen: int,
    cfg: DCTConfig = DCTConfig()
    ) -> np.ndarray:
    """
    Recover payload from Y (luma) channel of color image.
    """
    bgr = load_color_bgr_float32(input_path)
    Y, _, _ = bgr_to_ycbcr(bgr)

    img = Y
    padded, _ = pad_to_multiple(img, cfg.block_size)
    blocks = blocks_view(padded, cfg.block_size)
    nH, nW = blocks.shape[:2]
    total_blocks = nH * nW

    # compute the same effective repetition used at embed time
    reps = _effective_repetition(total_blocks, cfg.repetition, payload_bitlen)
    needed_bits = min(int(np.ceil(total_blocks / reps)), payload_bitlen)

    votes = [[] for _ in range(needed_bits)]
    br, bc = cfg.coeff_pos

    bit_idx = 0
    for i in range(nH):
        for j in range(nW):
            bslot = bit_idx // reps
            if bslot >= needed_bits:
                break
            B = blocks[i, j].astype(np.float32)
            D = dct2(B)
            bit = _qim_guess_bit(float(D[br, bc]), cfg.qim_step)
            votes[bslot].append(bit)
            bit_idx += 1

    recovered = np.array([majority_vote(v) if v else 0 for v in votes], dtype=np.uint8)
    if len(recovered) < payload_bitlen:
        recovered = np.concatenate([recovered, np.zeros(payload_bitlen - len(recovered), dtype=np.uint8)])
    else:
        recovered = recovered[:payload_bitlen]
    return recovered




