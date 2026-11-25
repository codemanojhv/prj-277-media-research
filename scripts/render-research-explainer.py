"""Render the silent, text-led home-page explainer (requires Pillow and ffmpeg)."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "apps" / "web" / "public" / "media"
OUTPUT.mkdir(parents=True, exist_ok=True)
W, H, FPS, DURATION = 960, 540, 15, 18
FONTS = Path("C:/Windows/Fonts")
SANS = str(FONTS / "segoeui.ttf")
BOLD = str(FONTS / "segoeuib.ttf")
SERIF = str(FONTS / "georgia.ttf")
INK, MUTED, GREEN = "#223e3b", "#627a70", "#2c6758"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def rounded(draw: ImageDraw.ImageDraw, box: tuple, fill: str, outline: str | None = None, radius: int = 16):
    draw.rounded_rectangle(tuple(round(value) for value in box), radius=radius, fill=fill, outline=outline, width=1)


def text(draw, xy, value, size=20, color=INK, face=SANS):
    draw.text(xy, value, fill=color, font=font(face, size))


def ease(t: float) -> float:
    return 1 - (1 - max(0.0, min(1.0, t))) ** 3


def frame(t: float) -> Image.Image:
    image = Image.new("RGB", (W, H), "#f1f6ef")
    d = ImageDraw.Draw(image)
    d.ellipse((690, -140, 1100, 270), fill="#e5f0e5")
    d.ellipse((-190, 365, 110, 665), fill="#e4eee5")
    text(d, (45, 32), "PRJ_277  /  MEDIA RESEARCH", 15, "#54796a", BOLD)
    text(d, (45, 65), "From a question to the evidence", 32, INK, SERIF)
    d.line((45, 119, 915, 119), fill="#d0e1d3", width=2)

    scene = min(2, int(t // 6))
    local = t - scene * 6
    lift = round((1 - ease(local / 0.65)) * 20)
    labels = [("01", "Search the coverage"), ("02", "Compare the stories"), ("03", "Follow the evidence")]
    for index, (number, label) in enumerate(labels):
        x = 45 + index * 290
        active = index == scene
        rounded(d, (x, 143, x + 260, 187), "#dbece0" if active else "#f8fbf6", "#bdd7c3" if active else "#dce8dc", 10)
        text(d, (x + 15, 153), number, 15, GREEN if active else MUTED, BOLD)
        text(d, (x + 52, 152), label, 16, INK if active else MUTED, BOLD if active else SANS)

    y = 211 + lift
    rounded(d, (45, y, 915, y + 250), "#ffffff", "#d8e6da", 18)
    if scene == 0:
        text(d, (75, y + 27), "Begin with a topic", 26, INK, SERIF)
        text(d, (75, y + 69), "Choose a date range and languages to collect news coverage.", 17, MUTED)
        rounded(d, (75, y + 109, 610, y + 154), "#f7faf6", "#cedfd2", 9)
        text(d, (92, y + 119), "e.g. a policy, campaign or announcement", 17, "#6b8276")
        rounded(d, (75, y + 175, 240, y + 214), "#e7f2e8", None, 9)
        text(d, (93, y + 184), "Dates  +  languages", 16, GREEN, BOLD)
        rounded(d, (658, y + 94, 858, y + 212), "#edf6eb", None, 12)
        d.ellipse((717, y + 110, 786, y + 179), outline="#6a9a7e", width=5)
        d.line((780, y + 172, 808, y + 199), fill="#6a9a7e", width=6)
    elif scene == 1:
        text(d, (75, y + 27), "See related reports together", 26, INK, SERIF)
        text(d, (75, y + 69), "Compare coverage by source and language within the sample.", 17, MUTED)
        for i, (label, detail) in enumerate((("Article A", "Publisher  /  Language"), ("Article B", "Publisher  /  Language"), ("Article C", "Publisher  /  Language"))):
            x = 75 + i * 268
            offset = round((1 - ease((local - i * .14) / .6)) * 14)
            rounded(d, (x, y + 111 + offset, x + 245, y + 214 + offset), "#f7faf6", "#d6e5d7", 10)
            text(d, (x + 16, y + 126 + offset), label, 19, INK, BOLD)
            text(d, (x + 16, y + 159 + offset), detail, 14, MUTED)
            d.line((x + 16, y + 189 + offset, x + 170, y + 189 + offset), fill="#b7d2bf", width=4)
    else:
        text(d, (75, y + 27), "Review the source", 26, INK, SERIF)
        text(d, (75, y + 69), "Open article text, quoted evidence and collection details.", 17, MUTED)
        rounded(d, (75, y + 105, 515, y + 215), "#f7faf6", "#d6e5d7", 10)
        text(d, (93, y + 119), "Source record", 18, INK, BOLD)
        text(d, (93, y + 153), "Article text and supporting excerpts", 16, MUTED)
        text(d, (93, y + 183), "Source link  /  Collection method", 14, GREEN)
        rounded(d, (555, y + 105, 856, y + 215), "#eaf4e9", None, 10)
        text(d, (575, y + 122), "Read the original", 18, INK, BOLD)
        text(d, (575, y + 157), "Interpretations are research", 15, MUTED)
        text(d, (575, y + 180), "aids, not verified findings.", 15, MUTED)

    d.line((45, 500, 915, 500), fill="#d9e8dc", width=4)
    d.line((45, 500, 45 + 870 * min(t / DURATION, 1), 500), fill="#7ba78a", width=4)
    text(d, (45, 512), "Illustrative walkthrough  •  No audio", 13, MUTED)
    return image


def main():
    frame(0.8).save(OUTPUT / "research-explainer-poster.jpg", quality=86, optimize=True)
    target = OUTPUT / "research-explainer.mp4"
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target)]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as process:
        assert process.stdin is not None
        for index in range(FPS * DURATION):
            process.stdin.write(frame(index / FPS).tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError("Could not render explainer video")
    print(f"Created {target} ({target.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
