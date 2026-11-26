#!/usr/bin/env python3
"""
Fetches the user's GitHub contribution calendar and generates a modern,
dark-minimalist luminous SVG heatmap with a subtle animated glare/shimmer effect.
"""

import datetime
import os
import re
import urllib.request
from pathlib import Path

USERNAME = os.getenv("GITHUB_USERNAME", "nestiawanfyans")
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "assets" / "contrib-grid.svg"

# Luminous dark-mode palette (Level 0..4)
LEVEL_STYLES = {
    0: {"fill": "#151B23", "stroke": "#1E2633", "glow": None, "pulse": False},
    1: {"fill": "#0E7490", "stroke": "#155E75", "glow": None, "pulse": False},
    2: {"fill": "#06B6D4", "stroke": "#22D3EE", "glow": "softGlow", "pulse": False},
    3: {"fill": "#38BDF8", "stroke": "#7DD3FC", "glow": "neonGlow", "pulse": True},
    4: {"fill": "#CFFAFE", "stroke": "#FFFFFF", "glow": "radiantGlow", "pulse": True},
}


def fetch_contributions(username: str) -> dict[datetime.date, int]:
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "contrib-grid-generator"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    matches = re.findall(
        r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="(\d)"', html
    )
    if not matches:
        alt = re.findall(
            r'data-level="(\d)"[^>]*data-date="(\d{4}-\d{2}-\d{2})"', html
        )
        matches = [(d, lvl) for lvl, d in alt]

    data: dict[datetime.date, int] = {}
    for date_str, lvl in matches:
        try:
            d = datetime.date.fromisoformat(date_str)
            data[d] = int(lvl)
        except ValueError:
            continue
    return data


