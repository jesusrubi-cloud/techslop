"""Original geometric motion design in Pillow, encoded as H.264 clips by FFmpeg."""
from __future__ import annotations

from functools import lru_cache
import math
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont
from techslop.render.adapter import RenderPlan, RenderScene

W, H, FPS = 1080, 1920, 30
BG, WHITE, MUTED, TEAL, CORAL = '#0c1628', '#f2f4ed', '#a8b7c9', '#64e3c1', '#ffae8c'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


@lru_cache(maxsize=30)
def font(size: int, bold: bool = False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def wrap(text: str, size: int, width: int, bold: bool = False) -> list[str]:
    draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    lines = []
    line = ''
    for word in text.split():
        candidate = (line + ' ' + word).strip()
        if draw.textlength(candidate, font=font(size, bold)) > width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    return lines + ([line] if line else [])


def text_block(draw, text: str, xy: tuple[int, int], size: int, width: int, color=WHITE, bold=False, max_lines=6) -> int:
    lines = wrap(text, size, width, bold)
    while len(lines) > max_lines and size > 26:
        size -= 2
        lines = wrap(text, size, width, bold)
    if len(lines) > max_lines:
        raise ValueError('Text exceeds safe area; shorten editorial copy')
    for i, line in enumerate(lines):
        draw.text((xy[0], xy[1] + i * (size + 14)), line, font=font(size, bold), fill=color)
    return xy[1] + len(lines) * (size + 14)


def base(scene: RenderScene, plan: RenderPlan, index: int) -> Image.Image:
    image = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(image)
    for y in range(0, H, 100):
        draw.line((0, y, W, y), fill='#112039', width=1)
    draw.rounded_rectangle((64, 74, 1016, 138), radius=22, fill='#29413e' if plan.demo else '#243550')
    label = 'DEMOSTRACIÓN FICTICIA · NO ES NOTICIA' if plan.demo else 'BORRADOR EDITORIAL · REVISIÓN HUMANA'
    draw.text((88, 91), label, font=font(27, True), fill=TEAL)
    draw.text((72, 202), f'TECHSLOP / ESTUDIO     0{index + 1}', font=font(25, True), fill=MUTED)
    if scene.kind != 'intro':
        text_block(draw, scene.title, (72, 290), 68, 930, bold=True, max_lines=4)
    text_block(draw, scene.text, (76, 670), 36, 914, color=MUTED, max_lines=4)
    draw.rounded_rectangle((64, 1400, 1016, 1456), radius=16, fill='#48342f' if plan.audio_mode == 'test_tone' else '#1e3b3b')
    audio_label = 'AUDIO DE PRUEBA · TONO, SIN VOZ' if plan.audio_mode == 'test_tone' else 'NARRACIÓN SINTÉTICA · ESPAÑOL DE MÉXICO'
    draw.text((85, 1415), audio_label, font=font(26, True), fill=CORAL if plan.audio_mode == 'test_tone' else TEAL)
    draw.text((72, 1800), 'PROTOTIPO LOCAL / SIN PUBLICACIÓN', font=font(25), fill=MUTED)
    return image


@lru_cache(maxsize=20)
def title_layer(title: str) -> Image.Image:
    layer = Image.new('RGBA', (1080, 380), (0, 0, 0, 0))
    text_block(ImageDraw.Draw(layer), title, (72, 0), 68, 930, bold=True, max_lines=4)
    return layer


def frame(scene: RenderScene, plan: RenderPlan, index: int, t: float, background: Image.Image | None = None) -> Image.Image:
    image = (background if background is not None else base(scene, plan, index)).copy()
    draw = ImageDraw.Draw(image)
    progress = min(1, max(0, t / max(scene.duration, 0.001)))
    ease = 1 - (1 - min(t / 1.5, 1)) ** 3
    shift = int(12 * math.sin(t * 0.45))
    if scene.kind == 'intro':
        heading = title_layer(scene.title).copy()
        heading.putalpha(heading.getchannel('A').point(lambda value: int(value * ease)))
        image.paste(heading, (0, 290 + int(60 * (1 - ease))), heading)
        # Expanding concentric frames provide a gentle camera-like push-in.
        radius = int(130 + 24 * ease + 8 * progress)
        cx, cy = 540 + shift, 1080
        for offset in [70, 35, 0]:
            draw.rounded_rectangle((cx-radius-offset, cy-radius-offset, cx+radius+offset, cy+radius+offset), radius=30, outline=TEAL if offset == 0 else '#284a51', width=4)
        draw.text((cx-74, cy-48), 'EN', font=font(54, True), fill=WHITE)
        draw.text((cx-110, cy+25), 'PRUEBA', font=font(39, True), fill=TEAL)
    elif scene.kind == 'explanation':
        # Original document illustration; no photo, geographical map or external asset.
        positions = [(125, 955), (430, 1010), (735, 955)]
        for i, (x, y) in enumerate(positions):
            y += int(12 * math.sin(t * .8 + i))
            draw.rounded_rectangle((x, y, x+220, y+230), radius=24, fill='#1a3046', outline=TEAL, width=3)
            for row in range(3):
                draw.line((x+30, y+45+row*36, x+175, y+45+row*36), fill=MUTED, width=6)
            draw.text((x+28, y+165), ['GUIÓN', 'ESCENA', 'FUENTE'][i], font=font(26, True), fill=WHITE)
            if i < 2:
                draw.line((x+230, 1115, x+285, 1115), fill=TEAL, width=5)
    elif scene.kind == 'chart':
        maximum = max(plan.chart_values)
        for i, value in enumerate(plan.chart_values):
            y = 940 + i * 95
            draw.text((80, y), f'ESCENA {i+1}', font=font(25, True), fill=MUTED)
            length = int(570 * value / maximum * ease)
            if length:
                draw.rounded_rectangle((270, y, 270+length, y+43), radius=10, fill=TEAL if i % 2 == 0 else CORAL)
            draw.text((875, y), f'{value:.1f} s', font=font(28, True), fill=WHITE)
        draw.text((80, 1335), 'FFPROBE · DURACIONES MEDIDAS, NO ESTADÍSTICAS', font=font(23), fill=MUTED)
    elif scene.kind == 'closing':
        draw.rounded_rectangle((80, 940+shift, 1000, 1325+shift), radius=28, fill='#1a3046', outline=TEAL, width=3)
        draw.text((115, 975+shift), 'REFERENCIAS DE ESTA DEMO', font=font(31, True), fill=TEAL)
        references = 'Guion y manifiesto: examples/hybrid-demo. Sin hechos periodísticos.' if plan.demo else ' / '.join(scene.source_urls)
        text_block(draw, references, (115, 1050+shift), 32, 835, max_lines=3)
        text_block(draw, 'Métrica: ffprobe sobre cada fragmento de audio.', (115, 1190+shift), 29, 835, max_lines=2)
    draw.rectangle((72, 1865, 72 + int(936 * progress), 1871), fill=TEAL)
    return image


def render_clip(scene: RenderScene, plan: RenderPlan, index: int, output: Path, *, tail: float = 0.4) -> Path:
    frames = math.ceil((scene.duration + tail) * FPS)
    command = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
               '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21',
               '-threads', '2', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)]
    background = base(scene, plan, index)
    # Logs go to disk to avoid pipe deadlocks on a failed encoder.
    with output.with_suffix('.ffmpeg.log').open('wb') as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            for i in range(frames):
                process.stdin.write(frame(scene, plan, index, i / FPS, background).tobytes())
            process.stdin.close()
            if process.wait() != 0:
                raise RuntimeError(f'FFmpeg clip encoding failed; inspect {output.with_suffix(".ffmpeg.log")}')
        except BaseException:
            process.kill()
            process.wait()
            raise
    return output
