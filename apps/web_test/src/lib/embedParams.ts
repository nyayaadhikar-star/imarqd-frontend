// src/lib/embedParams.ts

export type Preset = {
  name: string;
  long_edge: number | null;
  jpeg_quality: number | null;
  defaults: {
    qim_step: number;
    repetition: number;
    ecc_parity_bytes: number;
    use_y_channel: boolean;
  };
};

export type EmbedParams = {
  preset: string;
  text: string;
  long_edge?: number | null;
  jpeg_quality?: number | null;
  qim_step?: number;
  repetition?: number;
  ecc_parity_bytes?: number;
  use_y_channel?: boolean;
};

export type ExtractParams = {
  preset: string;
  long_edge?: number | null;
  jpeg_quality?: number | null;
  qim_step?: number;
  repetition?: number;
  ecc_parity_bytes?: number;
  use_y_channel?: boolean;
};
