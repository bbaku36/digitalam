"""Image card generation for selected autopost categories."""

from __future__ import annotations

import html
import math
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATED_DIR = ROOT / ".state" / "generated"

SECTION_HEADINGS = {
    "🌿 Өдрийн ерөнхий төлөв",
    "✂️ Үс засуулах тохиромж",
    "🛣️ Аян замд гарах",
    "📿 Үйл хийхэд сайн",
    "⚠️ Цээрлэх зүйл",
}

YEAR_EMOJIS = {
    "хулгана": "🐭",
    "үхэр": "🐮",
    "бар": "🐯",
    "туулай": "🐰",
    "луу": "🐲",
    "могой": "🐍",
    "морь": "🐴",
    "хонь": "🐑",
    "бич": "🐵",
    "тахиа": "🐓",
    "нохой": "🐶",
    "гахай": "🐷",
}


def _extract_source_value(source_context: str | None, prefix: str) -> str:
    if not source_context:
        return ""
    for line in source_context.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def _normalize_year_value(value: str) -> list[str]:
    cleaned = value.strip().rstrip(".")
    cleaned = re.sub(r"\s*жилтнээ$", "", cleaned).strip()
    if not cleaned:
        return []
    return [item.strip().capitalize() for item in cleaned.split(",") if item.strip()]


def _emoji_for_years(years: list[str]) -> str:
    emojis = [YEAR_EMOJIS.get(item.lower(), "") for item in years]
    return " ".join(item for item in emojis if item)


def _year_seal_html(years: list[str]) -> str:
    if not years:
        return '<span class="seal-empty">—</span>'
    items = []
    for name in years:
        emoji = YEAR_EMOJIS.get(name.lower(), "✦")
        items.append(
            '<span class="seal">'
            f'<span class="seal-ring"><span class="seal-emoji">{_escape(emoji)}</span></span>'
            f'<span class="seal-name">{_escape(name)}</span>'
            "</span>"
        )
    return "\n".join(items)


ICONS = {
    "leaf": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 '
        '17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6"/></svg>'
    ),
    "scissors": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
        'stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="3"/>'
        '<circle cx="6" cy="18" r="3"/><line x1="20" y1="4" x2="8.12" y2="15.88"/>'
        '<line x1="14.47" y1="14.48" x2="20" y2="20"/><line x1="8.12" y1="8.12" x2="12" y2="12"/></svg>'
    ),
    "compass": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
        'stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/>'
        '<polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>'
    ),
    "lotus": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="M12 3c1.8 2 2.6 3.9 2.6 5.6 '
        '0 1.7-1.1 3-2.6 3s-2.6-1.3-2.6-3C9.4 6.9 10.2 5 12 3z"/><path d="M12 21v-6"/>'
        '<path d="M12 16c-3.3 0-6-2.2-6-5 1.9-.2 3.6.4 5 1.6"/>'
        '<path d="M12 16c3.3 0 6-2.2 6-5-1.9-.2-3.6.4-5 1.6"/></svg>'
    ),
    "warning": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 '
        '0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/>'
        '<line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
    ),
    "spark": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v4M12 17v4M3 12h4M17 12h4"/>'
        '<path d="M12 8a4 4 0 0 0 4 4 4 4 0 0 0-4 4 4 4 0 0 0-4-4 4 4 0 0 0 4-4z"/></svg>'
    ),
    "sun": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
        'stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4.2"/>'
        '<path d="M12 2.5v2.2M12 19.3v2.2M4.2 12H2M22 12h-2.2M5.5 5.5 4 4M20 20l-1.5-1.5"/>'
        '<path d="M5.5 18.5 4 20M20 4l-1.5 1.5"/></svg>'
    ),
}


def _icon(name: str) -> str:
    return ICONS.get(name, "")


def _split_items(value: str, *, limit: int = 3) -> list[str]:
    cleaned = value.strip().strip(".")
    if not cleaned:
        return []
    parts = [item.strip(" ,.") for item in re.split(r",|\s+болон\s+", cleaned) if item.strip(" ,.")]
    unique: list[str] = []
    for part in parts:
        if part not in unique:
            unique.append(part)
        if len(unique) >= limit:
            break
    return unique


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _parse_horoscope_post(post_text: str) -> dict[str, str]:
    lines = [line.rstrip() for line in post_text.splitlines()]
    non_empty = [line.strip() for line in lines if line.strip()]
    if len(non_empty) < 3:
        raise ValueError("horoscope_post_too_short_for_image")

    data = {
        "date_line": non_empty[0],
        "title_line": non_empty[1],
        "biligiin_line": next((line for line in non_empty if line.startswith("Билгийн тооллын")), ""),
        "disclaimer": next(
            (
                line
                for line in reversed(non_empty)
                if not line.startswith("#") and line not in SECTION_HEADINGS and not line.startswith(("✅", "⚠️"))
            ),
            "",
        ),
    }

    sections: dict[str, list[str]] = {}
    current_heading = ""
    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped in SECTION_HEADINGS:
            current_heading = stripped
            sections[current_heading] = []
            continue
        if stripped.startswith("#"):
            continue
        if current_heading:
            sections.setdefault(current_heading, []).append(stripped)

    general_lines = sections.get("🌿 Өдрийн ерөнхий төлөв", [])
    data["general_text"] = next((line for line in general_lines if not line.startswith("Суудал:")), "")
    data["suudal"] = next((line.replace("Суудал:", "").strip() for line in general_lines if line.startswith("Суудал:")), "")
    data["hair_text"] = " ".join(sections.get("✂️ Үс засуулах тохиромж", []))
    data["travel_text"] = " ".join(sections.get("🛣️ Аян замд гарах", []))

    action_lines = sections.get("📿 Үйл хийхэд сайн", [])
    data["action_text"] = next((line for line in action_lines if not line.startswith(("✅", "⚠️"))), "")
    data["good_years_line"] = next((line.replace("✅ Сайн жилтэн:", "").strip() for line in action_lines if line.startswith("✅ Сайн жилтэн:")), "")
    data["caution_years_line"] = next((line.replace("⚠️ Болгоомжлох жилтэн:", "").strip() for line in action_lines if line.startswith("⚠️ Болгоомжлох жилтэн:")), "")

    caution_lines = [
        line for line in sections.get("⚠️ Цээрлэх зүйл", []) if line != data["disclaimer"]
    ]
    data["caution_text"] = " ".join(caution_lines)
    return data


