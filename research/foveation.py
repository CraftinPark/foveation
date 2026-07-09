#!/usr/bin/env python3
"""
foveation.py — Curcio foveated image representation toolkit
============================================================

Implements the foveated spiral sampling algorithm developed in this research
session.  The algorithm places N points using:

    θ_n = n · 2π/φ²           (golden angle → no moiré)
    r_n = CDF⁻¹(n/N)          (Curcio retinal density model)

    ρ(r) = ρ₀ / (1 + r/r₀)^2.6

The equal-area constraint sets r_max = 2/√π so that π·r_max² = 4 = area of
the normalised 2×2 square frame.

Public API
----------
    build_foveated_points(n_pts)          → x, y, nn (arrays)
    build_blur_stack(img_pil)             → list of blurred arrays
    sample_colours_blur(x,y,nn,blurred)   → colours (blur-averaged, biologically motivated)
    sample_colours_nn(x,y,blurred)        → colours (NN-like, no blur)
    build_voronoi_image(x,y,colours,res)  → uint8 HxWx3 array
    render_comparison(img_path, out_path, crop_centre=None)

    # Image preparation utilities
    pad_to_square_mirrored(img_path, out_path)
    centre_crop_to_square(img_path, out_path)
    crop_centred_at(img_pil, cx, cy)      → PIL Image

Usage examples
--------------
    python foveation.py --image lambo.png --out lambo_comparison.png
    python foveation.py --image lambo.png --out lambo_text.png --cx 2470 --cy 2310

Requirements
------------
    pip install numpy matplotlib Pillow scipy
"""

import argparse
import math
import os
import sys
from typing import Optional, Tuple, List

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree


# ── Global constants ──────────────────────────────────────────────────────────

# Equal-area constraint: π·r_max² = 4 (matches 2×2 normalised square)
R_MAX: float = 2.0 / math.sqrt(math.pi)   # ≈ 1.1284

# Curcio retinal density model parameters
R0: float = R_MAX / 10.0    # plateau radius (inner flat region)
N_EXP: float = 2.6          # exponent — gives ρ ∝ r^(-2.6) in the tail

# Blur mip-map sigma levels (pixels at SRC resolution)
BLUR_SIGMAS: List[float] = [0, 0.5, 1, 2, 4, 8, 16, 32, 64]

# Source resolution for the blur stack (1920×1920)
SRC: int = 1920

# Background colour
BG_HEX: str = "#1a1a2e"
BG_RGB: np.ndarray = np.array([26, 26, 46], dtype=np.uint8)


# ── Core algorithm ────────────────────────────────────────────────────────────

def build_foveated_points(n_pts: int = 65536) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (x, y, nn) for n_pts Curcio+golden-angle foveated points.

    x, y  — normalised coordinates in [-R_MAX, +R_MAX]
    nn    — nearest-neighbour distance for each point (used for dot size /
             blur sigma selection)
    """
    phi = (1 + math.sqrt(5)) / 2
    golden_angle = 2 * math.pi / phi ** 2

    # Curcio CDF inversion: places more points where ρ(r) is high
    r_grid = np.linspace(0, R_MAX, 200_000)
    rho = 1.0 / (1.0 + r_grid / R0) ** N_EXP
    cdf = np.cumsum(rho * r_grid * np.gradient(r_grid))
    cdf /= cdf[-1]

    i_arr = np.arange(n_pts)
    r_pts = np.interp(i_arr / n_pts, cdf, r_grid)
    th_pts = i_arr * golden_angle

    x_pts = r_pts * np.cos(th_pts)
    y_pts = r_pts * np.sin(th_pts)

    # Nearest-neighbour distances
    pts2d = np.column_stack([x_pts, y_pts])
    tree = cKDTree(pts2d)
    nn, _ = tree.query(pts2d, k=2)
    nn = nn[:, 1]   # exclude self

    return x_pts, y_pts, nn


# ── Blur stack ────────────────────────────────────────────────────────────────

def build_blur_stack(img_pil: Image.Image) -> List[np.ndarray]:
    """Return a list of float32 arrays: blurred[i] is the source blurred at
    BLUR_SIGMAS[i] pixels after resizing to SRC×SRC.
    """
    img_src = np.array(
        img_pil.resize((SRC, SRC), Image.LANCZOS), dtype=np.float32
    ) / 255.0
    return [
        gaussian_filter(img_src, [s, s, 0]) if s > 0 else img_src.copy()
        for s in BLUR_SIGMAS
    ]


# ── Pixel coordinate mapping ──────────────────────────────────────────────────

def _to_pixel_coords(
    x_pts: np.ndarray, y_pts: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Map normalised (x, y) in [-R_MAX, R_MAX] to pixel (px, py) in [0, SRC-1].

    y-axis is flipped: +R_MAX (top of image) → row 0.
    """
    px = ((x_pts / R_MAX + 1) / 2 * (SRC - 1)).clip(0, SRC - 1).astype(int)
    py = ((1 - y_pts / R_MAX) / 2 * (SRC - 1)).clip(0, SRC - 1).astype(int)
    return px, py


