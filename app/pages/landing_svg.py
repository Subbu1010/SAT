"""Inline SVG illustrations for the guest landing page."""

from __future__ import annotations


def hero_device_svg() -> str:
    """Laptop mockup showing a digital SAT module screen."""
    return """
<svg class="landing-hero-illus" viewBox="0 0 400 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Digital SAT on laptop">
  <defs>
    <linearGradient id="screenGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#e8f2ff"/>
      <stop offset="100%" style="stop-color:#d4e8ff"/>
    </linearGradient>
    <linearGradient id="laptopGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#5ba0ff"/>
      <stop offset="100%" style="stop-color:#2d7ff9"/>
    </linearGradient>
  </defs>
  <ellipse cx="200" cy="258" rx="150" ry="12" fill="rgba(45,127,249,0.15)"/>
  <rect x="55" y="30" width="290" height="185" rx="12" fill="url(#laptopGrad)"/>
  <rect x="68" y="42" width="264" height="155" rx="6" fill="url(#screenGrad)" stroke="#b8d4ff" stroke-width="1"/>
  <rect x="78" y="52" width="120" height="8" rx="4" fill="#2d7ff9" opacity="0.7"/>
  <rect x="78" y="68" width="200" height="6" rx="3" fill="#60738f" opacity="0.35"/>
  <rect x="78" y="80" width="180" height="6" rx="3" fill="#60738f" opacity="0.25"/>
  <rect x="78" y="100" width="220" height="28" rx="6" fill="#fff" stroke="#2d7ff9" stroke-width="1.5"/>
  <rect x="78" y="136" width="220" height="28" rx="6" fill="#fff" stroke="#e8eef5" stroke-width="1"/>
  <rect x="78" y="172" width="220" height="28" rx="6" fill="#fff" stroke="#e8eef5" stroke-width="1"/>
  <circle cx="92" cy="114" r="6" fill="none" stroke="#2d7ff9" stroke-width="1.5"/>
  <circle cx="92" cy="150" r="6" fill="none" stroke="#9aadc4" stroke-width="1.5"/>
  <rect x="300" y="52" width="24" height="10" rx="5" fill="#1b9c6e"/>
  <text x="312" y="60" text-anchor="middle" fill="#fff" font-size="6" font-weight="700">32:00</text>
  <path d="M30 218 L370 218 L385 240 L15 240 Z" fill="#1262e0"/>
  <rect x="170" y="225" width="60" height="4" rx="2" fill="#5ba0ff"/>
  <circle cx="330" cy="175" r="28" fill="#fff" stroke="#2d7ff9" stroke-width="2"/>
  <text x="330" y="172" text-anchor="middle" fill="#2d7ff9" font-size="11" font-weight="800">SAT</text>
  <text x="330" y="184" text-anchor="middle" fill="#60738f" font-size="7">Digital</text>
</svg>
"""


