"""
Singing Pipeline E2E Smoke Test (with error handling)
Usage: PYTHONPATH=src python scripts/test_singing_pipeline.py [bilibili_url]
"""
import asyncio
import sys
import os
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger
import yaml


def load_config():
    from anima.config.singing_config import SingingConfig
    config_path = Path(__file__).parent.parent / "config" / "singing.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return SingingConfig(**raw.get("singing", {}))


def human_size(bytes_val: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    
    config = load_config()
    logger.info(f"Config loaded. RVC enabled: {config.rvc.enabled}")
    logger.info(f"ASR: {config.asr.model_size}, language={config.asr.language}")
    logger.info(f"RVC: {config.rvc.model_name}, index={config.rvc.index_path}")

    from anima.services.singing.svc_pipeline import SVCPipeline
    from anima.services.singing.interface import PipelineProgress

    pipeline = SVCPipeline(config)
    
    # Add progress callback for visibility
    def _progress(p: PipelineProgress):
        logger.info(f"  [{p.stage.value}] {p.progress:.0f}% - {p.message}")
    pipeline.set_progress_callback(_progress)

    total_start = time.time()

    try:
        if url:
            logger.info(f"Testing with URL: {url}")
            result = await pipeline.process(url, auto_confirm_lyrics=True)
        else:
            cached = Path("data/singing/downloads/bilibili_test.wav")
            if not cached.exists():
                logger.error("No cached audio! Provide a URL.")
                return
            logger.info(f"Testing with cached: {cached} ({human_size(cached.stat().st_size)})")
            result = await pipeline.process_from_file(str(cached), auto_confirm_lyrics=True)

        total_time = time.time() - total_start

        print("\n" + "=" * 60)
        print("  PIPELINE COMPLETE")
        print("=" * 60)
        print(f"  Total time:        {total_time:.1f}s ({total_time/60:.1f} min)")
        print(f"  Video title:       {result.video_title or '(local file)'}")
        print(f"  Duration:          {result.duration_sec:.1f}s")
        print(f"  Lyrics:            {len(result.lyrics)} lines")
        print(f"  Volumes:           {len(result.volumes)} samples")
        print()

        files = {
            "Final mix": result.audio_path,
            "Vocals": result.vocals_path,
            "Original": result.original_audio_path,
            "Subtitle (.ass)": result.subtitle_path,
        }
        if result.tts_audio_path:
            files["TTS mix"] = result.tts_audio_path

        all_ok = True
        for label, path in files.items():
            p = Path(path)
            if p.exists():
                print(f"  [OK] {label:<20} {human_size(p.stat().st_size):>10}  {p}")
            else:
                print(f"  [XX] {label:<20} MISSING  {p}")
                all_ok = False

        if result.lyrics:
            print(f"\n  --- First 5 lyrics ---")
            for i, l in enumerate(result.lyrics[:5]):
                print(f"  [{l.start_ms/1000:6.2f}-{l.end_ms/1000:6.2f}] {l.text}")

        print()
        if all_ok:
            print("  [OK] ALL OUTPUT FILES PRESENT - Pipeline PASSED")
        else:
            print("  [XX] SOME FILES MISSING - Pipeline FAILED")

    except Exception as e:
        logger.error(f"Pipeline crashed: {e}")
        traceback.print_exc()
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