# ── Colour sampling ───────────────────────────────────────────────────────────

def sample_colours_blur(
    x_pts: np.ndarray,
    y_pts: np.ndarray,
    nn: np.ndarray,
    blurred: List[np.ndarray],
) -> np.ndarray:
    """Sample colour for each foveated point using blur proportional to NN distance.

    Biologically motivated: outer (sparse) points integrate over a larger
    neighbourhood, mimicking the lower acuity of the peripheral retina.

    Returns float32 array of shape (N, 3).
    """
    nn_px = nn * (SRC / 2.0)
    sigma_pts = nn_px / 2.0

    idx_hi = np.searchsorted(BLUR_SIGMAS, sigma_pts).clip(1, len(BLUR_SIGMAS) - 1)
    idx_lo = idx_hi - 1
    s_lo = np.array(BLUR_SIGMAS)[idx_lo]
    s_hi = np.array(BLUR_SIGMAS)[idx_hi]
    denom = s_hi - s_lo
    w = np.where(denom > 0, (sigma_pts - s_lo) / denom, 0.0)

    px, py = _to_pixel_coords(x_pts, y_pts)
    n = len(x_pts)
    colours = np.zeros((n, 3), dtype=np.float32)
    for i in range(n):
        c_lo = blurred[idx_lo[i]][py[i], px[i]]
        c_hi = blurred[idx_hi[i]][py[i], px[i]]
        colours[i] = c_lo * (1 - w[i]) + c_hi * w[i]
    return colours


def sample_colours_nn(
    x_pts: np.ndarray,
    y_pts: np.ndarray,
    blurred: List[np.ndarray],
) -> np.ndarray:
    """Sample colour for each foveated point using the raw (unblurred) pixel.

    NN-like: no spatial averaging.  Equivalent to what NN grid downsampling does.
    Returns float32 array of shape (N, 3).
    """
    px, py = _to_pixel_coords(x_pts, y_pts)
    return blurred[0][py, px]   # blurred[0] is the unblurred source


# ── Voronoi rendering ─────────────────────────────────────────────────────────

def build_voronoi_image(
    x_pts: np.ndarray,
    y_pts: np.ndarray,
    colours: np.ndarray,
    res: int = 2800,
) -> np.ndarray:
    """Build a lossless Voronoi tessellation of the foveated point set.

    Each output pixel is assigned the colour of its nearest foveated point.
    Pixels outside the equal-area circle are set to BG_RGB.

    y-axis convention: row 0 = y = +R_MAX (top of image), matching scatter plots.

    Returns uint8 array of shape (res, res, 3).
    """
    lin_x = np.linspace(-R_MAX, R_MAX, res)
    lin_y = np.linspace(R_MAX, -R_MAX, res)   # reversed: row 0 = top = +R_MAX
    gx, gy = np.meshgrid(lin_x, lin_y)

    pts2d = np.column_stack([x_pts, y_pts])
    tree = cKDTree(pts2d)
    _, idx = tree.query(np.column_stack([gx.ravel(), gy.ravel()]), workers=-1)

    img = (colours[idx] * 255).astype(np.uint8).reshape(res, res, 3)
    img[gx ** 2 + gy ** 2 > R_MAX ** 2] = BG_RGB
    return img