def _compact_date_for_card(date_line: str) -> str:
    match = re.match(r"^(\d{4}) оны (\d{1,2}) дугаар сарын (\d{1,2})\.$", date_line.strip())
    if not match:
        return date_line.strip()
    year, month, day = match.groups()
    return f"{year}.{int(month):02d}.{int(day):02d}"


def _compact_source_date(source_date: str) -> str:
    value = source_date.split("/", 1)[0].strip()
    match = re.match(r"^(\d{4})\.(\d{2})\.(\d{2})$", value)
    if not match:
        return value
    return value


def _sentence_case(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    return cleaned[0].upper() + cleaned[1:]


def _extract_general_guidance(source_context: str | None, fallback: str) -> str:
    caution = _extract_source_value(source_context, "Caution: ")
    if caution:
        if " тул " in caution:
            return _sentence_case(caution.split(" тул ", 1)[1].strip().rstrip(".") + ".")
        return _sentence_case(caution.rstrip(".") + ".")
    return fallback


def _hair_status(text: str) -> str:
    lower = text.lower()
    if any(marker in lower for marker in ("тохиромжгүй", "цээр", "эрлэг", "хэрүүл", "болзошгүй")):
        return "Тохиромжгүй"
    if any(marker in lower for marker in ("сайн", "төгөлдөр", "эд мал", "баялаг", "өлзий")):
        return "Тохиромжтой"
    return "Тохиромжтой"


def _travel_status(text: str) -> str:
    lower = text.lower()
    if any(marker in lower for marker in ("өлзийтэй", "сайн", "бүтэмжтэй", "дэмтэй", "зохистой")):
        return "Сайн"
    return "Анхаарах"


def build_horoscope_image_caption(post_text: str) -> str:
    parsed = _parse_horoscope_post(post_text)
    hashtags = [line.strip() for line in post_text.splitlines() if line.strip().startswith("#")]
    caption_lines = [
        parsed.get("date_line", "").strip(),
        "Зурган дээр: өдрийн ерөнхий төлөв, үс засуулах, аян замд гарах, үйл хийхэд сайн, сайн жилтэн, болгоомжлох жилтэн, цээрлэх зүйлс багтсан.",
    ]
    if hashtags:
        caption_lines.append(hashtags[-1])
    caption_lines.append("Өдөр бүр шинэ зурхайн мэдээллийг авах бол манай page-ийг дагаарай.")
    return "\n".join(line for line in caption_lines if line).strip()


ROYAL_GLYPHS = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]

STAR_POINTS = [
    (8, 12), (18, 30), (27, 8), (33, 52), (41, 20), (47, 72), (55, 15), (61, 44),
    (66, 80), (72, 25), (78, 58), (83, 12), (88, 40), (93, 66), (13, 60), (23, 84),
    (37, 88), (52, 40), (68, 5), (85, 84), (6, 44), (30, 66), (58, 60), (76, 90),
    (95, 20), (15, 44), (44, 60), (70, 68), (90, 52), (3, 70),
]


def _royal_wheel_svg() -> str:
    cx = cy = 500
    parts: list[str] = []
    for radius, width, opacity in [(475, 0.7, 0.9), (440, 0.5, 0.7), (315, 0.5, 0.6), (190, 0.5, 0.5)]:
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" stroke="#D4A44C" stroke-width="{width}" fill="none" opacity="{opacity}"/>'
        )
    for r1, r2, step, width in [(440, 475, 6, 0.5), (315, 340, 15, 0.5)]:
        for deg in range(0, 360, step):
            a = math.radians(deg)
            parts.append(
                f'<line x1="{cx + r1 * math.cos(a):.1f}" y1="{cy + r1 * math.sin(a):.1f}" '
                f'x2="{cx + r2 * math.cos(a):.1f}" y2="{cy + r2 * math.sin(a):.1f}" '
                f'stroke="#D4A44C" stroke-width="{width}" opacity="0.65"/>'
            )
    for deg in range(0, 360, 30):
        a = math.radians(deg - 90)
        parts.append(
            f'<line x1="{cx + 315 * math.cos(a):.1f}" y1="{cy + 315 * math.sin(a):.1f}" '
            f'x2="{cx + 440 * math.cos(a):.1f}" y2="{cy + 440 * math.sin(a):.1f}" '
            'stroke="#D4A44C" stroke-width="0.9" opacity="0.8"/>'
        )
    for idx, glyph in enumerate(ROYAL_GLYPHS):
        angle = math.radians(idx * 30 - 90)
        gx = cx + 383 * math.cos(angle)
        gy = cy + 383 * math.sin(angle)
        parts.append(
            f'<text x="{gx:.0f}" y="{gy:.0f}" fill="#E8C876" font-size="38" font-family="Montserrat, sans-serif" '
            f'text-anchor="middle" dominant-baseline="central" opacity="0.95">{glyph}\ufe0e</text>'
        )
    return '<svg viewBox="0 0 1000 1000" xmlns="http://www.w3.org/2000/svg">' + "".join(parts) + "</svg>"


