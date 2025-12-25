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
- Primary: #1e40af
- Secondary: #8b5cf6
- Accent: #06b6d4
- Text Primary: #1f2937

Navbar drop-in (desktop + mobile)
---------------------------------
HTML:
<a href="#hero" class="logo" aria-label="NuraTech" style="display:inline-flex;align-items:center;gap:.5rem">
  <img src="/assets/brand/nuratech_icon.svg" alt="" width="28" height="28" style="vertical-align:middle" />
  <img src="/assets/brand/nuratech_primary_lockup.svg" alt="NuraTech Systems" style="height:28px;vertical-align:middle" class="hide-on-mobile"/>
  <span class="show-on-mobile" style="font-weight:700;background:linear-gradient(135deg,#1e40af,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent">NuraTech</span>
</a>

CSS helpers:
.hide-on-mobile { display:inline; }
.show-on-mobile { display:none; }
@media (max-width: 768px) {
  .hide-on-mobile { display:none; }
  .show-on-mobile { display:inline; }
}

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