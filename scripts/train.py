#!/usr/bin/env python3
"""Anima Train — 一键训练 RVC v2 歌声模型.

Usage:
    python scripts/train.py --character shige_utage
    python scripts/train.py --character shige_utage --epochs 500
    python scripts/train.py --character shige_utage --deploy-only
    python scripts/train.py --character shige_utage --dry-run
    python scripts/train.py --help
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    from scripts.train.cli import main
    main()