def _royal_cluster(points: list[tuple[int, int]]) -> str:
    path = "M" + " L".join(f"{x} {y}" for x, y in points)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="3.4" fill="#F0D9A0"/>' for x, y in points)
    return (
        '<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">'
        f'<path d="{path}" stroke="#D4A44C" stroke-width="1.1" fill="none" opacity="0.7"/>{dots}</svg>'
    )


def _royal_clusters() -> tuple[str, str, str]:
    c1 = _royal_cluster([(20, 30), (60, 55), (95, 40), (130, 70), (110, 110), (70, 95), (40, 120), (150, 45)])
    c2 = _royal_cluster([(30, 150), (70, 120), (110, 140), (150, 105), (170, 150), (120, 175)])
    c3 = _royal_cluster([(40, 40), (85, 30), (120, 60), (90, 95)])
    return c1, c2, c3


def _royal_background_html() -> str:
    stars = []
    for idx, (x, y) in enumerate(STAR_POINTS):
        size = "3px" if idx % 3 == 0 else "2px"
        opacity = 0.3 + (idx % 5) * 0.12
        stars.append(
            f'<span class="star" style="left:{x}%;top:{y}%;width:{size};height:{size};opacity:{opacity:.2f}"></span>'
        )
    c1, c2, c3 = _royal_clusters()
    return (
        f'<div class="wheel">{_royal_wheel_svg()}</div>'
        f'<div class="const a">{c1}</div>'
        f'<div class="const b">{c2}</div>'
        f'<div class="const c">{c3}</div>'
        f'{"".join(stars)}'
        '<div class="moon"></div>'
        '<div class="veil"></div>'
    )


def _royal_seal_html(years: list[str]) -> str:
    if not years:
        return '<span class="seal-empty">—</span>'
    out = []
    for name in years:
        emoji = YEAR_EMOJIS.get(name.lower(), "✦")
        out.append(
            '<span class="seal">'
            f'<span class="seal-em">{_escape(emoji)}</span>'
            f'<span class="seal-nm">{_escape(name)}</span>'
            "</span>"
        )
    return "".join(out)


