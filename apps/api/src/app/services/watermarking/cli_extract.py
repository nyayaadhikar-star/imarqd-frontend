import argparse
import hashlib
from src.app.services.watermarking.image_extract import extract_dct_image
from src.app.services.watermarking.image_embed import build_payload_from_text
from src.app.services.watermarking.schemas import DCTConfig

def bits_to_hex(bits):
    import numpy as np
    from helpers import bits_to_bytes
    return hashlib.sha256(bits_to_bytes(bits)).hexdigest()  # not the original text hash, just a helper

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inp", required=True, help="Input image (possibly watermarked)")
    p.add_argument("--bitlen", type=int, default=256, help="Expected payload length in bits")
    p.add_argument("--qim", type=float, default=8.0)
    p.add_argument("--rep", type=int, default=20)
    p.add_argument("--check-text", default=None, help="If provided, checks recovered bits against SHA-256(check-text)")
    args = p.parse_args()

    cfg = DCTConfig(qim_step=args.qim, repetition=args.rep)
    recovered_bits = extract_dct_image(args.inp, args.bitlen, cfg)
    print(f"Recovered {len(recovered_bits)} bits.")

    if args.check_text:
        target_bits = build_payload_from_text(args.check_text)
        # Compare Hamming similarity
        import numpy as np
        L = min(len(recovered_bits), len(target_bits))
        match = np.mean(recovered_bits[:L] == target_bits[:L])
        print(f"Similarity to SHA256('{args.check_text}') bits: {match*100:.2f}%")
    else:
        print("No check-text provided; raw bits recovered.")

if __name__ == "__main__":
    main()
