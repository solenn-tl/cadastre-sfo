"""Crée des copies allégées (WebP) des images de imgs/ dans imgs_web/ (même arborescence).

Les originaux ne sont jamais modifiés. Le filtre web-images.lua remplace
automatiquement imgs/x.png par imgs_web/x.webp au rendu lorsque la copie existe.

Usage (depuis le dossier slides/) :  python optimize_images.py
Seules les images nouvelles ou modifiées sont retraitées.
"""
from pathlib import Path

from PIL import Image, ImageOps

SRC = Path(__file__).parent / "imgs"
DST = Path(__file__).parent / "imgs_web"
MAX_SIDE = 1920      # px : suffisant pour une slide 1600x900 et pour le zoom au clic
QUALITY_PNG = 88     # schémas, captures : qualité haute pour garder le texte net
QUALITY_JPEG = 82    # photos, scans
EXTS = {".jpg", ".jpeg", ".png"}


def process(src: Path, dst: Path) -> bool:
    """Écrit dst en WebP ; renvoie False (et n'écrit rien) si ce n'est pas plus léger."""
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        has_alpha = "A" in im.getbands() or "transparency" in im.info
        im = im.convert("RGBA" if has_alpha else "RGB")
        quality = QUALITY_PNG if src.suffix.lower() == ".png" else QUALITY_JPEG
        dst.parent.mkdir(parents=True, exist_ok=True)
        im.save(dst, "WEBP", quality=quality, method=6)
    if dst.stat().st_size >= src.stat().st_size:
        dst.unlink()  # le filtre utilisera l'original
        return False
    return True


def main() -> None:
    before = after = 0
    for src in sorted(SRC.rglob("*")):
        if not src.is_file() or src.suffix.lower() not in EXTS:
            continue
        dst = (DST / src.relative_to(SRC)).with_suffix(".webp")
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            if process(src, dst):
                print(f"{src.stat().st_size / 1e6:6.2f} Mo -> "
                      f"{dst.stat().st_size / 1e6:6.2f} Mo  {src.relative_to(SRC)}")
            else:
                print(f"  (original conservé)  {src.relative_to(SRC)}")
        before += src.stat().st_size
        after += dst.stat().st_size if dst.exists() else src.stat().st_size
    print(f"Total : {before / 1e6:.1f} Mo -> {after / 1e6:.1f} Mo")


if __name__ == "__main__":
    main()
