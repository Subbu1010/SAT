"""Inline TI-84 calculator icon used by the practice/mock exam launcher."""

from __future__ import annotations

# Compact SVG icon resembling a graphing calculator handset.
TI84_ICON_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="TI-84 calculator">
  <defs>
    <linearGradient id="ti84-body" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2f3f4f"/>
      <stop offset="100%" stop-color="#1b2733"/>
    </linearGradient>
    <linearGradient id="ti84-screen" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#9ed0ff"/>
      <stop offset="100%" stop-color="#5aa7e6"/>
    </linearGradient>
  </defs>
  <rect x="10" y="4" width="44" height="56" rx="6" fill="url(#ti84-body)" stroke="#0f172a" stroke-width="1.5"/>
  <rect x="15" y="10" width="34" height="18" rx="2" fill="url(#ti84-screen)" stroke="#334155" stroke-width="1"/>
  <path d="M18 34h6v6h-6zm10 0h6v6h-6zm10 0h6v6h-6zm-20 10h6v6h-6zm10 0h6v6h-6zm10 0h6v6h-6zm-20 10h28v5H18z" fill="#cbd5e1"/>
  <text x="32" y="22" text-anchor="middle" font-size="7" font-family="Segoe UI, Arial, sans-serif" fill="#0f172a">TI-84</text>
</svg>
""".strip()


def ti84_icon_html() -> str:
    return TI84_ICON_SVG
