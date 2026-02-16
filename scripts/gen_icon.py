#!/usr/bin/env python3
import os
from pathlib import Path

try:
    from PIL import Image
except Exception as e:
    print("Pillow not available; skipping icon generation:", e)
    raise SystemExit(0)

ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / 'src-tauri' / 'icons'
ICON_DIR.mkdir(parents=True, exist_ok=True)

def ensure_png(name: str, size: int) -> Path:
    path = ICON_DIR / name
    if not path.exists():
        img = Image.new('RGBA', (size, size), (0, 122, 204, 255))
        img.save(path, format='PNG')
        print(f"Created {path}")
    return path

def ensure_ico() -> Path:
    ico_path = ICON_DIR / 'icon.ico'
    if not ico_path.exists():
        sizes = [16, 32, 48, 64, 128, 256]
        imgs = [Image.new('RGBA', (s, s), (0, 122, 204, 255)) for s in sizes]
        imgs[0].save(ico_path, format='ICO', sizes=[(s, s) for s in sizes])
        print(f"Created {ico_path}")
    return ico_path

def main():
    ensure_png('32x32.png', 32)
    ensure_png('128x128.png', 128)
    ensure_png('128x128@2x.png', 256)
    ensure_ico()
    # macOS icns not required for Windows dev; skip
    print('Icon generation complete')

if __name__ == '__main__':
    main()