def structure_timeline_svg() -> str:
    """Vertical test-day structure infographic."""
    return """
<svg class="landing-infographic" viewBox="0 0 720 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="SAT test structure timeline">
  <defs>
    <linearGradient id="rwGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#5ba0ff"/><stop offset="100%" style="stop-color:#2d7ff9"/>
    </linearGradient>
    <linearGradient id="mathGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#34c38f"/><stop offset="100%" style="stop-color:#1b9c6e"/>
    </linearGradient>
    <linearGradient id="breakGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#ffc107"/><stop offset="100%" style="stop-color:#ff9800"/>
    </linearGradient>
  </defs>
  <text x="360" y="28" text-anchor="middle" fill="currentColor" font-size="16" font-weight="800">Test Day Structure</text>
  <text x="360" y="48" text-anchor="middle" fill="#60738f" font-size="11">2 hr 14 min · 98 questions · 10 min break</text>
  <!-- R&W header -->
  <rect x="40" y="68" width="640" height="36" rx="8" fill="url(#rwGrad)"/>
  <text x="60" y="91" fill="#fff" font-size="13" font-weight="700">📖 Reading and Writing</text>
  <text x="680" y="91" text-anchor="end" fill="#fff" font-size="11">64 min · 54 questions</text>
  <!-- R&W modules -->
  <rect x="60" y="118" width="280" height="72" rx="10" fill="#e8f2ff" stroke="#5ba0ff" stroke-width="1.5"/>
  <text x="200" y="142" text-anchor="middle" fill="#1262e0" font-size="12" font-weight="700">Module 1</text>
  <text x="200" y="162" text-anchor="middle" fill="#60738f" font-size="11">32 min · 27 questions</text>
  <text x="200" y="178" text-anchor="middle" fill="#60738f" font-size="10">Mixed difficulty</text>
  <path d="M350 154 L380 154" stroke="#5ba0ff" stroke-width="2" marker-end="url(#arrow)"/>
  <rect x="390" y="118" width="280" height="72" rx="10" fill="#d4e8ff" stroke="#2d7ff9" stroke-width="1.5"/>
  <text x="530" y="142" text-anchor="middle" fill="#1262e0" font-size="12" font-weight="700">Module 2</text>
  <text x="530" y="162" text-anchor="middle" fill="#60738f" font-size="11">32 min · 27 questions</text>
  <text x="530" y="178" text-anchor="middle" fill="#60738f" font-size="10">Easier OR harder</text>
  <!-- Break -->
  <rect x="260" y="208" width="200" height="32" rx="16" fill="url(#breakGrad)"/>
  <text x="360" y="229" text-anchor="middle" fill="#fff" font-size="11" font-weight="700">☕ 10-minute break</text>
  <!-- Math header -->
  <rect x="40" y="258" width="640" height="36" rx="8" fill="url(#mathGrad)"/>
  <text x="60" y="281" fill="#fff" font-size="13" font-weight="700">🔢 Math</text>
  <text x="680" y="281" text-anchor="end" fill="#fff" font-size="11">70 min · 44 questions</text>
  <!-- Math modules -->
  <rect x="60" y="308" width="280" height="72" rx="10" fill="#e6faf3" stroke="#34c38f" stroke-width="1.5"/>
  <text x="200" y="332" text-anchor="middle" fill="#0d5c41" font-size="12" font-weight="700">Module 1</text>
  <text x="200" y="352" text-anchor="middle" fill="#60738f" font-size="11">35 min · 22 questions</text>
  <text x="200" y="368" text-anchor="middle" fill="#60738f" font-size="10">Mixed difficulty</text>
  <path d="M350 344 L380 344" stroke="#34c38f" stroke-width="2"/>
  <polygon points="380,344 372,340 372,348" fill="#34c38f"/>
  <rect x="390" y="308" width="280" height="72" rx="10" fill="#d0f5e8" stroke="#1b9c6e" stroke-width="1.5"/>
  <text x="530" y="332" text-anchor="middle" fill="#0d5c41" font-size="12" font-weight="700">Module 2</text>
  <text x="530" y="352" text-anchor="middle" fill="#60738f" font-size="11">35 min · 22 questions</text>
  <text x="530" y="368" text-anchor="middle" fill="#60738f" font-size="10">Easier OR harder</text>
</svg>
"""


def adaptive_flow_svg() -> str:
    """Section-adaptive branching diagram."""
    return """
<svg class="landing-infographic" viewBox="0 0 720 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Section adaptive testing flow">
  <defs>
    <marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#5ba0ff"/>
    </marker>
  </defs>
  <text x="360" y="22" text-anchor="middle" fill="currentColor" font-size="14" font-weight="800">How Section-Adaptive Testing Works</text>
  <rect x="30" y="50" width="150" height="110" rx="12" fill="#e8f2ff" stroke="#5ba0ff" stroke-width="2"/>
  <text x="105" y="78" text-anchor="middle" fill="#1262e0" font-size="12" font-weight="700">Module 1</text>
  <text x="105" y="98" text-anchor="middle" fill="#60738f" font-size="10">Easy + Medium</text>
  <text x="105" y="114" text-anchor="middle" fill="#60738f" font-size="10">+ Hard mix</text>
  <text x="105" y="140" text-anchor="middle" fill="#2d7ff9" font-size="10" font-weight="600">Your performance →</text>
  <line x1="180" y1="105" x2="250" y2="105" stroke="#5ba0ff" stroke-width="2" marker-end="url(#arr)"/>
  <rect x="260" y="40" width="200" height="55" rx="10" fill="#d4e8ff" stroke="#2d7ff9" stroke-width="1.5"/>
  <text x="360" y="62" text-anchor="middle" fill="#1262e0" font-size="11" font-weight="700">Module 2 — Standard</text>
  <text x="360" y="80" text-anchor="middle" fill="#60738f" font-size="9">Solid Module 1 performance</text>
  <rect x="260" y="115" width="200" height="55" rx="10" fill="#fff3e0" stroke="#ff9800" stroke-width="1.5"/>
  <text x="360" y="137" text-anchor="middle" fill="#e65100" font-size="11" font-weight="700">Module 2 — Advanced</text>
  <text x="360" y="155" text-anchor="middle" fill="#60738f" font-size="9">Strong Module 1 performance</text>
  <line x1="460" y1="67" x2="520" y2="67" stroke="#5ba0ff" stroke-width="1.5" marker-end="url(#arr)"/>
  <line x1="460" y1="142" x2="520" y2="142" stroke="#ff9800" stroke-width="1.5" marker-end="url(#arr)"/>
  <rect x="530" y="50" width="160" height="110" rx="12" fill="#f0f5fc" stroke="#60738f" stroke-width="1" stroke-dasharray="4"/>
  <text x="610" y="78" text-anchor="middle" fill="currentColor" font-size="11" font-weight="700">Scored with</text>
  <text x="610" y="96" text-anchor="middle" fill="currentColor" font-size="11" font-weight="700">IRT weighting</text>
  <text x="610" y="118" text-anchor="middle" fill="#60738f" font-size="9">Harder Module 2</text>
  <text x="610" y="134" text-anchor="middle" fill="#60738f" font-size="9">= higher score</text>
  <text x="610" y="150" text-anchor="middle" fill="#60738f" font-size="9">potential</text>
</svg>
"""


