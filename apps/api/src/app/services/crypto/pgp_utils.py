# services/crypto/pgp_utils.py
from typing import Tuple
import pgpy

def load_public_key(armored_pubkey: str) -> pgpy.PGPKey:
    pub, _ = pgpy.PGPKey.from_blob(armored_pubkey)
    if not pub.is_public:
        raise ValueError("Provided key is not a public key")
    return pub

def key_fingerprint(armored_pubkey: str) -> str:
    pub = load_public_key(armored_pubkey)
    # Modern OpenPGP keys expose a 40-hex fingerprint; remove spaces just in case
    return pub.fingerprint.replace(" ", "")

def verify_detached_signature(
    armored_pubkey: str,
    message_bytes: bytes,
    armored_signature: str
) -> bool:
    """
    Verify a detached ASCII-armored signature over message_bytes using the given public key.
    Returns True/False (never raises unless the inputs are malformed).
    """
    pub = load_public_key(armored_pubkey)
    sig = pgpy.PGPSignature.from_blob(armored_signature)

    # pgpy can verify either a raw bytes/str or a PGPMessage; try both defensively
    try:
        ok = pub.verify(message_bytes, sig)
        return bool(ok)
    except Exception:
        pass
    try:
        msg = pgpy.PGPMessage.new(message_bytes)  # wrap as literal message
        ok = pub.verify(msg, sig)
        return bool(ok)
    except Exception:
        return False

def parse_signature_metadata(armored_signature: str) -> Tuple[str, str]:
    try:
        sig = pgpy.PGPSignature.from_blob(armored_signature)
        return (str(sig.hash_algorithm), str(sig.type))
    except Exception:
        return ("", "")
