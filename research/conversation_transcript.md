# Conversation Transcript: Foveated Spiral Sampling Research
**Date:** July 8, 2026

---

## Q: Are almost all image formats 2 dimensional in data representation?

Yes, almost all standard image formats (JPEG, PNG, BMP, GIF, TIFF, WebP, etc.) represent data in 2D — a grid of pixels with width × height dimensions.

Exceptions / nuances:
- **3D / volumetric**: Medical formats like DICOM and NIfTI store 3D voxel grids (e.g., CT/MRI scans).
- **Layered**: PSD (Photoshop) and TIFF support multiple layers/frames, making them effectively 3D (width × height × layers).
- **Animated**: GIF, APNG, and WebP can store multiple frames — a time dimension.
- **HDR / multi-channel**: Some scientific formats (FITS, EXR) store many spectral channels per pixel, going beyond the usual RGB/RGBA.
- **Depth maps**: Formats like depth-JPEG or stereo images store a Z/depth channel alongside color.
- **Cube maps / equirectangular**: Used in 3D graphics, but still stored as flat 2D textures interpreted geometrically.

So the **storage format** is nearly always 2D, but some formats encode higher-dimensional data within that 2D structure.

---

## Q: I'm thinking of a 1 dimensional signal with non-uniform spatial embedding. Perhaps like a fermat spiral, but non-uniform in density.

**The structure you're describing:** A 1D signal s(t) embedded via a curve γ(t) = (x(t), y(t)) into 2D space, where the spatial density ‖dγ/dt‖⁻¹ varies — so equal steps in t map to unequal spatial distances.

**Contrast with Fermat spiral:** Fermat's r = a√θ gives uniform area density (sunflower packing). Your idea decouples the parameterization from spatial uniformity — e.g. denser coils near a region of interest, sparser elsewhere.

**Related concepts:**
- Non-uniform MRI k-space trajectories
- Foveated imaging — higher sample density near gaze center, log-polar falloff outward
- Importance-sampled scanning — adaptive raster where sample rate varies with local signal energy
- Compressed sensing — non-uniform sampling in a transform domain
- Hilbert curve variants

**Key tension:** The non-uniformity creates a mismatch between the 1D index t and spatial position — reconstruction requires knowing γ(t) explicitly, and interpolation onto a regular grid introduces errors unless you account for the Jacobian ‖dγ/dt‖.

---

## Q: Both a storage scheme and sensing model. Does the idea of the spiral make sense to you?

Yes, it makes good sense — and the spiral is a particularly apt choice for both roles simultaneously.

**Why spiral specifically works well:**
- *Continuity* — unlike a raster scan, a spiral is a single unbroken curve with no spatial discontinuities baked into the scan path itself.
- *Locality preservation* — nearby points in 2D tend to be nearby in the 1D index t.
- *Non-uniform density as an implicit attention map* — the winding tightness dr/dθ at each radius encodes how much "bit budget" that region gets.

**As a joint sensing + storage scheme:** The elegant part is that the sensing trajectory **is** the storage layout — no remapping step. The encoder (sensor) produces the 1D signal in order, and the decoder just needs γ(t) to reconstruct spatial positions.

**One non-trivial issue:** Reconstruction from a non-uniform spiral requires scattered-data interpolation. The Jacobian ‖γ̇(t)‖ weights each sample's contribution differently, so naive gridding introduces bias toward densely-sampled regions unless corrected.

---

## Q: The non-uniformity would be determined by the pattern of determining the next distance along the spiral to place the point "pixel". If we follow the fibonacci sequence, I believe that we would end up with a uniform density, is this correct?

Not quite — and the distinction is important.

**Using Fibonacci numbers as step sizes → non-uniform, decreasing density.** Fibonacci terms grow as Fₙ ≈ φⁿ/√5, so the gaps between successive points grow exponentially. You'd get a cluster of closely-spaced points early in the sequence and widely-spaced points later.

**The actual Fibonacci/golden ratio connection to uniform density** comes from using the golden angle ≈ 137.5° for angular placement:
- rₙ = a√n, θₙ = n · 2π/φ²

