#!/usr/bin/env python3
"""Demucs wrapper — patches save_audio to bypass torchcodec incompatibility."""
import sys
import numpy as np
import soundfile as sf

# 1. Patch torchaudio BEFORE any demucs import
import torchaudio as _ta

def _sf_save(uri, src, sample_rate, **kwargs):
    arr = src.detach().cpu().numpy() if hasattr(src, 'numpy') else np.asarray(src)
    if arr.ndim == 2 and arr.shape[0] <= arr.shape[1]:
        arr = arr.T
    sf.write(str(uri), arr.astype(np.float32), sample_rate, subtype='PCM_16')

_ta.save = _sf_save

# 2. Patch demucs.audio.save_audio
import demucs.audio as _da

def _patched_save_audio(wav, path, samplerate,
                         bitrate=320, clip='rescale',
                         bits_per_sample=16, as_float=False,
                         preset=2):
    """Soundfile-based save to bypass torchcodec."""
    wav = _da.convert_audio_channels(wav, 2)
    wav = _da.convert_audio(wav, samplerate, 44100, 2)
    if clip == 'clamp':
        wav = wav.clamp(-0.999, 0.999)
    elif clip == 'tanh':
        wav = wav.tanh()
    elif clip == 'rescale':
        mx = wav.abs().max()
        if mx > 0:
            wav = wav / mx * 0.999
    arr = wav.numpy()
    if arr.ndim == 2:
        arr = arr.T
    subtype = {16: 'PCM_16', 24: 'PCM_24', 32: 'PCM_32'}[bits_per_sample]
    sf.write(str(path), arr.astype(np.float32), 44100, subtype=subtype)

_da.save_audio = _patched_save_audio

# 3. Run demucs
from demucs.separate import main as demucs_main

if __name__ == "__main__":
    demucs_main()
