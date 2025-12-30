from typing import Tuple
from reedsolo import RSCodec, ReedSolomonError

def ecc_encode_sha256(payload_32: bytes, parity_bytes: int = 24) -> bytes:
    """
    Encode 32-byte SHA-256 payload with Reed–Solomon parity.
    Returns codeword of length 32 + parity_bytes.
    """
    if len(payload_32) != 32:
        raise ValueError("payload_32 must be exactly 32 bytes (SHA-256).")
    if not (2 <= parity_bytes <= 64):
        raise ValueError("parity_bytes should be between 2 and 64 for this RS setup.")
    rsc = RSCodec(parity_bytes)
    return bytes(rsc.encode(payload_32))  # returns data+parity

def ecc_decode_to_sha256(codeword: bytes, parity_bytes: int = 24) -> Tuple[bytes, bool]:
    """
    Decode codeword and return (original_32_bytes, ok).
    ok=False if decoding fails.
    """
    try:
        rsc = RSCodec(parity_bytes)
        decoded = rsc.decode(codeword)[0]  # (message, ecc, errpos)
        if len(decoded) != 32:
            return decoded[:32], False
        return decoded, True
    except ReedSolomonError:
        # decoding failed
        return b"", False