The golden angle is irrational in a way that maximally avoids resonance, so no two spokes ever overlap — the result is the most uniform packing on a disk.

**For uniform density on a spiral** you need constant arc-length steps Δs = const.

**The interesting inversion:** Your non-uniform scheme runs this backwards — choosing a non-constant step sequence is precisely the mechanism for controlling where density is high vs. low.

---

## Q: Yes, the distances in terms of arc length between each point would expand, but when seen as a coil, the density is uniform, no?

Not quite. On a Fermat spiral, the area per coil turn is constant. For uniform 2D point density, you need a constant number of points per turn, which requires the average step size to scale with circumference: Δs ∝ r.

Fibonacci grows as φⁿ — exponentially. This massively over-compensates. The outer coils would be sampled so sparsely that density collapses rapidly.

**What would actually give uniform density:** You'd want step sizes growing roughly as √n or n^(1/3).

**Fibonacci is a good intentional non-uniformity** — a controllable, analytically clean way to concentrate samples near the center with a known fall-off rate. Just not uniform.

---

## Q: I now want this. Given a coil spatial line, what would the best function be to put the points at, to match the way cones are distributed in the eye?

**The canonical empirical reference: Curcio et al. (1990)**

Human cone density as a function of eccentricity e (mm from fovea):

ρ(r) = ρ₀ / (1 + r/r₀)ⁿ

Approximate values:
- ρ₀ ≈ 150,000 cones/mm² (foveal peak)
- r₀ ≈ 0.3 mm (~1° visual angle) — the half-density radius
- n ≈ 2.6 (fitted exponent)

**Translating to arc-length step sizes on the spiral:**

Δs(r) = r · (1 + r/r₀)ⁿ / (ρ₀ · π a²)

**Important caveats from real retinal anatomy:**
- The distribution is not radially symmetric
- There's a blind spot at ~15° nasal eccentricity
- At very small r (foveola), packing is hexagonal

---

## Q: Can you create a visual with plot points following this along a coil?

*[Generated: foveated_spiral.png, foveated_spiral2.png, foveated_spiral3.png]*

Used the corrected step-size formula:

Δs(r) = r / (π a² · ρ(r))

which explicitly accounts for the coil spacing ≈ πa²/r shrinking inward. Without that factor, the spiral's geometric bias toward placing more arc length in outer regions dominates completely.

Density breakdown with correct formula:
- r=[0,2]: 956 pts  density=76.08/unit²
- r=[2,4]: 203 pts  density=5.38/unit²
- r=[4,6]: 116 pts  density=1.85/unit²
- r=[6,8]:  76 pts  density=0.86/unit²
- r=[8,10]: 55 pts  density=0.49/unit²

---

## Q: What function are we using for the spiral?

A **Fermat spiral** (parabolic spiral): r = a√θ

x(θ) = a√θ · cos θ,  y(θ) = a√θ · sin θ

**Key property:** equal increments of θ trace equal areas — the coils are uniformly spaced in radius, which makes it the natural base for a 2D density-matched sampling scheme.

---

## Q: My intention is that in terms of 2D space, the points across the spiral would be most dense in regards to all directions, not only along the line.

This reveals a fundamental tension with the Fermat spiral. The coil-to-coil spacing on a Fermat spiral is:

Δr_coil ≈ πa²/r

This is **large near center** (small r) and shrinks outward. So even if you pack points tightly along the arc near center, the adjacent coil is far away — the density is anisotropic.

For isotropic spacing you'd need Δs(r) ≈ Δr_coil(r), which forces ρ(r) ∝ r² — i.e. density increasing outward. The opposite of foveated.

**The Fermat spiral is the wrong base geometry for isotropic foveated packing.** Better options:
- Variable-pitch spiral where the coil spacing itself shrinks toward center
- Log-polar hex grid
- Sunflower with adaptive density

*[Generated: spiral_comparison.png, spiral_comparison2.png]*

Key fix: Variable-pitch spiral with dr/dθ = b(r)/(2π), b(r) = b₀(1 + r/r₀)^(n/2). This ensures coil spacing = b(r) and along-arc step = b(r), so both match at every radius.