def build_svg(data: dict[datetime.date, int]) -> str:
    if not data:
        raise RuntimeError("No contribution data retrieved from GitHub.")

    sorted_dates = sorted(data.keys())
    first_date = sorted_dates[0]
    last_date = sorted_dates[-1]

    # Align start to Sunday (weekday(): Mon=0..Sun=6 -> Sunday offset = (wd + 1) % 7)
    start_sunday = first_date - datetime.timedelta(days=(first_date.weekday() + 1) % 7)
    total_days = (last_date - start_sunday).days + 1
    num_weeks = (total_days + 6) // 7

    # Layout constants
    width = 900
    height = 202
    cell = 11.8
    gap = 3.2
    step = cell + gap
    grid_width = num_weeks * step - gap
    grid_x = round((width - grid_width) / 2 + 12, 1)
    grid_y = 66

    # Build cells & month labels
    cell_elements: list[str] = []
    month_labels: list[str] = []
    seen_months: set[tuple[int, int]] = set()
    last_label_x = -999.0

    for w in range(num_weeks):
        col_x = round(grid_x + w * step, 1)
        # Check month label for the Sunday or first valid day in this column
        for d_off in range(7):
            cur = start_sunday + datetime.timedelta(days=w * 7 + d_off)
            if cur in data and cur.day <= 7:
                ym = (cur.year, cur.month)
                if ym not in seen_months and (col_x - last_label_x) >= 34:
                    seen_months.add(ym)
                    last_label_x = col_x
                    month_labels.append(
                        f'<text x="{col_x}" y="{grid_y - 10}" fill="#64748B" font-size="10.5" class="mono">{cur.strftime("%b")}</text>'
                    )
                break

        for row in range(7):
            cur = start_sunday + datetime.timedelta(days=w * 7 + row)
            if cur < first_date or cur > last_date:
                continue
            lvl = data.get(cur, 0)
            style = LEVEL_STYLES.get(lvl, LEVEL_STYLES[0])
            cy = round(grid_y + row * step, 1)

            attrs = [
                f'x="{col_x}"',
                f'y="{cy}"',
                f'width="{cell}"',
                f'height="{cell}"',
                'rx="3"',
                f'fill="{style["fill"]}"',
                f'stroke="{style["stroke"]}"',
                'stroke-width="0.6"',
            ]
            if style["glow"]:
                attrs.append(f'filter="url(#{style["glow"]})"')
            if style["pulse"]:
                delay = round(((w * 7 + row) % 9) * 0.35, 2)
                attrs.append(f'class="glow-cell" style="animation-delay: {delay}s"')

            cell_elements.append(f"    <rect {' '.join(attrs)} />")

    # Weekday labels (Mon=1, Wed=3, Fri=5)
    weekday_x = round(grid_x - 10, 1)
    weekday_labels = [
        f'  <text x="{weekday_x}" y="{round(grid_y + 1 * step + 9.5, 1)}" text-anchor="end" fill="#475569" font-size="10" class="mono">Mon</text>',
        f'  <text x="{weekday_x}" y="{round(grid_y + 3 * step + 9.5, 1)}" text-anchor="end" fill="#475569" font-size="10" class="mono">Wed</text>',
        f'  <text x="{weekday_x}" y="{round(grid_y + 5 * step + 9.5, 1)}" text-anchor="end" fill="#475569" font-size="10" class="mono">Fri</text>',
    ]

    # Legend swatches
    legend_x = width - 166
    legend_y = 24
    legend_swatches = []
    for idx in range(5):
        st = LEVEL_STYLES[idx]
        sx = legend_x + 36 + idx * 16
        glow_attr = f' filter="url(#{st["glow"]})"' if st["glow"] else ""
        legend_swatches.append(
            f'    <rect x="{sx}" y="{legend_y - 9}" width="11" height="11" rx="2.5" fill="{st["fill"]}" stroke="{st["stroke"]}" stroke-width="0.6"{glow_attr} />'
        )

    svg = f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <clipPath id="cardClip">
      <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="14" />
    </clipPath>

    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#111720" />
      <stop offset="100%" stop-color="#0D1117" />
    </linearGradient>

    <linearGradient id="topAccent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#0D1117" stop-opacity="0" />
      <stop offset="25%" stop-color="#06B6D4" stop-opacity="0.75" />
      <stop offset="50%" stop-color="#38BDF8" stop-opacity="0.95" />
      <stop offset="75%" stop-color="#A855F7" stop-opacity="0.75" />
      <stop offset="100%" stop-color="#0D1117" stop-opacity="0" />
    </linearGradient>

    <!-- Glare / Shimmer light beam ("efek silau") -->
    <linearGradient id="glareBeam" x1="0%" y1="0%" x2="100%" y2="25%">
      <stop offset="0%" stop-color="#38BDF8" stop-opacity="0" />
      <stop offset="32%" stop-color="#38BDF8" stop-opacity="0.06" />
      <stop offset="48%" stop-color="#E0F2FE" stop-opacity="0.18" />
      <stop offset="52%" stop-color="#FFFFFF" stop-opacity="0.22" />
      <stop offset="68%" stop-color="#A855F7" stop-opacity="0.06" />
      <stop offset="100%" stop-color="#A855F7" stop-opacity="0" />
    </linearGradient>

    <!-- Soft luminous glow filters -->
    <filter id="softGlow" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="1.6" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>

    <filter id="neonGlow" x="-70%" y="-70%" width="240%" height="240%">
      <feGaussianBlur stdDeviation="2.8" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>

    <filter id="radiantGlow" x="-100%" y="-100%" width="300%" height="300%">
      <feGaussianBlur stdDeviation="4.2" result="blur1" />
      <feGaussianBlur stdDeviation="1.8" result="blur2" />
      <feMerge>
        <feMergeNode in="blur1" />
        <feMergeNode in="blur2" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <style>
    .title {{
      font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Inter, Roboto, sans-serif;
      font-weight: 600;
      letter-spacing: -0.015em;
    }}
    .mono {{
      font-family: 'SF Mono', 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-weight: 500;
    }}
    @keyframes glareSweep {{
      0% {{ transform: translateX(-360px); opacity: 0; }}
      10% {{ opacity: 1; }}
      55% {{ transform: translateX(1080px); opacity: 1; }}
      65%, 100% {{ transform: translateX(1080px); opacity: 0; }}
    }}
    @keyframes cellPulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.72; }}
    }}
    .glare {{
      animation: glareSweep 5.6s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }}
    .glow-cell {{
      animation: cellPulse 3.2s ease-in-out infinite;
    }}
  </style>

  <!-- Card frame -->
  <rect x="0.75" y="0.75" width="{width - 1.5}" height="{height - 1.5}" rx="14" fill="url(#bgGrad)" stroke="#21262D" stroke-width="1.2" />
  <rect x="140" y="0.75" width="620" height="1.5" fill="url(#topAccent)" />

  <!-- Header -->
  <text x="26" y="30" fill="#F8FAFC" font-size="13.5" class="title">Contribution Calendar</text>
  <rect x="176" y="16" width="96" height="18" rx="9" fill="#161F2C" stroke="#38BDF8" stroke-opacity="0.3" stroke-width="0.9" />
  <text x="224" y="28.5" text-anchor="middle" fill="#7DD3FC" font-size="9.5" class="mono">LUMINOUS GRID</text>

  <!-- Legend -->
  <text x="{legend_x}" y="{legend_y}" fill="#64748B" font-size="10.5" class="mono">Less</text>
{chr(10).join(legend_swatches)}
  <text x="{legend_x + 120}" y="{legend_y}" fill="#64748B" font-size="10.5" class="mono">More</text>

  <!-- Month & Weekday Labels -->
  {chr(10).join(month_labels)}
{chr(10).join(weekday_labels)}

  <!-- Contribution Cells -->
  <g>
{chr(10).join(cell_elements)}
  </g>

  <!-- Animated Diagonal Glare / Shimmer Effect -->
  <g clip-path="url(#cardClip)" pointer-events="none">
    <g class="glare">
      <polygon points="0,0 180,0 110,{height} -70,{height}" fill="url(#glareBeam)" />
    </g>
  </g>
</svg>
"""
    return svg


def main() -> None:
    data = fetch_contributions(USERNAME)
    svg = build_svg(data)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(svg, encoding="utf-8")
    print(f"Generated {OUTPUT_PATH} ({len(data)} days)")


if __name__ == "__main__":
    main()
