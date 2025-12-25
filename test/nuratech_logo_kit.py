# nuratech_logo_kit.py
# Generate a clean, human-grade logo system for NuraTech Systems.
# - Creates SVGs (icon, primary lockup, mono variants)
# - Writes a README with usage + navbar snippet
# - Optionally exports PNGs if cairosvg is available

import os
from textwrap import dedent

# ========= Brand tokens (pulled from your site CSS) =========
PRIMARY = "#1e40af"      # Indigo-800
SECONDARY = "#8b5cf6"    # Violet-500
ACCENT = "#06b6d4"       # Cyan-500
TEXT_PRIMARY = "#1f2937" # Slate-800
WHITE = "#ffffff"
BLACK = "#0b1220"        # Deep navy for dark variant

# ========= Output dirs =========
BASE_DIR = os.path.abspath("./nuratech_logo_kit")
PREVIEW_DIR = os.path.join(BASE_DIR, "previews")
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)

# ========= SVGs =========

ICON_SVG = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="512" height="512" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g1" x1="6" y1="6" x2="58" y2="58" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{PRIMARY}"/>
      <stop offset="1" stop-color="{SECONDARY}"/>
    </linearGradient>
    <linearGradient id="g2" x1="14" y1="14" x2="50" y2="50" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{ACCENT}"/>
      <stop offset="1" stop-color="{PRIMARY}"/>
    </linearGradient>
    <filter id="soft" x="-50%" y="-50%" width="200%" height="200%">
      <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="{PRIMARY}" flood-opacity="0.12"/>
    </filter>
  </defs>

  <!-- Badge -->
  <rect x="4" y="4" width="56" height="56" rx="14" ry="14" fill="url(#g1)" filter="url(#soft)"/>

  <!-- 'N' pillars -->
  <rect x="17" y="16" width="6" height="32" rx="3" fill="{WHITE}" opacity="0.96"/>
  <rect x="41" y="16" width="6" height="32" rx="3" fill="{WHITE}" opacity="0.96"/>

  <!-- Diagonal stroke -->
  <path d="M20 20 L44 44" stroke="{WHITE}" stroke-width="6" stroke-linecap="round" opacity="0.96"/>

  <!-- Automation nodes -->
  <circle cx="26" cy="26" r="2.2" fill="{ACCENT}"/>
  <circle cx="32" cy="32" r="2.2" fill="{WHITE}" opacity="0.95"/>
  <circle cx="38" cy="38" r="2.2" fill="{ACCENT}"/>

  <!-- Forward arrow -->
  <path d="M46 44 L40 40 L40 48 Z" fill="url(#g2)" opacity="0.95"/>
</svg>
"""

PRIMARY_LOCKUP_SVG = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="1200" height="320" viewBox="0 0 1200 320" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="brand" x1="0" y1="0" x2="1200" y2="320" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{PRIMARY}"/>
      <stop offset="1" stop-color="{SECONDARY}"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1200" y2="320" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{ACCENT}"/>
      <stop offset="1" stop-color="{PRIMARY}"/>
    </linearGradient>
  </defs>

  <!-- Icon (scaled) -->
  <g transform="translate(20,20) scale(0.45)">
    <rect x="4" y="4" width="56" height="56" rx="14" ry="14" fill="url(#brand)"/>
    <rect x="17" y="16" width="6" height="32" rx="3" fill="{WHITE}" opacity="0.96"/>
    <rect x="41" y="16" width="6" height="32" rx="3" fill="{WHITE}" opacity="0.96"/>
    <path d="M20 20 L44 44" stroke="{WHITE}" stroke-width="6" stroke-linecap="round" opacity="0.96"/>
    <circle cx="26" cy="26" r="2.2" fill="{ACCENT}"/>
    <circle cx="32" cy="32" r="2.2" fill="{WHITE}" opacity="0.95"/>
    <circle cx="38" cy="38" r="2.2" fill="{ACCENT}"/>
    <path d="M46 44 L40 40 L40 48 Z" fill="url(#accent)" opacity="0.95"/>
  </g>

  <!-- Wordmark -->
  <g transform="translate(180, 60)">
    <text x="0" y="90" font-family="Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif"
          font-weight="800" font-size="120" fill="url(#brand)" letter-spacing="0.5">NuraTech</text>
    <text x="6" y="150" font-family="Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif"
          font-weight="600" font-size="46" fill="{TEXT_PRIMARY}" opacity="0.92" letter-spacing="1">Systems</text>
  </g>
</svg>
"""