---

## Q: What is the function of spiral of Archimedes?

r = aθ

In Cartesian: x(θ) = aθ cos θ,  y(θ) = aθ sin θ

**Key property:** constant coil spacing Δr_coil = 2πa = const. The spiral you'd get by winding a rope of uniform thickness.

---

## Q: Now, plot points that are linear along the arc length of the spiral, just 1, 2, 3, 4

*[Generated: archimedes_pts.png]*

Each point is at exactly s = L/4, L/2, 3L/4, L along the spiral's total arc length (~179.7 units). Points cluster toward the outer coils because the outer arc is much longer per turn.

---

## Q: Now do it with 100 points

*[Generated: archimedes_100pts.png]*

The clustering toward the outer coils is very clear — the inner coils get only a handful of points because those coils have much shorter arc length.

---

## Q: Make the arc length for the point to sit on 10x bigger than the idx of the point. So e.g. point 100 is at arc length 1000

*[Generated: archimedes_linear_s.png]*

Now the distribution is much more even across coils — the spacing between consecutive points is visually consistent all the way from center to edge.

---

## Q: Make the factor 100 and now do it for 1000 points

*[Generated: archimedes_1000pts.png]*

~73 turns, 1000 uniformly arc-length-spaced points. The density across all coils looks very consistent — roughly the same number of points per coil throughout.

---

## Q: Can we pick a parameter for distancing that will avoid the moiré effect?

Yes — the golden ratio.

**Why moiré appears:** Wherever N_turn(r) = 2πr/Δs is close to an integer, points on adjacent coils align radially — that's the moiré spoke pattern.

**The fix:** Choose Δs so that N_turn is φ² ≈ 2.618 at the characteristic radius. The golden ratio φ = (1+√5)/2 is the most irrational number — maximally resists resonance at any rational approximation.

For a fixed-step Archimedean spiral, best step: Δs = 2πr* / φ²

*[Generated: moire_comparison.png]*

The comparison shows:
- **Fixed Δs=100**: radial spokes clearly visible
- **Golden angle Δθ=137.5°**: completely uniform, featureless disk — the classic sunflower pattern

---

## Q: What is the formula for the distancing? It is no longer linear right?

Correct, it's no longer linear. In the golden angle scheme:

θₙ = n·Δθ,  rₙ = a·n·Δθ

Arc-length spacing grows **linearly with n**: Δsₙ ≈ Δθ · rₙ

Summary of schemes:
| Scheme | Δsₙ | 2D density |
|---|---|---|
| Fixed arc-length | const | uniform (but moiré) |
| Golden angle | ∝ n ∝ r | ∝ 1/r² (sparse center) |
| Foveated (cone density) | ∝ r·(1+r/r₀)^(n/2) | dense center, sparse periphery |

---

## Q: Can we try Fibonacci sequence and giving me the visual?

*[Generated: fibonacci_pts.png]*

The exponential nature of Fibonacci is brutally clear. Only 25 points fit within arc-length 100,000 (F₂₅ = 75025). The first ~18 points are all crammed into a tiny central blob near the origin. Only the last 4–5 points make it out to the outer half of the field.

This confirms Fibonacci gives an extremely aggressive center-heavy concentration — far more so than the retinal cone density model.

---

## Q: Let's no longer make the factor 100, but just 1

*[Generated: archimedes_factor1.png]*

About 7 turns, covering arc length 0→1000. The uniform spacing is very clear — each coil has roughly the same number of points (~140/turn), and the gaps between consecutive points are visually identical all the way around.

---

## Q: Oh when we did fibonacci, we didn't do 1×100, 1×100, 2×100, 3×100?

Correct — the Fibonacci plot used raw Fibonacci values as arc-lengths directly (s = 1, 1, 2, 3, 5, 8, …), not scaled by 100. So it was effectively factor=1 already, just with only 25 points.

To match the spirit of the other plots: s_n = 100·F_n would push the outermost point to arc-length 7.5 million.

---

## Q: What would be the next after linear to make it biased to have more points spatially near the center and more sparse outward?

The natural ladder between linear and exponential is **power laws**: sᵢ = iᵖ

