"""Crée des copies allégées des images de imgs/ dans imgs_web/ (même arborescence).

Les originaux ne sont jamais modifiés. Le filtre web-images.lua remplace
automatiquement imgs/... par imgs_web/... au rendu lorsque la copie existe.

Usage (depuis le dossier slides/) :  python optimize_images.py
Seules les images nouvelles ou modifiées sont retraitées.
"""
from pathlib import Path

from PIL import Image, ImageOps

SRC = Path(__file__).parent / "imgs"
DST = Path(__file__).parent / "imgs_web"
MAX_SIDE = 2400      # px : suffisant pour une slide 1600x900 et pour le zoom au clic
JPEG_QUALITY = 85
EXTS = {".jpg", ".jpeg", ".png"}


def process(src: Path, dst: Path) -> None:
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in {".jpg", ".jpeg"}:
            im.convert("RGB").save(dst, "JPEG", quality=JPEG_QUALITY,
                                   optimize=True, progressive=True)
        else:  # PNG conservé en PNG (texte et schémas restent nets)
            im.save(dst, "PNG", optimize=True)
    # si la copie n'est pas plus légère, on garde l'original tel quel
    if dst.stat().st_size >= src.stat().st_size:
        dst.write_bytes(src.read_bytes())


def main() -> None:
    before = after = 0
    for src in sorted(SRC.rglob("*")):
        if not src.is_file() or src.suffix.lower() not in EXTS:
            continue
        dst = DST / src.relative_to(SRC)
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            process(src, dst)
            print(f"{src.stat().st_size / 1e6:6.2f} Mo -> "
                  f"{dst.stat().st_size / 1e6:6.2f} Mo  {src.relative_to(SRC)}")
        before += src.stat().st_size
        after += dst.stat().st_size
    print(f"Total : {before / 1e6:.1f} Mo -> {after / 1e6:.1f} Mo")


if __name__ == "__main__":
    main()
