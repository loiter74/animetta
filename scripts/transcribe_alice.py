"""
Transcribe alice_training_set WAV files using FasterWhisper.
Generates train.jsonl for Qwen3-TTS fine-tuning.

Usage: python scripts/transcribe_alice.py
Output: E:/animetta_data/tts_training/kuonji_arisu/training_ready/train.jsonl
"""
import json
import os
import sys
from pathlib import Path

DATA_DIR = Path("E:/animetta_data/tts_training/kuonji_arisu/training_ready/alice_training_set")
OUTPUT = Path("E:/animetta_data/tts_training/kuonji_arisu/training_ready/train.jsonl")
CHECKPOINT = Path("E:/animetta_data/tts_training/kuonji_arisu/training_ready/transcribe_checkpoint.json")

def main():
    # Collect WAV files
    wav_files = sorted(DATA_DIR.glob("*.wav"))
    print(f"Found {len(wav_files)} WAV files")

    # Load checkpoint
    done = set()
    if CHECKPOINT.exists():
        done = set(json.loads(CHECKPOINT.read_text(encoding="utf-8")))
        print(f"Resuming from checkpoint: {len(done)} already done, {len(wav_files) - len(done)} remaining")

    # Load FasterWhisper
    from faster_whisper import WhisperModel
    model_size = "large-v3"
    print(f"Loading FasterWhisper {model_size}...")
    model = WhisperModel(model_size, device="cuda", compute_type="float16")
    print("Model loaded.")

    # Transcribe
    total = len(wav_files)
    with open(OUTPUT, "a", encoding="utf-8") as f_out:
        for i, wav_path in enumerate(wav_files):
            fname = wav_path.name
            if fname in done:
                continue

            try:
                segments, info = model.transcribe(
                    str(wav_path),
                    language="ja",          # Primarily Japanese (FGO game voices)
                    beam_size=5,
                    vad_filter=True,        # Filter silence
                    vad_parameters=dict(
                        min_silence_duration_ms=300,
                    ),
                )
                text = " ".join(s.text.strip() for s in segments if s.text.strip())

                if text:
                    line = json.dumps({"audio_path": str(wav_path), "text": text}, ensure_ascii=False)
                    f_out.write(line + "\n")
                    f_out.flush()
                else:
                    print(f"  [{i+1}/{total}] SKIP (no text): {fname}")

                # Checkpoint every 50 files
                done.add(fname)
                if (i + 1) % 50 == 0:
                    CHECKPOINT.write_text(json.dumps(list(done), ensure_ascii=False), encoding="utf-8")
                    print(f"  [{i+1}/{total}] checkpoint saved. Sample: {text[:60] if text else 'N/A'}...")

            except Exception as e:
                print(f"  [{i+1}/{total}] ERROR {fname}: {e}")
                done.add(fname)  # Skip failed files

    # Final checkpoint
    CHECKPOINT.write_text(json.dumps(list(done), ensure_ascii=False), encoding="utf-8")
    print(f"\nDone! {len(done)} files processed.")
    print(f"Output: {OUTPUT}")

if __name__ == "__main__":
    main()