# ── Grid panel helpers ────────────────────────────────────────────────────────

def _make_grid_panels(
    img_pil: Image.Image,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (256×256 NN, 256×256 Lanczos) arrays with circle mask applied."""
    img256_nn = np.array(img_pil.resize((256, 256), Image.NEAREST))
    img256_avg = np.array(img_pil.resize((256, 256), Image.LANCZOS))
    cy, cx = np.ogrid[:256, :256]
    rmask = np.sqrt((cx - 127.5) ** 2 + (cy - 127.5) ** 2) > (256 * R_MAX / 2.0)
    img256_nn[rmask] = 26
    img256_avg[rmask] = 26
    return img256_nn, img256_avg


def _make_original_display(img_pil: Image.Image, res: int = 2800) -> np.ndarray:
    """Return a circle-masked copy of img_pil at resolution res×res."""
    arr = np.array(img_pil.resize((res, res), Image.LANCZOS))
    lin = np.linspace(-R_MAX, R_MAX, res)
    gx, gy = np.meshgrid(lin, lin)
    arr[gx ** 2 + gy ** 2 > R_MAX ** 2] = BG_RGB
    return arr


# ── Crop utilities ────────────────────────────────────────────────────────────

def crop_centred_at(img_pil: Image.Image, cx: int, cy: int) -> Image.Image:
    """Return the largest square crop of img_pil centred at (cx, cy)."""
    W, H = img_pil.size
    half = min(cx, W - cx, cy, H - cy)
    return img_pil.crop((cx - half, cy - half, cx + half, cy + half))


def centre_crop_to_square(img_path: str, out_path: str) -> None:
    """Centre-crop img_path to a square and save to out_path."""
    img = Image.open(img_path).convert("RGB")
    W, H = img.size
    s = min(W, H)
    left = (W - s) // 2
    top = (H - s) // 2
    img.crop((left, top, left + s, top + s)).save(out_path)
    print(f"Centre-cropped {W}×{H} → {s}×{s}: {out_path}")


def pad_to_square_mirrored(img_path: str, out_path: str) -> None:
    """Pad a landscape/portrait image to a square using mirrored + blurred edges."""
    img = Image.open(img_path).convert("RGB")
    W, H = img.size
    S = max(W, H)
    canvas = np.zeros((S, S, 3), dtype=np.uint8)
    # Place original centred
    x0 = (S - W) // 2
    y0 = (S - H) // 2
    canvas[y0:y0 + H, x0:x0 + W] = np.array(img)
    # Fill gaps with blurred mirror of edge rows/columns
    arr_f = canvas.astype(np.float32)
    for _ in range(3):
        arr_f = gaussian_filter(arr_f, [20, 20, 0])
    # Only write into the padded regions
    mask = np.zeros((S, S), dtype=bool)
    mask[y0:y0 + H, x0:x0 + W] = True
    combined = arr_f.astype(np.uint8)
    combined[mask] = np.array(img).reshape(-1, 3)[
        np.where(mask[y0:y0 + H, x0:x0 + W].ravel())
    ]
    # Simpler: rebuild properly
    bg = np.array(Image.fromarray(np.array(img)).resize((S, S), Image.LANCZOS))
    bg_blur = gaussian_filter(bg.astype(np.float32), [40, 40, 0]).astype(np.uint8)
    result = bg_blur.copy()
    result[y0:y0 + H, x0:x0 + W] = np.array(img)
    Image.fromarray(result).save(out_path)
    print(f"Padded {W}×{H} → {S}×{S}: {out_path}")


# ── Main rendering function ───────────────────────────────────────────────────

def render_comparison(
    img_path: str,
    out_path: str,
    n_pts: int = 65536,
    crop_centre: Optional[Tuple[int, int]] = None,
    dpi: int = 400,
    fig_panel_in: float = 7.0,
    voronoi_res: int = 2800,
) -> None:
    """Render a 6-panel comparison figure and save to out_path.

    Panels (left to right):
        1. Original image (or crop) — full data
        2. 256×256 Nearest-Neighbour
        3. 256×256 Lanczos Average
        4. Foveated scatter — blur-averaged
        5. Foveated Voronoi — blur-averaged (lossless)
        6. Foveated scatter — NN-like (no blur)

    All five non-original panels use exactly n_pts data points.

    Parameters
    ----------
    img_path       : Source image (any PIL-readable format).
    out_path       : Output PNG path.
    n_pts          : Number of foveated sample points (default 65536 = 256²).
    crop_centre    : (cx, cy) pixel coords to centre a square crop on.
                     If None, the full (square) image is used.
    dpi            : Output DPI (400 recommended for publication quality).
    fig_panel_in   : Width of each panel in inches.
    voronoi_res    : Pixel resolution of the Voronoi / original panels.
    """
    img_orig = Image.open(img_path).convert("RGB")
    if crop_centre is not None:
        cx, cy = crop_centre
        img_orig = crop_centred_at(img_orig, cx, cy)
        print(f"Crop centred at ({cx},{cy}): {img_orig.size}")

    orig_pts = img_orig.size[0] * img_orig.size[1]
    print(f"Source: {img_orig.size}  ({orig_pts:,} px)")

    # Build foveated point set
    print(f"Building {n_pts:,} foveated points...")
    x_pts, y_pts, nn = build_foveated_points(n_pts)

    # Build blur stack
    print("Building blur stack...")
    blurred = build_blur_stack(img_orig)

    # Sample colours
    print("Sampling blur-averaged colours...")
    c_blur = sample_colours_blur(x_pts, y_pts, nn, blurred)
    print("Sampling NN-like colours...")
    c_nn = sample_colours_nn(x_pts, y_pts, blurred)

    # Voronoi
    print(f"Building Voronoi image ({voronoi_res}×{voronoi_res})...")
    vor_img = build_voronoi_image(x_pts, y_pts, c_blur, res=voronoi_res)

    # Grid panels
    img256_nn, img256_avg = _make_grid_panels(img_orig)
    orig_display = _make_original_display(img_orig, res=voronoi_res)

    # Marker sizes: dot area proportional to NN² so dots just touch
    pts_per_unit = (fig_panel_in * 72) / (2 * R_MAX)
    fill = 1.15
    s_pts = np.pi * (pts_per_unit * fill) ** 2 * nn ** 2

    ext = [-R_MAX, R_MAX, -R_MAX, R_MAX]
    theta = np.linspace(0, 2 * np.pi, 400)

    print(f"Rendering 6-panel at {dpi} dpi...")
    fig, axes = plt.subplots(1, 6, figsize=(fig_panel_in * 6, fig_panel_in))
    fig.patch.set_facecolor(BG_HEX)
    for ax in axes:
        ax.set_facecolor(BG_HEX)
        ax.set_aspect("equal")
        ax.axis("off")

    def t(line1, line2):
        return f"{line1}\n{line2}"

    # Panel 1 — original
    axes[0].imshow(orig_display, extent=ext, origin="upper", aspect="equal")
    axes[0].plot(R_MAX * np.cos(theta), R_MAX * np.sin(theta), "w-", lw=0.8, alpha=0.5)
    axes[0].set_title(
        t(f"Original ({img_orig.size[0]}×{img_orig.size[1]})", f"{orig_pts:,} data points"),
        color="white", fontsize=11, pad=10,
    )

    # Panel 2 — 256×256 NN grid
    axes[1].imshow(img256_nn, extent=ext, origin="upper", aspect="equal")
    axes[1].plot(R_MAX * np.cos(theta), R_MAX * np.sin(theta), "w-", lw=0.8, alpha=0.5)
    axes[1].set_title(
        t("256×256 Nearest-Neighbour", f"{256*256:,} data points"),
        color="white", fontsize=11, pad=10,
    )

    # Panel 3 — 256×256 Lanczos
    axes[2].imshow(img256_avg, extent=ext, origin="upper", aspect="equal")
    axes[2].plot(R_MAX * np.cos(theta), R_MAX * np.sin(theta), "w-", lw=0.8, alpha=0.5)
    axes[2].set_title(
        t("256×256 Lanczos Average", f"{256*256:,} data points"),
        color="white", fontsize=11, pad=10,
    )

    # Panel 4 — foveated scatter (blur)
    axes[3].scatter(x_pts, y_pts, s=s_pts, c=c_blur, linewidths=0, rasterized=True)
    axes[3].plot(R_MAX * np.cos(theta), R_MAX * np.sin(theta), "w-", lw=0.8, alpha=0.5)
    axes[3].set_xlim(-R_MAX, R_MAX)
    axes[3].set_ylim(-R_MAX, R_MAX)
    axes[3].set_title(
        t("Foveated scatter (blur avg)", f"{n_pts:,} data points"),
        color="white", fontsize=11, pad=10,
    )

    # Panel 5 — Voronoi (blur)
    axes[4].imshow(vor_img, extent=ext, origin="upper", aspect="equal")
    axes[4].plot(R_MAX * np.cos(theta), R_MAX * np.sin(theta), "w-", lw=0.8, alpha=0.5)
    axes[4].set_title(
        t("Foveated Voronoi (blur avg)", f"{n_pts:,} data points"),
        color="white", fontsize=11, pad=10,
    )

    # Panel 6 — foveated scatter (NN-like)
    axes[5].scatter(x_pts, y_pts, s=s_pts, c=c_nn, linewidths=0, rasterized=True)
    axes[5].plot(R_MAX * np.cos(theta), R_MAX * np.sin(theta), "w-", lw=0.8, alpha=0.5)
    axes[5].set_xlim(-R_MAX, R_MAX)
    axes[5].set_ylim(-R_MAX, R_MAX)
    axes[5].set_title(
        t("Foveated NN-like (no blur)", f"{n_pts:,} data points"),
        color="white", fontsize=11, pad=10,
    )

    plt.tight_layout(pad=0.4)
    plt.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor=BG_HEX)
    plt.close()

    final_size = Image.open(out_path).size
    print(f"Saved: {out_path}  {final_size}")


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Foveated image comparison renderer (Curcio + golden angle)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--image", required=True, help="Input image path")
    parser.add_argument("--out", required=True, help="Output PNG path")
    parser.add_argument("--n_pts", type=int, default=65536, help="Number of foveated points")
    parser.add_argument("--cx", type=int, default=None, help="Crop centre X pixel")
    parser.add_argument("--cy", type=int, default=None, help="Crop centre Y pixel")
    parser.add_argument("--dpi", type=int, default=400, help="Output DPI")
    parser.add_argument("--voronoi_res", type=int, default=2800, help="Voronoi panel pixel resolution")
    args = parser.parse_args()

    crop_centre = (args.cx, args.cy) if args.cx is not None and args.cy is not None else None

    render_comparison(
        img_path=args.image,
        out_path=args.out,
        n_pts=args.n_pts,
        crop_centre=crop_centre,
        dpi=args.dpi,
        voronoi_res=args.voronoi_res,
    )


if __name__ == "__main__":
    main()
