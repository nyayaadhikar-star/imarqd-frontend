import argparse
from image_embed import embed_dct_image, build_payload_from_text
from schemas import DCTConfig

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inp", required=True, help="Input image (grayscale preferred)")
    p.add_argument("--out", dest="out", required=True, help="Output watermarked image path")
    p.add_argument("--text", required=True, help="Text used to derive a 256-bit payload (SHA-256)")
    p.add_argument("--qim", type=float, default=8.0, help="QIM step (strength)")
    p.add_argument("--rep", type=int, default=20, help="Repetition factor (robustness)")
    args = p.parse_args()

    payload = build_payload_from_text(args.text)  # 256 bits
    cfg = DCTConfig(qim_step=args.qim, repetition=args.rep)
    embed_dct_image(args.inp, args.out, payload, cfg)
    print(f"Watermarked saved → {args.out}")

if __name__ == "__main__":
    main()
