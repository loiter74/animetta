#!/usr/bin/env python3
import os
import re


STALE_MAP = {"animetta": "animetta"}


def fix_file(filepath: str) -> int:
    changes = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix stale package paths
    for old, new in STALE_MAP.items():
        if old in content:
            content = content.replace(old, new)
            changes += 1

    new_lines = []
    for line in content.split('\n'):
            changes += 1
            continue
        new_lines.append(line)
    content = '\n'.join(new_lines)

    if changes:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    return changes


def main():
    total_changes = 0
    total_files = 0

    for root, dirs, files in os.walk('.'):
        # Skip non-relevant dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__'
                   and d != 'node_modules' and d != '.pnpm']

        for f in files:
            if not f.endswith('.py'):
                continue
            path = os.path.join(root, f)
            changes = fix_file(path)
            if changes:
                total_changes += changes
                total_files += 1
                print(f"  [{changes:3d} changes] {path}")

    print(f"\nTotal: {total_changes} changes across {total_files} files")


if __name__ == '__main__':
    main()