MONO_DARK_SVG = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="1200" height="320" viewBox="0 0 1200 320" fill="none" xmlns="http://www.w3.org/2000/svg">
  <g transform="translate(20,20) scale(0.45)">
    <rect x="4" y="4" width="56" height="56" rx="14" ry="14" fill="{BLACK}"/>
    <rect x="17" y="16" width="6" height="32" rx="3" fill="{WHITE}"/>
    <rect x="41" y="16" width="6" height="32" rx="3" fill="{WHITE}"/>
    <path d="M20 20 L44 44" stroke="{WHITE}" stroke-width="6" stroke-linecap="round"/>
    <circle cx="26" cy="26" r="2.2" fill="{WHITE}"/>
    <circle cx="32" cy="32" r="2.2" fill="{WHITE}"/>
    <circle cx="38" cy="38" r="2.2" fill="{WHITE}"/>
    <path d="M46 44 L40 40 L40 48 Z" fill="{WHITE}"/>
  </g>
  <g transform="translate(180, 60)">
    <text x="0" y="90" font-family="Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif"
          font-weight="800" font-size="120" fill="{BLACK}" letter-spacing="0.5">NuraTech</text>
    <text x="6" y="150" font-family="Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif"
          font-weight="600" font-size="46" fill="{BLACK}" opacity="0.85" letter-spacing="1">Systems</text>
  </g>
</svg>
"""

MONO_LIGHT_SVG = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="1200" height="320" viewBox="0 0 1200 320" fill="none" xmlns="http://www.w3.org/2000/svg">
  <g transform="translate(20,20) scale(0.45)">
    <rect x="4" y="4" width="56" height="56" rx="14" ry="14" fill="{WHITE}" stroke="{WHITE}"/>
    <rect x="17" y="16" width="6" height="32" rx="3" fill="{BLACK}"/>
    <rect x="41" y="16" width="6" height="32" rx="3" fill="{BLACK}"/>
    <path d="M20 20 L44 44" stroke="{BLACK}" stroke-width="6" stroke-linecap="round"/>
    <circle cx="26" cy="26" r="2.2" fill="{BLACK}"/>
    <circle cx="32" cy="32" r="2.2" fill="{BLACK}"/>
    <circle cx="38" cy="38" r="2.2" fill="{BLACK}"/>
    <path d="M46 44 L40 40 L40 48 Z" fill="{BLACK}"/>
  </g>
  <g transform="translate(180, 60)">
    <text x="0" y="90" font-family="Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif"
          font-weight="800" font-size="120" fill="{WHITE}" stroke="{BLACK}" stroke-width="2" letter-spacing="0.5">NuraTech</text>
    <text x="6" y="150" font-family="Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif"
          font-weight="600" font-size="46" fill="{BLACK}" opacity="0.92" letter-spacing="1">Systems</text>
  </g>
</svg>
"""

ICON_MONO_SVG = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="256" height="256" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="4" y="4" width="56" height="56" rx="14" ry="14" fill="{BLACK}"/>
  <rect x="17" y="16" width="6" height="32" rx="3" fill="{WHITE}"/>
  <rect x="41" y="16" width="6" height="32" rx="3" fill="{WHITE}"/>
  <path d="M20 20 L44 44" stroke="{WHITE}" stroke-width="6" stroke-linecap="round"/>