_ROYAL_BASE_CSS = """
:root {
  --gold: #d4a44c;
  --gold-2: #c89a45;
  --gold-lt: #f4d98a;
  --gold-tx: #e8c876;
  --cream: #f2e3c2;
  --cream-2: #ebd9b4;
  --muted: #d9b77a;
  --ok: #9bd98a;
  --warn: #f0a88e;
}
* { box-sizing: border-box; }
html, body {
  width: 1080px; height: 1350px; margin: 0; padding: 0; overflow: hidden;
  font-family: 'Montserrat', sans-serif; color: var(--cream); -webkit-font-smoothing: antialiased;
}
.bg {
  position: relative; width: 1080px; height: 1350px; padding: 44px; overflow: hidden;
  background:
    radial-gradient(85% 55% at 50% 0%, rgba(226,178,88,.20), transparent 62%),
    radial-gradient(circle at 50% 46%, #5e1c20 0%, #440f12 52%, #280809 100%);
}
.wheel { position:absolute; top:48%; left:50%; width:1180px; height:1180px; transform:translate(-50%,-50%); opacity:.34; }
.const { position:absolute; opacity:.5; }
.const.a { top:70px; left:40px; width:200px; height:200px; }
.const.b { bottom:70px; right:40px; width:190px; height:190px; }
.const.c { top:120px; right:120px; width:150px; height:150px; opacity:.38; }
.star { position:absolute; border-radius:50%; background:#f0d9a0; box-shadow:0 0 5px rgba(240,217,160,.9); }
.moon {
  position:absolute; top:96px; left:96px; width:86px; height:86px; border-radius:50%;
  background:radial-gradient(circle at 36% 34%, #fbebc4, #e3c17a 68%, #c49b4e);
  box-shadow:0 0 34px rgba(227,193,122,.4), inset -11px -9px 0 -3px rgba(40,12,14,.9);
}
.veil { position:absolute; inset:0; background:radial-gradient(58% 46% at 50% 50%, rgba(38,8,9,.64), rgba(38,8,9,.2) 58%, transparent 76%); }
.frame {
  position:relative; z-index:3; height:100%; border:2px solid var(--gold-2); border-radius:4px; padding:44px 50px 36px;
  display:flex; flex-direction:column;
  box-shadow: inset 0 0 0 6px rgba(68,15,18,1), inset 0 0 0 7px rgba(200,154,69,.55);
}
.corner { position:absolute; width:44px; height:44px; border:2px solid #d4a44c; }
.corner.tl { top:14px; left:14px; border-right:none; border-bottom:none; }
.corner.tr { top:14px; right:14px; border-left:none; border-bottom:none; }
.corner.bl { bottom:14px; left:14px; border-right:none; border-top:none; }
.corner.br { bottom:14px; right:14px; border-left:none; border-top:none; }

.eyebrow { text-align:center; font-size:13px; letter-spacing:.5em; text-transform:uppercase; color:var(--muted); }
.date { text-align:center; margin-top:14px; font-size:30px; letter-spacing:.3em; color:var(--cream); font-weight:600; }
.title {
  text-align:center; margin-top:6px; font-family:'Playfair Display',serif; font-weight:700; font-size:92px; line-height:1;
  color:var(--gold-lt); text-shadow:0 2px 0 rgba(0,0,0,.28), 0 0 36px rgba(212,164,76,.4);
}
.bil, .subtitle { text-align:center; margin-top:14px; font-size:15px; letter-spacing:.3em; text-transform:uppercase; color:var(--muted); }
.orn { display:flex; align-items:center; justify-content:center; gap:12px; margin:22px 0 4px; color:var(--gold); }
.orn:before, .orn:after { content:""; height:1px; width:140px; background:linear-gradient(90deg,transparent,#d4a44c); }
.orn:after { background:linear-gradient(90deg,#d4a44c,transparent); }
.orn svg { width:26px; height:26px; }

.ov { text-align:center; margin-top:12px; }
.ov h2 { font-family:'Playfair Display',serif; font-weight:600; font-size:19px; letter-spacing:.3em; text-transform:uppercase; color:#e6c176; }
.ov p { margin:12px auto 0; max-width:92%; font-size:29px; line-height:1.5; color:#efdfc0; }
.chip {
  display:inline-block; margin-top:14px; padding:6px 22px; border:1px solid var(--gold-2); border-radius:999px;
  font-size:15px; letter-spacing:.2em; text-transform:uppercase; color:var(--gold-lt); background:rgba(40,8,9,.5);
}

.seals { margin-top:24px; display:grid; grid-template-columns:1fr 1px 1fr; gap:24px; align-items:center; }
.sdiv { align-self:stretch; width:1px; background:linear-gradient(180deg,transparent,rgba(212,164,76,.5),transparent); }
.scol { text-align:center; }
.scol h3 { font-size:15px; letter-spacing:.26em; text-transform:uppercase; color:var(--muted); margin-bottom:14px; }
.srow { display:flex; justify-content:center; gap:20px; flex-wrap:wrap; }
.seal { display:flex; flex-direction:column; align-items:center; gap:8px; }
.seal-em {
  width:72px; height:72px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:38px;
  background:radial-gradient(circle at 50% 32%,#7a2a2e,#4a1518); border:1.5px solid #d4a44c;
  box-shadow:0 0 20px rgba(212,164,76,.25), inset 0 0 0 4px rgba(74,21,24,.9), inset 0 0 0 5px rgba(212,164,76,.4);
}
.seal-nm { font-family:'Playfair Display',serif; font-size:21px; color:var(--cream); }
.seal-empty { color:var(--muted); font-size:22px; }

.panels { margin-top:24px; display:grid; grid-template-columns:1fr 1fr; gap:18px; }
.panel { border:1px solid rgba(212,164,76,.55); border-radius:8px; padding:20px 22px; background:linear-gradient(180deg,rgba(122,42,46,.55),rgba(50,12,14,.6)); }
.ptop { display:flex; align-items:center; gap:12px; }
.ico { width:28px; height:28px; color:var(--gold-lt); display:inline-flex; }
.ico svg { width:100%; height:100%; }
.pname { font-family:'Playfair Display',serif; font-size:25px; color:var(--gold-lt); }
.st { margin-left:auto; font-size:12px; letter-spacing:.1em; text-transform:uppercase; padding:4px 12px; border-radius:999px; border:1px solid currentColor; white-space:nowrap; }
.st.ok { color:var(--ok); } .st.warn { color:var(--warn); }
.ptext { margin:12px 0 0; font-size:22px; line-height:1.5; color:var(--cream-2); }

.lists { margin-top:24px; display:grid; grid-template-columns:1fr 1fr; gap:28px; }
.lhead { display:flex; align-items:center; gap:10px; padding-bottom:10px; border-bottom:1px solid rgba(212,164,76,.4); font-size:17px; letter-spacing:.16em; text-transform:uppercase; }
.lhead svg { width:18px; height:18px; }
.lhead.g { color:var(--ok); } .lhead.b { color:var(--warn); }
ul { list-style:none; padding:0; margin:0; }
li { position:relative; padding-left:24px; font-size:21px; line-height:1.4; color:var(--cream-2); margin-top:12px; }
li:before { content:""; position:absolute; left:2px; top:8px; width:6px; height:6px; transform:rotate(45deg); }
li.g:before { background:var(--ok); } li.b:before { background:var(--warn); }

.foot { margin-top:auto; padding-top:20px; text-align:center; color:var(--muted); font-size:13px; letter-spacing:.24em; text-transform:uppercase; border-top:1px solid rgba(212,164,76,.3); }
"""

_ZODIAC_CSS = """
.lead {
  margin:16px auto 0; max-width:94%; text-align:center; font-size:20px; line-height:1.5; color:#e4d3ab;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
}
.signs { margin-top:16px; flex:1; display:grid; grid-template-columns:1fr 1fr; align-content:space-between; column-gap:30px; row-gap:0; }
.sign { display:flex; gap:14px; padding:15px 0; border-bottom:1px solid rgba(212,164,76,.28); }
.sign-glyph {
  flex:none; width:58px; height:58px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-size:30px; color:var(--gold-lt); background:radial-gradient(circle at 50% 32%,#7a2a2e,#4a1518);
  border:1.5px solid #d4a44c; box-shadow:inset 0 0 0 3px rgba(74,21,24,.9), inset 0 0 0 4px rgba(212,164,76,.4);
}
.sign-body { flex:1; min-width:0; }
.sign-head { display:flex; align-items:baseline; justify-content:space-between; gap:10px; }
.sign-name { font-family:'Playfair Display',serif; font-size:23px; font-weight:600; color:var(--cream); }
.sign-range { font-size:13px; font-weight:600; letter-spacing:.04em; color:var(--muted); white-space:nowrap; }
.sign-text {
  margin:6px 0 0; font-size:17px; line-height:1.4; color:#e4d3ab;
  display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;
}
"""