The 2D density produced: ρ(r) ∝ r^(2/p - 2)

| p | sᵢ | ρ(r) | character |
|---|---|---|---|
| 1 | i | r⁰ = const | uniform |
| 1.5 | i^1.5 | r^(-2/3) | very gentle bias |
| **2** | **i²** | **r⁻¹** | **mild — good next step** |
| 3 | i³ | r^(-4/3) | moderate |
| 4 | i⁴ | r^(-3/2) | strong |

The retinal cone model (Curcio) has ρ ∝ r^(-2.6), which corresponds roughly to p ≈ 3.7.

---

## Q: Try 2

*[Generated: power2_pts.png]*

p=2 gives ρ ∝ 1/r (mild center bias). The inner region is denser but the outer field still gets reasonable coverage. Some moiré spokes visible because the quadratic spacing isn't resonance-free.

---

## Q: Try retina

*[Generated: retina_pts.png]*

Used p=3.7. Density breakdown:
- Inner 20%: 418 pts
- Next 20%: 191 pts
- ...down to 113 in outer 20% (4:1 ratio)

**Correction noted:** p=3.7 actually gives ρ ∝ r^(-1.46), not r^(-2.6) as claimed. The power-law arc-length scheme on an Archimedean spiral cannot match Curcio's steep profile — the steepest achievable is r^(-2) (as p→∞).

---

## Q: How did you come to the conclusion that 3.7 is retina? Does it match the diagram?

The derivation was flawed. Correcting:

On an Archimedean spiral, r ∝ n^(p/2), giving ρ(r) ∝ r^(2/p - 2).

For any finite positive p, steepest possible fall-off is r^(-2) (as p→∞). To get r^(-2.6) you'd need 2/p - 2 = -2.6, i.e. 2/p = -0.6 — **impossible**.

The Curcio model ρ(r) = ρ₀/(1+r/r₀)^2.6 cannot be reproduced by arc-length spacing on a simple Archimedean spiral. The variable-pitch spiral approach is required.

---

## Q: Can we try p = π?

*[Generated: pi_pts.png]*

ρ ∝ r^(2/π - 2) ≈ r^(-1.36) — moderately center-biased.

Density: 358/200/164/145/132 across 5 radial zones (2.7:1 ratio inner to outer).

Artifacts noted: localized dense areas in outer portions — a moiré-like effect.

---

## Q: Is the moiré avoidable by changing our parameter somehow?

Yes. The cause: N_turn(r) = 2πr/Δs(r) changes with radius. Every time it crosses an integer, spokes form.

The two clean solutions:
| Approach | How | Trade-off |
|---|---|---|
| **Golden angle** | Δθ = 2π/φ² always | No moiré, density fixed at ∝ 1/r² |
| **Variable-pitch spiral** | Coil spacing = b(r), step = b(r) | Tunable density + no moiré, complex path |

---

## Q: I don't understand the variable pitch approach

The core problem: Archimedean coil spacing is fixed at Δr_coil = 2πa everywhere. When you put fewer points per turn in outer region, adjacent coils have large gaps creating ring artefacts.

**The key insight:** For no moiré, you want exactly 1 point per coil gap — i.e. the along-arc spacing between consecutive points equals the coil-to-coil spacing at that radius.

**What variable-pitch does:** Instead of fixing Δr_coil, you let the coil spacing be a function of radius: Δr_coil(r) = b(r). Then you also set the along-arc step = b(r). Both spacings match everywhere.

The spiral equation: dr/dθ = b(r)/(2π)

Visual analogy:
- Archimedean = rope wound with constant thickness → equal gaps always
- Variable-pitch = rope that gets thicker outward → wider gaps outward, tight near center

*[Generated: vp_pi.png]*

Result: no moiré, density follows p=π profile, NN lines point in all directions (isotropic).

---

## Q: We get a different moiré effect — lines coming out from the center. Is this avoidable?

Yes. Cause: with ~1 point per coil turn, consecutive points step by nearly the same angle each time. When that angle is close to a rational fraction of 2π, radial spokes form.

