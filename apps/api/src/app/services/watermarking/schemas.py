from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel

class EmbedMethod(str, Enum):
    DCT_IMAGE = "dct_image"

@dataclass
class DCTConfig:
    block_size: int = 8
    # Mid-frequency coefficient to modulate (row, col) in 8x8 DCT block
    coeff_pos: tuple[int, int] = (3, 4)
    # Quantization step for QIM (larger = stronger/robuster but more visible)
    qim_step: float = 8.0
    # How many blocks contribute to each payload bit (repetition code)
    repetition: int = 20