</svg>
"""

README = f"""
NuraTech Systems — Logo Kit
===========================

Files
-----
- nuratech_icon.svg — Gradient badge + routed 'N' mark (favicon/app/avatars)
- nuratech_primary_lockup.svg — Icon + 'NuraTech Systems' horizontal wordmark (primary)
- nuratech_lockup_mono_dark.svg — Monochrome dark variant (for light backgrounds)
- nuratech_lockup_mono_light.svg — Monochrome light variant (for dark backgrounds)
- nuratech_icon_mono.svg — Simplified icon for tiny sizes

Brand colors
------------
- Primary: {PRIMARY}
- Secondary: {SECONDARY}
- Accent: {ACCENT}
- Text Primary: {TEXT_PRIMARY}

Navbar drop-in (desktop + mobile)
---------------------------------
HTML:
<a href="#hero" class="logo" aria-label="NuraTech" style="display:inline-flex;align-items:center;gap:.5rem">
  <img src="/assets/brand/nuratech_icon.svg" alt="" width="28" height="28" style="vertical-align:middle" />
  <img src="/assets/brand/nuratech_primary_lockup.svg" alt="NuraTech Systems" style="height:28px;vertical-align:middle" class="hide-on-mobile"/>
  <span class="show-on-mobile" style="font-weight:700;background:linear-gradient(135deg,{PRIMARY},{SECONDARY});-webkit-background-clip:text;-webkit-text-fill-color:transparent">NuraTech</span>
</a>

CSS helpers:
.hide-on-mobile {{ display:inline; }}
.show-on-mobile {{ display:none; }}
@media (max-width: 768px) {{
  .hide-on-mobile {{ display:none; }}
  .show-on-mobile {{ display:inline; }}
}}

Favicons
--------
Use nuratech_icon.svg directly, or export to PNGs (32/192/512).
<link rel="icon" type="image/svg+xml" href="/assets/brand/nuratech_icon.svg">

Design rationale
----------------
- 'N' formed as a routed trace with subtle automation nodes + forward arrow ⇒ motion, integration, progress.
- Rounded badge reads clean at 16–32px. Wordmark uses Inter to match your site—no random fonts.

Tips to avoid the “AI logo” look
--------------------------------
- Keep gradients to the mark or the “NuraTech” text—don’t gradient everything.
- Use one soft shadow max; avoid neon glows and crowded geometry.
"""

# ========= Write files =========
files = {
    "nuratech_icon.svg": ICON_SVG,
    "nuratech_primary_lockup.svg": PRIMARY_LOCKUP_SVG,
    "nuratech_lockup_mono_dark.svg": MONO_DARK_SVG,
    "nuratech_lockup_mono_light.svg": MONO_LIGHT_SVG,
    "nuratech_icon_mono.svg": ICON_MONO_SVG,
    "README.txt": README.strip(),
}

for name, data in files.items():
    with open(os.path.join(BASE_DIR, name), "w", encoding="utf-8") as f:
        f.write(dedent(data))

print(f"Logo kit written to: {BASE_DIR}")

# ========= Optional: export PNGs via cairosvg (if installed) =========
PNG_SIZES = [32, 192, 512]

try:
    import cairosvg  # pip install cairosvg
    for svg_name in [k for k in files.keys() if k.endswith(".svg")]:
        svg_path = os.path.join(BASE_DIR, svg_name)
        for size in PNG_SIZES:
            out_png = os.path.join(PREVIEW_DIR, f"{os.path.splitext(svg_name)[0]}_{size}.png")
            cairosvg.svg2png(url=svg_path, write_to=out_png, output_width=size, output_height=size)
    print(f"PNG previews exported to: {PREVIEW_DIR}")
except Exception as e:
    print("PNG export skipped. To export PNGs, install cairosvg:")
    print("  pip install cairosvg")
    print("Then re-run this script. Error was:", e)