**The fix:** Decouple angular placement from the spiral march — use golden angle for θ and derive r from the desired density:

θₙ = n · 2π/φ²,    rₙ = r_max · (n/N)^(p/2)

- **θ** controls moiré → use golden angle
- **r** controls density profile → use power law

*[Generated: golden_pi.png]*

Both problems solved simultaneously. No spokes, no rings, smooth density gradient matching p=π.

---

## Q: The drop-off is not as steep as the retina. What parameters can we change?

Two levers:

**Option 1: Increase p.** But the hard limit is r^(-2) (as p→∞) — retina needs r^(-2.6), beyond what power law can achieve.

**Option 2: Use the actual Curcio CDF to place rₙ.** Invert the cumulative density directly:

n/N = ∫₀^rₙ ρ(r) r dr / ∫₀^r_max ρ(r) r dr,   ρ(r) = ρ₀/(1+r/r₀)^2.6

This is the only way to faithfully match the retinal profile — handles the flat plateau near center (no singularity at r=0) and the steep r^(-2.6) tail correctly.

**Recommendation:** Option 2 with golden angle for θ.

*[Generated: curcio_golden.png]*

Result:
- Inner 20%: **435 pts**
- Zones: 435 → 254 → 145 → 97 → 68 (6.4:1 ratio inner to outer)
- No moiré — golden angle keeps all points structurally anti-resonant
- NN distance uniformly green (isotropic) across full field

---

## Final Summary: Methods Explored

| Method | File | Key Property |
|---|---|---|
| Fermat spiral, foveated step | foveated_spiral3.png | Correct 2D density but anisotropic |
| Variable-pitch vs Fermat comparison | spiral_comparison2.png | Isotropy comparison |
| Archimedean, plain line | archimedean.png | Baseline |
| Archimedean, 4 pts linear s | archimedes_pts.png | Arc-length placement demo |
| Archimedean, 100 pts linear s | archimedes_100pts.png | Outer clustering visible |
| Archimedean, s=10·i, 100 pts | archimedes_linear_s.png | More even distribution |
| Archimedean, s=100·i, 1000 pts | archimedes_1000pts.png | Consistent coil density |
| Fixed Δs vs golden angle | moire_comparison.png | Moiré elimination demo |
| Fibonacci arc-length positions | fibonacci_pts.png | Exponential clustering |
| Archimedean, s=i, 1000 pts | archimedes_factor1.png | Factor=1 baseline |
| Power law p=2 | power2_pts.png | ρ ∝ 1/r, mild bias |
| Power law p=3.7 (approx retina) | retina_pts.png | ρ ∝ r^(-1.46) |
| Power law p=π | pi_pts.png | ρ ∝ r^(-1.36), moiré present |
| Variable-pitch p=π | vp_pi.png | Isotropic, moiré-free spiral |
| Golden angle + power law p=π | golden_pi.png | No moiré, correct density |
| Golden angle + Curcio CDF | curcio_golden.png | **Best: faithful retinal model, no moiré** |

### Final Best Method: Curcio CDF + Golden Angle

```
θₙ = n · 2π/φ²                           (golden angle, anti-moiré)
rₙ = CDF⁻¹(n/N)  where CDF from ρ(r) = ρ₀/(1+r/r₀)^2.6   (Curcio retinal model)
```

Two independent parameters, two independent concerns, both solved cleanly.

---

## Session 2: Image Representation and Codec Comparison

---

## Q: We are now going to represent an image using a standard coordinate scheme (2D matrix) and represent it with our plotting

**Goal:** Map real image pixels onto the Curcio+golden-angle foveated point field (65536 points in a circle of radius r_max = 2/√π), using a blur mip-map to sample the appropriate level of detail at each point's spatial scale.

**Approach:**
- Resize source image to 1920×1920 as the blur base
- Build 9-level mip-map: σ = [0, 0.5, 1, 2, 4, 8, 16, 32, 64] px
- For each foveated point, compute NN distance → blur sigma → interpolate between adjacent mip levels
- Map (x, y) in [–r_max, +r_max]² to pixel coordinates in the source
- Render as scatter plot with variable dot size proportional to NN distance