_WEEKLY_CSS = """
.week { margin-top:20px; border:1px solid rgba(212,164,76,.45); border-radius:10px; overflow:hidden; background:linear-gradient(180deg, rgba(122,42,46,.42), rgba(50,12,14,.55)); }
.week-head, .week-row { display:grid; grid-template-columns:190px 1fr 1fr 1fr; align-items:center; }
.week-head { padding:14px 22px; background:rgba(120,40,44,.5); border-bottom:1px solid rgba(212,164,76,.45); }
.week-head .col { display:flex; align-items:center; justify-content:center; gap:8px; font-size:14px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); }
.week-head .col.day { justify-content:flex-start; }
.week-head .col svg { width:16px; height:16px; }
.week-row { padding:13px 22px; min-height:82px; border-bottom:1px solid rgba(212,164,76,.22); }
.week-row:last-child { border-bottom:none; }
.week-row.alt { background:rgba(255,255,255,.03); }
.cell-day { display:flex; flex-direction:column; gap:2px; }
.weekday { font-family:'Playfair Display',serif; font-size:26px; font-weight:600; line-height:1; color:var(--cream); }
.weekdate { font-size:14px; font-weight:600; letter-spacing:.06em; color:var(--muted); }
.cell-stat { display:flex; flex-direction:column; gap:4px; padding:0 14px; color:var(--muted); }
.stat-label { display:flex; align-items:center; gap:8px; font-size:18px; font-weight:700; line-height:1.1; }
.stat-label:before { content:""; width:8px; height:8px; border-radius:50%; background:currentColor; flex:none; }
.stat-brief { font-size:14px; line-height:1.3; color:#cbb98e; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; word-break:break-word; }
.status-good { color:var(--ok); } .status-warn { color:#f0c56a; } .status-bad { color:var(--warn); } .status-travel { color:var(--cream); }
.summary { margin-top:20px; display:grid; grid-template-columns:repeat(3,1fr); gap:16px; align-items:stretch; }
.summary-card { padding:16px; border:1px solid rgba(212,164,76,.4); border-radius:10px; text-align:center; background:linear-gradient(180deg, rgba(122,42,46,.42), rgba(50,12,14,.55)); display:flex; flex-direction:column; justify-content:flex-start; }
.summary-icon { width:28px; height:28px; margin:0 auto 8px; color:var(--gold-lt); }
.summary-icon svg { width:100%; height:100%; }
.summary-label { font-size:13px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); }
.summary-day { margin-top:8px; font-family:'Playfair Display',serif; font-size:22px; font-weight:600; color:var(--gold-lt); line-height:1.25; min-height:2.5em; }
.summary-date { margin-top:4px; font-size:14px; color:var(--muted); }
"""


def _build_horoscope_html(post_text: str, source_context: str | None) -> str:
    parsed = _parse_horoscope_post(post_text)
    source_date = _extract_source_value(source_context, "Source date: ")
    compact_date = _compact_source_date(source_date) if source_date else _compact_date_for_card(parsed.get("date_line", ""))

    biligiin_line = _extract_source_value(source_context, "Bilgiin line: ") or parsed.get("biligiin_line", "")
    general_text = parsed.get("general_text", "").strip() or _extract_general_guidance(source_context, parsed.get("general_text", ""))
    suudal = _extract_source_value(source_context, "Suudal: ") or parsed.get("suudal", "")

    source_hair_omen = _extract_source_value(source_context, "Haircut omen: ")
    source_hair_line = _extract_source_value(source_context, "Haircut line: ")
    hair_text = parsed.get("hair_text", "")
    if source_hair_omen:
        hair_text = f"Үс засуулвал {source_hair_omen.rstrip('.')}."
    elif source_hair_line:
        hair_text = f"Үс шинээр үргээлгэх буюу засуулахад {source_hair_line.rstrip('.')}."
    hair_status = _hair_status(source_hair_line or source_hair_omen or hair_text)
    hair_state = "ok" if hair_status == "Тохиромжтой" else "warn"

    source_travel = _extract_source_value(source_context, "Travel direction: ")
    travel_text = parsed.get("travel_text", "")
    if source_travel:
        travel_text = f"Хол газар яваар одогсод {source_travel.rstrip('.')}."
    travel_status = _travel_status(source_travel or travel_text)
    travel_state = "ok" if travel_status == "Сайн" else "warn"

    fallback_action = parsed.get("action_text", "")
    fallback_action = re.sub(r"^Эл өдөр\s+", "", fallback_action).strip()
    fallback_action = re.sub(r"\s+зэрэг үйлд\s+сайн\.?$", "", fallback_action).strip()
    fallback_action = re.sub(r"\s+сайн\.?$", "", fallback_action).strip()
    good_activities = _split_items(fallback_action, limit=4)
    if not good_activities:
        good_activities = _split_items(_extract_source_value(source_context, "Good activities: "), limit=4)

    caution_items = _split_items(_extract_source_value(source_context, "Bad activities: "), limit=3)
    if not caution_items:
        fallback_caution = parsed.get("caution_text", "")
        fallback_caution = re.sub(r"\s+үйл цээрлэвэл зохистой\.?$", "", fallback_caution).strip()
        caution_items = _split_items(fallback_caution, limit=3)

    favorable_years = _normalize_year_value(parsed.get("good_years_line", "") or _extract_source_value(source_context, "Favorable years: "))
    caution_years = _normalize_year_value(parsed.get("caution_years_line", "") or _extract_source_value(source_context, "Caution years: "))

    favorable_seals_html = _royal_seal_html(favorable_years)
    caution_seals_html = _royal_seal_html(caution_years)

    good_items = good_activities or [parsed.get("action_text", "")]
    caution_items_final = caution_items or [parsed.get("caution_text", "")]
    good_list_html = "\n".join(f"<li class=\"g\">{_escape(_sentence_case(item))}</li>" for item in good_items if item)
    caution_list_html = "\n".join(f"<li class=\"b\">{_escape(_sentence_case(item))}</li>" for item in caution_items_final if item)

    disclaimer = parsed.get("disclaimer", "").strip() or "Уламжлалт билгийн тооллын ерөнхий мэдээлэл."

    return f"""<!doctype html>
<html lang="mn">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Өдрийн Зурхай</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,500&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <style>{_ROYAL_BASE_CSS}</style>
  </head>
  <body>
    <div class="bg">
      {_royal_background_html()}
      <div class="frame">
        <span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span>
        <div class="eyebrow">Билгийн тоолол · Уламжлалт зурхай</div>
        <div class="date">{_escape(compact_date)}</div>
        <h1 class="title">Өдрийн Зурхай</h1>
        <div class="bil">{_escape(biligiin_line)}</div>
        <div class="orn">{_icon("sun")}</div>

        <div class="ov">
          <h2>Өдрийн ерөнхий төлөв</h2>
          <p>{_escape(general_text)}</p>
          <div class="chip">Суудал · {_escape(suudal)}</div>
        </div>

        <div class="seals">
          <div class="scol"><h3>Сайн жилтэн</h3><div class="srow">{favorable_seals_html}</div></div>
          <div class="sdiv"></div>
          <div class="scol"><h3>Болгоомжлох</h3><div class="srow">{caution_seals_html}</div></div>
        </div>

        <div class="panels">
          <div class="panel">
            <div class="ptop"><span class="ico">{_icon("scissors")}</span><span class="pname">Үс засуулах</span><span class="st {hair_state}">{_escape(hair_status)}</span></div>
            <p class="ptext">{_escape(hair_text)}</p>
          </div>
          <div class="panel">
            <div class="ptop"><span class="ico">{_icon("compass")}</span><span class="pname">Аян замд гарах</span><span class="st {travel_state}">{_escape(travel_status)}</span></div>
            <p class="ptext">{_escape(travel_text)}</p>
          </div>
        </div>

        <div class="lists">
          <div><div class="lhead g">{_icon("lotus")}<span>Үйл хийхэд сайн</span></div><ul>{good_list_html}</ul></div>
          <div><div class="lhead b">{_icon("warning")}<span>Цээрлэх зүйлс</span></div><ul>{caution_list_html}</ul></div>
        </div>

        <div class="foot">{_escape(disclaimer)}</div>
      </div>
    </div>
  </body>
</html>"""


