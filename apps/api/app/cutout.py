"""Hand-cut sticker edge for generated art (tape collage, doodle): numpy + Pillow only.

If the image already has real transparency (tape motif), cut around its alpha. If it arrived on
paper (doodle), separate ink from the paper colour first. Then dilate into a generous paper
margin and roughen it with low-frequency noise and a coarse polygon feel, like scissors.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def _foreground(img: Image.Image) -> np.ndarray:
    a = np.asarray(img).astype(float)
    alpha = a[..., 3]
    if (alpha < 250).mean() > 0.05:  # real transparency present
        return alpha > 40
    rgb = a[..., :3]
    border = np.concatenate([rgb[:30].reshape(-1, 3), rgb[-30:].reshape(-1, 3), rgb[:, :30].reshape(-1, 3), rgb[:, -30:].reshape(-1, 3)])
    distance = np.sqrt(((rgb - np.median(border, 0)) ** 2).sum(-1))
    smooth = np.asarray(Image.fromarray(np.clip(distance * 4, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), float) / 4
    return smooth > 22


def hand_cut(img: Image.Image, margin: int = 26, seed: int = 5) -> Image.Image:
    img = img.convert('RGBA')
    fg = Image.fromarray((_foreground(img) * 255).astype(np.uint8))
    # close gaps between strokes/pieces, then fill enclosed holes via flood fill from the corner
    closed = fg.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.MinFilter(9))
    holes = closed.copy()
    ImageDraw.floodfill(holes, (0, 0), 128)
    solid = np.asarray(holes) != 128
    # generous margin with a slowly wandering edge
    grown = np.asarray(Image.fromarray((solid * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(margin * 0.9)), float) / 255
    rng = np.random.default_rng(seed)
    h, w = solid.shape
    noise = np.asarray(Image.fromarray(rng.integers(0, 255, (max(h // 40, 2), max(w // 40, 2)), dtype=np.uint8)).resize((w, h), Image.BICUBIC), float) / 255
    cut = (grown + (noise - 0.5) * 0.18) > 0.12
    coarse = Image.fromarray((cut * 255).astype(np.uint8)).resize((max(w // 14, 1), max(h // 14, 1)), Image.BILINEAR).resize((w, h), Image.BILINEAR)
    alpha = coarse.point(lambda v: 255 if v > 128 else 0).filter(ImageFilter.GaussianBlur(0.8))
    base = img.copy()
    if (np.asarray(img)[..., 3] < 250).mean() > 0.05:  # transparent motif: back it with paper inside the cut
        paper = Image.new('RGBA', img.size, (250, 246, 238, 255))
        paper.alpha_composite(img)
        base = paper
    base.putalpha(alpha)
    box = base.getbbox()
    return base.crop(box) if box else base