**Equal-area constraint:** Set r_max = 2/√π ≈ 1.1284 so π·r_max² = 4 = area of the 2×2 square — the circle and square frame the same total area.

*[Generated: superman_foveated.png, superman_foveated_equalarea.png]*

---

## Q: Let's compare: lambo.png as a high-definition image vs our foveated representation

**4-panel comparison layout:**
1. 256×256 Nearest-Neighbour downsampled
2. 256×256 Lanczos average downsampled
3. Foveated 65536pts — uniform dot (median NN distance)
4. Foveated 65536pts — variable dot (dot size ∝ NN distance)

All panels use equal-area circle mask (r_max = 1.1284).

**Image preparation:**
- `lambo.png` (3840×2160 landscape) → padded to 3840×3840 square with mirrored + Gaussian-blurred edge fill
- `cat.png` (7952×5304) → centre-cropped to 5304×5304, then face-centred to 5038×5038
- `tree.jpg` (4928×3264) → centre-cropped to 3264×3264

**Dot size tuning:** fill factor iterated 0.60 → 1.15 to eliminate black voids between outer (peripheral) points.

*[Generated: lambo_comparison.png (150 dpi), lambo.png (padded), cat.png (face-centred), tree.jpg (square-cropped)]*
*[Generated: tree_comparison.png]*

---

## Q: Are we losing information in the rendering of the foveation due to 2D rendering?

**Three distinct loss mechanisms identified:**

| Loss type | Cause | Severity |
|---|---|---|
| **Dot occlusion** | Dense fovea: dots overlap, inner colours hidden | High — fundamental |
| **Sub-pixel dots** | Outer peripheral: dots smaller than 1 render pixel | Medium — resolution-dependent |
| **Rasterizer blending** | Anti-aliased dot edges mix background colour into sampled colour | Low |

**Resolution scaling (400 DPI):** Helps sub-pixel loss. At 400 dpi, 7" panels = 2800 px/panel → peripheral dots now occupy ≥1 px each.

**Voronoi tessellation:** The correct information-preserving representation. Assign each output pixel to the colour of its nearest foveated point. Every sampled colour is visible; cell boundaries encode density.

*[Generated: lambo_comparison_hires.png (400 dpi, 11127×2942), tree_comparison_hires.png (400 dpi, 11218×2950)]*

---

## Q: Do it for tree as well. Also do Voronoi

**Voronoi implementation:**
```python
lin_x = np.linspace(-r_max, r_max, VORONOI_RES)
lin_y = np.linspace(-r_max, r_max, VORONOI_RES)
gx, gy = np.meshgrid(lin_x, lin_y)
_, idx = cKDTree(pts2d).query(flat, workers=-1)
voronoi_img = colours[idx].reshape(RES, RES, 3)
voronoi_img[gx**2 + gy**2 > r_max**2] = BG_colour
```

4-panel: NN256 | avg256 | scatter | Voronoi — for both lambo and tree.

Voronoi cell boundaries naturally encode the density gradient: tiny cells at the fovea (high density), large cells at periphery (low density). This is lossless — every one of the 65536 sampled colours is represented.

*[Generated: lambo_voronoi.png (11218×2950), tree_voronoi.png (11218×2950)]*

---

## Q: Can we do something similar to what nearest neighbor would do for foveation? Also: lambo centered at text (x=2470, y=2310), full 5-panel comparison. Fix Voronoi inversion.

### Foveated NN-like rendering

**Current method (blur-averaged):** Each foveated point samples a Gaussian-blurred version of the source, with blur sigma proportional to its NN distance. Outer points (large NN gaps) get heavy blurring — an area-average of the local neighbourhood.

**NN-like method:** Each point samples the raw unblurred pixel at its exact location (sigma=0 for all points, equivalent to `blurred[0][py, px]`). No spatial averaging. Matches what NN grid downsampling does — take the nearest pixel value directly.

**Perceptual effect:** The periphery shows sharp/aliased colours (no low-pass before sampling), while the fovea centre remains dense regardless. This inverts the biological sense (real retina averages more at the periphery) but reveals what information was being concealed by the blur.