def content_donut_svg(
    segments: list[tuple[str, int, str]],
    *,
    title: str,
    center_label: str,
) -> str:
    """Simple donut chart via SVG arcs."""
    import math

    cx, cy, r_outer, r_inner = 80, 80, 68, 42
    total = sum(p for _, p, _ in segments) or 1
    paths = []
    start_angle = -90
    legend = []
    for label, pct, color in segments:
        sweep = (pct / total) * 360
        end_angle = start_angle + sweep
        s_rad = math.radians(start_angle)
        e_rad = math.radians(end_angle)
        x1o = cx + r_outer * math.cos(s_rad)
        y1o = cy + r_outer * math.sin(s_rad)
        x2o = cx + r_outer * math.cos(e_rad)
        y2o = cy + r_outer * math.sin(e_rad)
        x1i = cx + r_inner * math.cos(e_rad)
        y1i = cy + r_inner * math.sin(e_rad)
        x2i = cx + r_inner * math.cos(s_rad)
        y2i = cy + r_inner * math.sin(s_rad)
        large = 1 if sweep > 180 else 0
        paths.append(
            f'<path d="M{x1o:.1f},{y1o:.1f} A{r_outer},{r_outer} 0 {large},1 {x2o:.1f},{y2o:.1f} '
            f'L{x1i:.1f},{y1i:.1f} A{r_inner},{r_inner} 0 {large},0 {x2i:.1f},{y2i:.1f} Z" fill="{color}"/>'
        )
        legend.append(
            f'<div class="landing-domain-item">'
            f'<span class="landing-domain-dot" style="background:{color}"></span>'
            f'<span>{label}</span><span class="landing-domain-pct">{pct}%</span></div>'
        )
        start_angle = end_angle

    return f"""
<div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap">
  <svg width="160" height="160" viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{title}">
    {''.join(paths)}
    <text x="{cx}" y="{cy - 4}" text-anchor="middle" fill="currentColor" font-size="11" font-weight="800">{center_label}</text>
    <text x="{cx}" y="{cy + 12}" text-anchor="middle" fill="#60738f" font-size="8">domains</text>
  </svg>
  <div class="landing-domain-list" style="flex:1;min-width:160px">{''.join(legend)}</div>
</div>
"""


def scoring_gauge_svg() -> str:
    """400–1600 score scale visualization."""
    return """
<svg class="landing-infographic" viewBox="0 0 720 120" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="SAT scoring scale">
  <defs>
    <linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#5ba0ff"/>
      <stop offset="50%" style="stop-color:#2d7ff9"/>
      <stop offset="100%" style="stop-color:#1262e0"/>
    </linearGradient>
  </defs>
  <text x="360" y="22" text-anchor="middle" fill="currentColor" font-size="13" font-weight="800">Score Scale (IRT → Equating → Scaled Score)</text>
  <rect x="60" y="45" width="600" height="24" rx="12" fill="url(#scoreGrad)"/>
  <text x="70" y="62" fill="#fff" font-size="11" font-weight="700">400</text>
  <text x="650" y="62" text-anchor="end" fill="#fff" font-size="11" font-weight="700">1600</text>
  <rect x="200" y="38" width="160" height="38" rx="8" fill="#fff" stroke="#5ba0ff" stroke-width="2"/>
  <text x="280" y="56" text-anchor="middle" fill="#1262e0" font-size="10" font-weight="700">R&amp;W</text>
  <text x="280" y="70" text-anchor="middle" fill="#60738f" font-size="10">200 – 800</text>
  <rect x="400" y="38" width="160" height="38" rx="8" fill="#fff" stroke="#34c38f" stroke-width="2"/>
  <text x="480" y="56" text-anchor="middle" fill="#0d5c41" font-size="10" font-weight="700">Math</text>
  <text x="480" y="70" text-anchor="middle" fill="#60738f" font-size="10">200 – 800</text>
  <text x="360" y="105" text-anchor="middle" fill="#60738f" font-size="10">Which questions you get right matters — not just how many</text>
</svg>
"""