def _render_html_to_png(html_content: str, slug: str) -> Path:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node_not_found_for_image_card")

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    html_path = GENERATED_DIR / f"{slug}.html"
    png_path = GENERATED_DIR / f"{slug}.png"

    html_path.write_text(html_content, encoding="utf-8")

    completed = subprocess.run(
        [
            "npx",
            "playwright",
            "screenshot",
            "--viewport-size=1080,1350",
            "--wait-for-timeout=2500",
            f"file://{html_path}",
            str(png_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if completed.returncode != 0:
        reason = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(reason or "playwright_screenshot_failed")

    if not png_path.exists():
        raise RuntimeError("card_png_missing")
    return png_path


def generate_horoscope_card_image(
    *,
    post_text: str,
    source_context: str | None,
    slug: str,
) -> Path:
    return _render_html_to_png(_build_horoscope_html(post_text, source_context), slug)


def generate_weekly_horoscope_card_image(
    *,
    post_text: str,
    source_context: str | None,
    slug: str,
) -> Path:
    return _render_html_to_png(_build_weekly_horoscope_html(post_text, source_context), slug)


WEEKDAY_HEADER_RE = re.compile(r"^\[(.+?)\s+(\d{4}-\d{2}-\d{2})\]$")


def _parse_weekly_source_context(source_context: str | None) -> list[dict[str, str]]:
    if not source_context:
        return []
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    field_prefixes = (
        ("Bilgiin line: ", "bilgiin"),
        ("Haircut omen: ", "haircut_omen"),
        ("Haircut suitability: ", "haircut_suitability"),
        ("Travel guidance: ", "travel"),
        ("Good activities: ", "good_activities"),
        ("Bad activities: ", "bad_activities"),
        ("Caution: ", "caution"),
        ("Summary paragraph: ", "summary"),
    )
    for raw in source_context.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        match = WEEKDAY_HEADER_RE.match(stripped)
        if match:
            if current:
                entries.append(current)
            current = {
                "weekday": match.group(1),
                "date": match.group(2),
                "bilgiin": "",
                "haircut_omen": "",
                "haircut_suitability": "",
                "travel": "",
                "good_activities": "",
                "bad_activities": "",
                "caution": "",
                "summary": "",
            }
            continue
        if current is None:
            continue
        for prefix, key in field_prefixes:
            if stripped.startswith(prefix):
                current[key] = stripped[len(prefix) :].strip()
                break
    if current:
        entries.append(current)
    return entries


def _weekly_hair_status(suitability: str) -> tuple[str, str]:
    lower = suitability.lower()
    if "тохиромжгүй" in lower:
        return "bad", "Тохиромжгүй"
    return "good", "Тохиромжтой"


def _weekly_action_status(caution: str) -> tuple[str, str]:
    lower = caution.lower()
    if "сөрөг муу нөлөө" in lower or "хянамгай" in lower:
        return "warn", "Хянамгай"
    return "good", "Сайн"


def _direction_short(travel: str) -> str:
    cleaned = travel.strip().lower()
    if not cleaned:
        return "—"
    base = re.split(r"\s+мөр", cleaned, maxsplit=1)[0].strip()
    base = re.sub(r"\s*зүгт?$", "", base).strip()
    return base.capitalize() if base else "—"


def _short_omen(text: str, *, max_chars: int = 26) -> str:
    cleaned = text.strip().rstrip(".")
    if not cleaned:
        return ""
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"


def _short_date_label(date_str: str) -> str:
    parts = date_str.split("-")
    if len(parts) == 3:
        return f"{int(parts[1]):02d}.{int(parts[2]):02d}"
    return date_str


def _pick_highlight_days(entries: list[dict[str, str]], picker) -> list[tuple[str, str]]:
    matches = [
        (entry["weekday"], _short_date_label(entry["date"]))
        for entry in entries
        if picker(entry)
    ]
    return matches or [("—", "")]


def _summary_card_html(icon_svg: str, label: str, days: list[tuple[str, str]]) -> str:
    if len(days) >= 7:
        days_main = "Бүх өдөр"
        dates_line = ""
    else:
        days_main = " · ".join(name for name, _ in days)
        dates_line = " · ".join(date for _, date in days if date)
    dates_html = (
        f'<div class="summary-date">{_escape(dates_line)}</div>' if dates_line else ""
    )
    return (
        '<div class="summary-card">'
        f'<div class="summary-icon">{icon_svg}</div>'
        f'<div class="summary-label">{_escape(label)}</div>'
        f'<div class="summary-day">{_escape(days_main)}</div>'
        f"{dates_html}"
        "</div>"
    )


def build_weekly_horoscope_image_caption(post_text: str) -> str:
    lines = [line.strip() for line in post_text.splitlines() if line.strip()]
    headline = next(
        (line for line in lines if line.startswith("7 хоногийн") or "хоногийн" in line.lower()),
        lines[0] if lines else "7 хоногийн зурхай",
    )
    hashtags = [line for line in lines if line.startswith("#")]
    caption_lines = [
        headline,
        "Зурган дээр: 7 өдрийн үс засуулах, аян зам, үйл хийхийн чиглэл нэг харцаар.",
    ]
    if hashtags:
        caption_lines.append(hashtags[-1])
    caption_lines.append("Долоо хоногийн зурхайг өдөр бүр шинэчлэн авах бол манай page-ийг дагаарай.")
    return "\n".join(caption_lines).strip()


def _build_weekly_horoscope_html(post_text: str, source_context: str | None) -> str:
    entries = _parse_weekly_source_context(source_context)
    if len(entries) < 7:
        raise ValueError("weekly_source_missing_days")

    week_range_display = _extract_source_value(source_context, "Week range: ").strip()

    rows_html_parts: list[str] = []
    for idx, entry in enumerate(entries):
        weekday = entry.get("weekday", "")
        date_label = _short_date_label(entry.get("date", ""))
        hair_class, hair_label = _weekly_hair_status(entry.get("haircut_suitability", ""))
        hair_brief = (entry.get("haircut_omen", "") or hair_label).strip().rstrip(".")
        direction = _direction_short(entry.get("travel", ""))
        action_class, action_label = _weekly_action_status(entry.get("caution", ""))
        action_first = _split_items(entry.get("good_activities", ""), limit=2)
        action_brief = ", ".join(_sentence_case(item) for item in action_first) if action_first else action_label
        alt_class = " alt" if idx % 2 == 1 else ""

        rows_html_parts.append(
            f"""
        <div class="week-row{alt_class}">
          <div class="cell-day">
            <span class="weekday">{_escape(weekday)}</span>
            <span class="weekdate">{_escape(date_label)}</span>
          </div>
          <div class="cell-stat status-{hair_class}">
            <span class="stat-label">{_escape(hair_label)}</span>
            <span class="stat-brief">{_escape(hair_brief)}</span>
          </div>
          <div class="cell-stat status-travel">
            <span class="stat-label">{_escape(direction)}</span>
            <span class="stat-brief">мөрөө гаргавал</span>
          </div>
          <div class="cell-stat status-{action_class}">
            <span class="stat-label">{_escape(action_label)}</span>
            <span class="stat-brief">{_escape(action_brief)}</span>
          </div>
        </div>"""
        )

    rows_html = "\n".join(rows_html_parts)

    best_hair_days = _pick_highlight_days(
        entries, lambda e: "тохиромжгүй" not in e.get("haircut_suitability", "").lower()
    )
    best_action_days = _pick_highlight_days(
        entries,
        lambda e: "хянамгай" not in e.get("caution", "").lower() and bool(e.get("good_activities")),
    )
    best_travel_days = _pick_highlight_days(
        entries,
        lambda e: "зохистой" in e.get("travel", "").lower()
        and "болгоомж" not in e.get("travel", "").lower(),
    )

    summary_hair_html = _summary_card_html(_icon("scissors"), "Үс засуулах өдөр", best_hair_days)
    summary_travel_html = _summary_card_html(_icon("compass"), "Аян замд гарах", best_travel_days)
    summary_action_html = _summary_card_html(_icon("lotus"), "Үйл хийхэд сайн", best_action_days)

    return f"""<!doctype html>
<html lang="mn">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>7 Хоногийн Зурхай</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,500&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <style>{_ROYAL_BASE_CSS}{_WEEKLY_CSS}</style>
  </head>
  <body>
    <div class="bg">
      {_royal_background_html()}
      <div class="frame">
        <span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span>
        <div class="eyebrow">Долоо хоногийн тойм · Уламжлалт зурхай</div>
        <div class="date">{_escape(week_range_display)}</div>
        <h1 class="title">7 Хоногийн Зурхай</h1>
        <div class="subtitle">Үс засуулах · Аян зам · Үйл хийх</div>
        <div class="orn">{_icon("sun")}</div>

        <section class="week">
          <div class="week-head">
            <div class="col day">Өдөр</div>
            <div class="col">{_icon("scissors")}<span>Үс засуулах</span></div>
            <div class="col">{_icon("compass")}<span>Аян замд</span></div>
            <div class="col">{_icon("lotus")}<span>Үйл хийхэд</span></div>
          </div>
          {rows_html}
        </section>

        <section class="summary">
          {summary_hair_html}
          {summary_travel_html}
          {summary_action_html}
        </section>

        <div class="foot">Уламжлалт билгийн тооллын ерөнхий мэдээлэл</div>
      </div>
    </div>
  </body>
</html>"""


ZODIAC_HEADER_RE = re.compile(r"^(?P<sym>[^\w\s\u200d\ufe0f])\ufe0f?\s*(?P<label>.+?)\s*\((?P<range>[^)]+)\)\s*$")


def _parse_zodiac_post(post_text: str) -> tuple[str, list[dict[str, str]]]:
    lines = [line.rstrip() for line in post_text.splitlines()]
    intro_lines: list[str] = []
    signs: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = ZODIAC_HEADER_RE.match(stripped)
        if match:
            if current is not None:
                signs.append(current)
            current = {
                "sym": match.group("sym"),
                "label": match.group("label").strip(),
                "range": match.group("range").strip(),
                "text": "",
            }
            continue
        if current is not None:
            if stripped.startswith(("Тэмдэглэл", "Анхаар", "Эх сурвалж")):
                continue
            current["text"] = f"{current['text']} {stripped}".strip() if current["text"] else stripped
        else:
            if stripped.startswith("12 ордын"):
                continue
            intro_lines.append(stripped)

    if current is not None:
        signs.append(current)

    intro = " ".join(intro_lines).strip()
    return intro, signs


def _zodiac_date_label(post_text: str, source_context: str | None) -> str:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", post_text)
    if match:
        return match.group(1)
    match = re.search(r"(\d{4}-\d{2}-\d{2})", source_context or "")
    if match:
        return match.group(1)
    return datetime.now().strftime("%Y-%m-%d")


def build_zodiac_horoscope_image_caption(post_text: str) -> str:
    lines = [line.strip() for line in post_text.splitlines() if line.strip()]
    date_label = _zodiac_date_label(post_text, None)
    hashtags = [line for line in lines if line.startswith("#")]
    caption_lines = [
        f"12 ордын өдрийн зурхай · {date_label}",
        "Зурган дээр: 12 ордын өнөөдрийн товч зурхай нэг харцаар.",
    ]
    if hashtags:
        caption_lines.append(hashtags[-1])
    caption_lines.append("Орд бүрийн өдрийн зурхайг авах бол манай page-ийг дагаарай.")
    return "\n".join(line for line in caption_lines if line).strip()


def _build_zodiac_horoscope_html(post_text: str, source_context: str | None) -> str:
    intro, signs = _parse_zodiac_post(post_text)
    if len(signs) < 12:
        raise ValueError("zodiac_source_missing_signs")

    date_label = _zodiac_date_label(post_text, source_context)

    sign_cards = []
    for idx, sign in enumerate(signs):
        alt_class = " alt" if idx % 2 == 1 else ""
        sign_cards.append(
            f"""
        <div class="sign{alt_class}">
          <span class="sign-glyph">{_escape(sign["sym"])}\ufe0e</span>
          <div class="sign-body">
            <div class="sign-head">
              <span class="sign-name">{_escape(sign["label"])}</span>
              <span class="sign-range">{_escape(sign["range"])}</span>
            </div>
            <p class="sign-text">{_escape(sign["text"])}</p>
          </div>
        </div>"""
        )
    signs_html = "\n".join(sign_cards)

    intro_html = f'<p class="lead">{_escape(intro)}</p>' if intro else ""

    return f"""<!doctype html>
<html lang="mn">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>12 Ордын Зурхай</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,500&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <style>{_ROYAL_BASE_CSS}{_ZODIAC_CSS}</style>
  </head>
  <body>
    <div class="bg">
      {_royal_background_html()}
      <div class="frame">
        <span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span>
        <div class="eyebrow">Од эрхсийн · Уламжлалт зурхай</div>
        <div class="date">{_escape(date_label)}</div>
        <h1 class="title">12 Ордын Зурхай</h1>
        <div class="orn">{_icon("sun")}</div>
        {intro_html}
        <section class="signs">
          {signs_html}
        </section>
        <div class="foot">Энэ нь ордын ерөнхий зурхай · хувь хүний нөхцөлөөс хамаарч өөр байна</div>
      </div>
    </div>
  </body>
</html>"""


def generate_zodiac_horoscope_card_image(
    *,
    post_text: str,
    source_context: str | None,
    slug: str,
) -> Path:
    return _render_html_to_png(_build_zodiac_horoscope_html(post_text, source_context), slug)


def cleanup_generated_card_assets(image_path: str | Path) -> None:
    path = Path(image_path)
    related_paths = [path, path.with_suffix(".html")]
    for target in related_paths:
        try:
            if target.exists():
                target.unlink()
        except OSError as exc:
            raise RuntimeError(f"failed_to_cleanup_generated_asset:{target.name}:{exc}") from exc