*[Generated: lambo_foveated_nn_vs_avg.png (5601×2927), tree_foveated_nn_vs_avg.png (5601×2927)]*
→ Left panel: Foveated NN-like (no blur) | Right panel: Foveated blur-averaged

### Voronoi y-axis inversion fix

**Problem:** `np.meshgrid(lin, lin)` with `lin = linspace(-r_max, r_max)` produces row 0 at gy=–r_max. With `imshow(origin='upper')`, row 0 renders at the top — so gy=–r_max (foveated bottom) appeared at top of image.

**Fix:** Reverse the y linspace:
```python
lin_y = np.linspace(r_max, -r_max, res)   # row 0 = +r_max = top of image ✓
lin_x = np.linspace(-r_max, r_max, res)
gx, gy = np.meshgrid(lin_x, lin_y)
```

*[Regenerated: lambo_voronoi.png, tree_voronoi.png (y-axis corrected)]*

### Lambo text-centred 5-panel

**Crop:** From padded lambo.png (3840×3840), centred at (x=2470, y=2310):
- half_size = min(2470, 1370, 2310, 1530) = 1370
- Crop box: (1100, 940, 3840, 3680) → 2740×2740 px

**5-panel layout:**
1. 256×256 Nearest-Neighbour
2. 256×256 Lanczos Average
3. Foveated scatter — blur-averaged (variable dot, fill=1.15)
4. Foveated Voronoi — blur-averaged (y-axis fixed)
5. Foveated scatter — NN-like (no blur, variable dot)

*[Generated: lambo_text_5panel.png (14017×2946)]*


---

## Q: Can we add the original into the 5-panel one

Added original crop as the first panel, making it a 6-panel layout. The original is displayed at full quality (resized to 2800×2800 for rendering) with the same equal-area circle mask applied. Regenerated `lambo_text_5panel.png` as a 6-panel (16817×2942).

**6-panel layout:**
1. Original (2740×2740 crop)
2. 256×256 Nearest-Neighbour
3. 256×256 Lanczos Average
4. Foveated scatter (blur avg)
5. Foveated Voronoi (blur avg)
6. Foveated NN-like (no blur)

*[Regenerated: lambo_text_5panel.png (16817×2942)]*

---

## Q: Can you confirm, all of the images in the lambo_text_5panel (except for the original) have 65,536 data points only

**Confirmed — yes.** All five non-original panels encode exactly 65,536 data points:

| Panel | Data points | How |
|---|---|---|
| 256×256 Nearest-Neighbour | 256 × 256 = **65,536** pixels | One source sample per output grid cell |
| 256×256 Lanczos Average | 256 × 256 = **65,536** pixels | One weighted-average sample per output grid cell |
| Foveated scatter (blur avg) | **65,536** foveated points | One sample per Curcio+golden-angle point |
| Foveated Voronoi (blur avg) | **65,536** unique colour values | Same 65,536 samples; Voronoi cells extrapolate to fill display pixels |
| Foveated NN-like (no blur) | **65,536** foveated points | Same geometry, raw unblurred pixel per point |

The Voronoi panel renders at 2800×2800 (7.84M display pixels) but carries no new information — every pixel is assigned the colour of its nearest foveated point, so only 65,536 unique values exist in the data.

The original crop is 2740×2740 = **7,507,600 data points** — a ~115:1 ratio vs the compressed representations.

---

## Q: Can we make that explicit in the labels (the data point counts)

Added a second subtitle line to every panel showing the data point count. Panel titles are now two-line:

- `"Original (2740×2740 crop)" / "7,507,600 data points"`
- `"256×256 Nearest-Neighbour" / "65,536 data points"`
- `"256×256 Lanczos Average" / "65,536 data points"`
- `"Foveated scatter (blur avg)" / "65,536 data points"`
- `"Foveated Voronoi (blur avg)" / "65,536 data points"`
- `"Foveated NN-like (no blur)" / "65,536 data points"`

The 7,507,600 vs 65,536 contrast on the original makes the ~115:1 compression ratio immediately visible at a glance.

*[Regenerated: lambo_text_5panel.png (16783×2983)]*

