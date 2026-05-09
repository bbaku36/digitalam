"""Image card generation for selected autopost categories."""

from __future__ import annotations

import html
import re
import shutil
import subprocess
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
        return '<div class="animal-empty">—</div>'
    items = []
    for name in years:
        emoji = YEAR_EMOJIS.get(name.lower(), "✦")
        items.append(
            f'<div class="animal-seal-card">'
            f'<div class="animal-seal"><div class="animal-emoji">{_escape(emoji)}</div></div>'
            f'<div class="animal-name">{_escape(name)}</div>'
            f"</div>"
        )
    return "\n".join(items)


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
    hair_status_class = "" if hair_status == "Тохиромжтой" else "bad"

    source_travel = _extract_source_value(source_context, "Travel direction: ")
    travel_text = parsed.get("travel_text", "")
    if source_travel:
        travel_text = f"Хол газар яваар одогсод {source_travel.rstrip('.')}."
    travel_status = _travel_status(source_travel or travel_text)
    travel_status_class = "" if travel_status == "Сайн" else "bad"

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

    favorable_seals_html = _year_seal_html(favorable_years)
    caution_seals_html = _year_seal_html(caution_years)

    good_activities_html = "\n".join(
        f'<div class="list-item"><span class="dot good">•</span><span>{_escape(item)}</span></div>'
        for item in (good_activities or [parsed.get("action_text", "")])
        if item
    )
    caution_html = "\n".join(
        f'<div class="list-item"><span class="dot bad">•</span><span>{_escape(item)}</span></div>'
        for item in (caution_items or [parsed.get("caution_text", "")])
        if item
    )

    return f"""<!doctype html>
<html lang="mn">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Horoscope Card</title>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Montserrat:wght@300;400;700&display=swap');
      
      :root {{
        --paper: #f8f1de;
        --paper-deep: #efe2c0;
        --paper-soft: #fbf6e8;
        --ink: #2a1f12;
        --ink-soft: #4a3a25;
        --ink-mute: #7a6745;
        --gold: #b8860b;
        --gold-soft: #c9a857;
        --gold-glow: rgba(184, 134, 11, 0.18);
        --line: rgba(125, 95, 32, 0.22);
        --good: #4f7032;
        --bad: #a14a3c;
      }}
      * {{ box-sizing: border-box; }}
      html, body {{ margin: 0; background: var(--paper); font-family: 'Montserrat', sans-serif; color: var(--ink); width: 1080px; height: 1350px; overflow: hidden; }}
      .page {{ display: flex; justify-content: center; padding: 0; width: 1080px; height: 1350px; }}

      .card {{
        width: 1080px;
        height: 1350px;
        background:
          radial-gradient(circle at 12% 18%, rgba(255, 240, 200, 0.7), transparent 45%),
          radial-gradient(circle at 88% 82%, rgba(212, 175, 55, 0.12), transparent 45%),
          linear-gradient(160deg, var(--paper-soft) 0%, var(--paper) 55%, var(--paper-deep) 100%);
        position: relative;
        overflow: hidden;
        border: 1px solid var(--line);
        display: flex;
        flex-direction: column;
      }}

      /* Decorative Mandala SVG in Background */
      .card::before {{
        content: "";
        position: absolute;
        top: -220px;
        right: -220px;
        width: 900px;
        height: 900px;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='45' stroke='%23b8860b' stroke-width='0.15' fill='none' opacity='0.18'/%3E%3Ccircle cx='50' cy='50' r='35' stroke='%23b8860b' stroke-width='0.12' fill='none' opacity='0.14'/%3E%3Cpath d='M50 5 L50 95 M5 50 L95 50' stroke='%23b8860b' stroke-width='0.08' opacity='0.1'/%3E%3C/svg%3E");
        background-size: contain;
        background-repeat: no-repeat;
        pointer-events: none;
        z-index: 0;
        opacity: 0.45;
      }}
      .card::after {{
        content: "";
        position: absolute;
        bottom: -260px;
        left: -260px;
        width: 720px;
        height: 720px;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='48' stroke='%23b8860b' stroke-width='0.2' fill='none' opacity='0.18'/%3E%3C/svg%3E");
        background-size: contain;
        background-repeat: no-repeat;
        pointer-events: none;
        z-index: 0;
        opacity: 0.35;
      }}
      
      .content {{ padding: 64px 80px 56px; position: relative; z-index: 2; flex: 1; display: flex; flex-direction: column; }}

      header {{ text-align: center; margin-bottom: 56px; }}

      .date-badge {{
        display: inline-block;
        background: var(--gold);
        color: var(--paper-soft);
        padding: 14px 52px;
        border-radius: 99px;
        font-family: 'Montserrat', sans-serif;
        font-size: 36px;
        font-weight: 800;
        margin-bottom: 32px;
        box-shadow: 0 8px 24px rgba(125, 95, 32, 0.25);
        letter-spacing: -0.01em;
      }}

      .title {{
        margin: 0;
        font-family: 'Playfair Display', serif;
        font-size: 92px;
        font-weight: 700;
        letter-spacing: 0.03em;
        color: var(--ink);
        text-transform: uppercase;
        line-height: 1;
      }}
      .subtitle {{
        margin: 20px 0 0;
        color: var(--ink-mute);
        font-size: 22px;
        font-weight: 500;
        letter-spacing: 0.2em;
        text-transform: uppercase;
      }}

      .main-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        row-gap: 44px;
        column-gap: 32px;
        margin-top: 8px;
      }}

      .section-card {{
        background: rgba(255, 250, 232, 0.55);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 32px;
        position: relative;
        box-shadow: 0 4px 12px rgba(125, 95, 32, 0.06);
      }}

      .overview-section {{ grid-column: span 2; border: none; background: transparent; padding: 0; text-align: center; margin-bottom: 12px; box-shadow: none; }}
      .overview-section h2 {{
        font-family: 'Playfair Display', serif;
        font-size: 32px;
        color: var(--gold);
        margin: 0 0 20px;
        text-transform: uppercase;
        letter-spacing: 0.15em;
      }}
      .overview-section p {{
        font-size: 26px;
        line-height: 1.65;
        max-width: 92%;
        margin: 0 auto;
        font-weight: 400;
        color: var(--ink-soft);
      }}

      .animal-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 32px; grid-column: span 2; padding: 0 8px; margin-bottom: 4px; }}
      .animal-group {{ text-align: center; }}
      .animal-label {{
        font-size: 16px;
        font-weight: 800;
        text-transform: uppercase;
        color: var(--ink-mute);
        letter-spacing: 0.24em;
        margin-bottom: 18px;
      }}
      .animal-seals {{ display: flex; justify-content: center; gap: 28px; flex-wrap: wrap; }}
      .animal-seal-card {{ display: flex; flex-direction: column; align-items: center; gap: 12px; }}

      .animal-seal {{
        width: 120px;
        height: 120px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(184, 134, 11, 0.14), rgba(255, 245, 215, 0.5) 70%);
        border: 1.5px solid var(--gold-soft);
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        box-shadow: 0 6px 18px rgba(125, 95, 32, 0.18);
      }}
      .animal-seal::after {{
        content: "";
        position: absolute;
        top: 7px; left: 7px; right: 7px; bottom: 7px;
        border: 1px dashed rgba(184, 134, 11, 0.35);
        border-radius: 50%;
      }}

      .animal-emoji {{
        font-size: 64px;
        z-index: 2;
        filter: drop-shadow(0 2px 4px rgba(125, 95, 32, 0.25));
      }}

      .animal-name {{
        font-size: 24px;
        font-weight: 700;
        color: var(--ink);
        font-family: 'Playfair Display', serif;
      }}
      .animal-empty {{ color: var(--ink-mute); font-size: 22px; padding: 40px 0; }}

      .panel {{ display: flex; flex-direction: column; gap: 12px; }}
      .panel-title {{
        font-family: 'Playfair Display', serif;
        font-size: 26px;
        color: var(--ink);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: flex;
        align-items: center;
        gap: 12px;
      }}
      .panel-icon {{ font-size: 22px; opacity: 0.85; }}
      .panel-status {{ font-size: 16px; font-weight: 700; color: var(--gold); margin-left: auto; border: 1px solid var(--gold); padding: 4px 10px; letter-spacing: 0.05em; border-radius: 2px; }}
      .panel-status.bad {{ color: var(--bad); border-color: var(--bad); }}
      .panel-content {{ font-size: 21px; line-height: 1.55; color: var(--ink-soft); font-weight: 400; }}

      .list-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 32px; grid-column: span 2; margin-top: 4px; }}
      .list-box-title {{
        font-size: 18px;
        font-weight: 800;
        text-transform: uppercase;
        color: var(--ink);
        letter-spacing: 0.12em;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 12px;
      }}
      .list-box-title::after {{ content: ""; height: 1px; flex: 1; background: var(--line); }}

      .list-items {{ display: grid; gap: 12px; }}
      .item {{ display: flex; align-items: flex-start; gap: 12px; font-size: 20px; line-height: 1.45; color: var(--ink-soft); font-weight: 400; }}
      .item-mark {{ font-size: 18px; margin-top: 2px; font-weight: 700; }}
      .item-mark.good {{ color: var(--good); }}
      .item-mark.bad {{ color: var(--bad); }}

      .footer {{ margin-top: auto; padding-top: 28px; text-align: center; opacity: 0.6; }}
      .footer p {{ font-size: 14px; letter-spacing: 0.3em; text-transform: uppercase; line-height: 1.5; color: var(--ink-mute); }}

      .suudal-badge {{
        display: inline-block;
        margin-top: 14px;
        padding: 6px 18px;
        border: 1px solid var(--gold-soft);
        font-size: 14px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--gold);
        background: rgba(255, 250, 232, 0.7);
        border-radius: 2px;
      }}
    </style>
  </head>
  <body>
    <main class="page">
      <article class="card">
        <div class="content">
          <header>
            <div class="date-badge">{_escape(compact_date)}</div>
            <h1 class="title">Өдрийн Зурхай</h1>
            <p class="subtitle">{_escape(biligiin_line)}</p>
          </header>
          
          <section class="main-grid">
            <section class="section-card overview-section">
              <h2>Өдрийн Төлөв</h2>
              <p>{_escape(general_text)}</p>
              <div class="suudal-badge">Суудал: {_escape(suudal)}</div>
            </section>
            
            <div class="animal-grid">
              <div class="animal-group">
                <div class="animal-label">Сайн жилтэн</div>
                <div class="animal-seals">{favorable_seals_html}</div>
              </div>
              <div class="animal-group">
                <div class="animal-label">Болгоомжлох</div>
                <div class="animal-seals">{caution_seals_html}</div>
              </div>
            </div>

            <section class="section-card panel">
              <div class="panel-title">
                <span class="panel-icon">✂️</span>
                <span>Үс засуулах</span>
                <span class="panel-status {hair_status_class}">{_escape(hair_status)}</span>
              </div>
              <div class="panel-content">{_escape(hair_text)}</div>
            </section>

            <section class="section-card panel">
              <div class="panel-title">
                <span class="panel-icon">🧭</span>
                <span>Аян замд</span>
                <span class="panel-status {travel_status_class}">{_escape(travel_status)}</span>
              </div>
              <div class="panel-content">{_escape(travel_text)}</div>
            </section>
            
            <div class="list-container">
              <div class="list-box">
                <div class="list-box-title">Үйл хийхэд сайн</div>
                <div class="list-items">{good_activities_html.replace('list-item', 'item').replace('dot', 'item-mark')}</div>
              </div>
              <div class="list-box">
                <div class="list-box-title">Цээрлэх зүйлс</div>
                <div class="list-items">{caution_html.replace('list-item', 'item').replace('dot', 'item-mark')}</div>
              </div>
            </div>
          </section>

          <footer class="footer">
            <p>{_escape(parsed.get("disclaimer", "Уламжлалт билгийн тоолол"))}</p>
          </footer>
        </div>
      </article>
    </main>
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


def _pick_highlight_day(entries: list[dict[str, str]], picker) -> tuple[str, str]:
    for entry in entries:
        if picker(entry):
            return entry["weekday"], _short_date_label(entry["date"])
    return "—", ""


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

    week_range = _extract_source_value(source_context, "Week range: ").strip()
    if week_range:
        week_range_display = week_range.replace(".", "-").replace("-", ".", 2)
        week_range_display = week_range
    else:
        week_range_display = ""

    rows_html_parts: list[str] = []
    for entry in entries:
        weekday = entry.get("weekday", "")
        date_label = _short_date_label(entry.get("date", ""))
        hair_class, hair_label = _weekly_hair_status(entry.get("haircut_suitability", ""))
        hair_brief = _short_omen(entry.get("haircut_omen", "") or hair_label, max_chars=24)
        direction = _direction_short(entry.get("travel", ""))
        action_class, action_label = _weekly_action_status(entry.get("caution", ""))
        action_first = _split_items(entry.get("good_activities", ""), limit=1)
        action_brief = _short_omen(action_first[0] if action_first else action_label, max_chars=22)

        rows_html_parts.append(
            f"""
        <div class="week-row">
          <div class="cell cell-day">
            <div class="weekday">{_escape(weekday)}</div>
            <div class="weekdate">{_escape(date_label)}</div>
          </div>
          <div class="cell cell-stat status-{hair_class}">
            <div class="stat-icon">✂</div>
            <div class="stat-label">{_escape(hair_label)}</div>
            <div class="stat-brief">{_escape(hair_brief)}</div>
          </div>
          <div class="cell cell-stat status-good">
            <div class="stat-icon">🧭</div>
            <div class="stat-label">{_escape(direction)}</div>
            <div class="stat-brief">мөрөө гаргавал</div>
          </div>
          <div class="cell cell-stat status-{action_class}">
            <div class="stat-icon">📿</div>
            <div class="stat-label">{_escape(action_label)}</div>
            <div class="stat-brief">{_escape(action_brief)}</div>
          </div>
        </div>"""
        )

    rows_html = "\n".join(rows_html_parts)

    best_hair_day, best_hair_date = _pick_highlight_day(
        entries, lambda e: "тохиромжгүй" not in e.get("haircut_suitability", "").lower()
    )
    best_action_day, best_action_date = _pick_highlight_day(
        entries, lambda e: "хянамгай" not in e.get("caution", "").lower() and bool(e.get("good_activities"))
    )
    best_travel_day, best_travel_date = entries[0]["weekday"], _short_date_label(entries[0]["date"])
    for entry in entries:
        guidance = entry.get("travel", "").lower()
        if "зохистой" in guidance and "болгоомж" not in guidance:
            best_travel_day = entry["weekday"]
            best_travel_date = _short_date_label(entry["date"])
            break

    return f"""<!doctype html>
<html lang="mn">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Weekly Horoscope Card</title>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Montserrat:wght@400;500;700;800&display=swap');

      :root {{
        --paper: #f8f1de;
        --paper-deep: #efe2c0;
        --paper-soft: #fbf6e8;
        --ink: #2a1f12;
        --ink-soft: #4a3a25;
        --ink-mute: #7a6745;
        --gold: #b8860b;
        --gold-soft: #c9a857;
        --line: rgba(125, 95, 32, 0.22);
        --good: #4f7032;
        --warn: #b67a1f;
        --bad: #a14a3c;
        --row-good: rgba(79, 112, 50, 0.08);
        --row-warn: rgba(182, 122, 31, 0.10);
        --row-bad: rgba(161, 74, 60, 0.10);
      }}
      * {{ box-sizing: border-box; }}
      html, body {{ margin: 0; background: var(--paper); font-family: 'Montserrat', sans-serif; color: var(--ink); width: 1080px; height: 1350px; overflow: hidden; }}
      .page {{ display: flex; justify-content: center; padding: 0; width: 1080px; height: 1350px; }}

      .card {{
        width: 1080px;
        height: 1350px;
        background:
          radial-gradient(circle at 12% 18%, rgba(255, 240, 200, 0.7), transparent 45%),
          radial-gradient(circle at 88% 82%, rgba(212, 175, 55, 0.12), transparent 45%),
          linear-gradient(160deg, var(--paper-soft) 0%, var(--paper) 55%, var(--paper-deep) 100%);
        position: relative;
        overflow: hidden;
        border: 1px solid var(--line);
        display: flex;
        flex-direction: column;
      }}
      .card::before {{
        content: "";
        position: absolute;
        top: -220px; right: -220px;
        width: 900px; height: 900px;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='45' stroke='%23b8860b' stroke-width='0.15' fill='none' opacity='0.18'/%3E%3Ccircle cx='50' cy='50' r='35' stroke='%23b8860b' stroke-width='0.12' fill='none' opacity='0.14'/%3E%3C/svg%3E");
        background-size: contain; background-repeat: no-repeat;
        pointer-events: none; z-index: 0; opacity: 0.45;
      }}

      .content {{ padding: 60px 70px 50px; position: relative; z-index: 2; flex: 1; display: flex; flex-direction: column; }}

      header {{ text-align: center; margin-bottom: 32px; }}
      .date-badge {{
        display: inline-block;
        background: var(--gold);
        color: var(--paper-soft);
        padding: 12px 44px;
        border-radius: 99px;
        font-size: 28px;
        font-weight: 800;
        margin-bottom: 24px;
        box-shadow: 0 8px 24px rgba(125, 95, 32, 0.22);
        letter-spacing: 0.02em;
      }}
      .title {{
        margin: 0;
        font-family: 'Playfair Display', serif;
        font-size: 76px;
        font-weight: 700;
        color: var(--ink);
        line-height: 1;
        text-transform: uppercase;
        letter-spacing: 0.02em;
      }}
      .subtitle {{
        margin: 16px 0 0;
        color: var(--ink-mute);
        font-size: 19px;
        font-weight: 500;
        letter-spacing: 0.18em;
        text-transform: uppercase;
      }}

      .week-grid {{ display: flex; flex-direction: column; gap: 0; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; background: rgba(255, 250, 232, 0.55); box-shadow: 0 4px 12px rgba(125, 95, 32, 0.06); }}

      .header-row, .week-row {{ display: grid; grid-template-columns: 200px 1fr 1fr 1fr; align-items: center; }}
      .header-row {{
        padding: 14px 20px;
        background: rgba(184, 134, 11, 0.10);
        border-bottom: 1px solid var(--line);
      }}
      .header-row .col-label {{
        font-size: 14px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        color: var(--ink-mute);
        text-align: center;
      }}
      .header-row .col-label.day {{ text-align: left; padding-left: 8px; }}

      .week-row {{ padding: 14px 20px; border-bottom: 1px solid var(--line); min-height: 92px; }}
      .week-row:last-child {{ border-bottom: none; }}
      .week-row:nth-child(even) {{ background: rgba(255, 240, 200, 0.18); }}

      .cell-day {{ display: flex; flex-direction: column; align-items: flex-start; padding-left: 8px; gap: 2px; }}
      .weekday {{
        font-family: 'Playfair Display', serif;
        font-size: 30px;
        font-weight: 700;
        color: var(--ink);
        line-height: 1;
      }}
      .weekdate {{ font-size: 18px; font-weight: 600; color: var(--ink-mute); letter-spacing: 0.04em; }}

      .cell-stat {{
        display: grid;
        grid-template-columns: 38px 1fr;
        grid-template-rows: auto auto;
        gap: 2px 12px;
        align-items: center;
        padding: 0 14px;
      }}
      .stat-icon {{
        grid-row: 1 / span 2;
        font-size: 28px;
        line-height: 1;
        text-align: center;
      }}
      .stat-label {{ font-size: 18px; font-weight: 700; color: var(--ink); line-height: 1.15; }}
      .stat-brief {{ font-size: 13px; color: var(--ink-mute); line-height: 1.25; letter-spacing: 0.02em; }}
      .status-good .stat-label {{ color: var(--good); }}
      .status-warn .stat-label {{ color: var(--warn); }}
      .status-bad .stat-label {{ color: var(--bad); }}

      .summary {{
        margin-top: 28px;
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 16px;
      }}
      .summary-card {{
        background: rgba(255, 250, 232, 0.65);
        border: 1px solid var(--line);
        border-radius: 6px;
        padding: 18px 20px;
        text-align: center;
      }}
      .summary-icon {{ font-size: 26px; margin-bottom: 4px; }}
      .summary-label {{
        font-size: 12px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        color: var(--ink-mute);
        margin-bottom: 6px;
      }}
      .summary-day {{
        font-family: 'Playfair Display', serif;
        font-size: 24px;
        font-weight: 700;
        color: var(--gold);
      }}
      .summary-date {{ font-size: 14px; color: var(--ink-mute); margin-top: 2px; }}

      .footer {{ margin-top: auto; padding-top: 22px; text-align: center; opacity: 0.65; }}
      .footer p {{ font-size: 13px; letter-spacing: 0.28em; text-transform: uppercase; line-height: 1.5; color: var(--ink-mute); margin: 0; }}
    </style>
  </head>
  <body>
    <main class="page">
      <article class="card">
        <div class="content">
          <header>
            <div class="date-badge">{_escape(week_range_display)}</div>
            <h1 class="title">7 хоногийн зурхай</h1>
            <p class="subtitle">Үс засуулах · Аян зам · Үйл хийх</p>
          </header>

          <section class="week-grid">
            <div class="header-row">
              <div class="col-label day">Өдөр</div>
              <div class="col-label">✂ Үс засуулах</div>
              <div class="col-label">🧭 Аян замд</div>
              <div class="col-label">📿 Үйл хийхэд</div>
            </div>
            {rows_html}
          </section>

          <section class="summary">
            <div class="summary-card">
              <div class="summary-icon">✂</div>
              <div class="summary-label">Үс засуулах өдөр</div>
              <div class="summary-day">{_escape(best_hair_day)}</div>
              <div class="summary-date">{_escape(best_hair_date)}</div>
            </div>
            <div class="summary-card">
              <div class="summary-icon">🧭</div>
              <div class="summary-label">Аян замд гарах</div>
              <div class="summary-day">{_escape(best_travel_day)}</div>
              <div class="summary-date">{_escape(best_travel_date)}</div>
            </div>
            <div class="summary-card">
              <div class="summary-icon">📿</div>
              <div class="summary-label">Үйл хийхэд сайн</div>
              <div class="summary-day">{_escape(best_action_day)}</div>
              <div class="summary-date">{_escape(best_action_date)}</div>
            </div>
          </section>

          <footer class="footer">
            <p>Эх сурвалж · gogo.mn / Цаг тооны бичиг</p>
          </footer>
        </div>
      </article>
    </main>
  </body>
</html>"""


def cleanup_generated_card_assets(image_path: str | Path) -> None:
    path = Path(image_path)
    related_paths = [path, path.with_suffix(".html")]
    for target in related_paths:
        try:
            if target.exists():
                target.unlink()
        except OSError as exc:
            raise RuntimeError(f"failed_to_cleanup_generated_asset:{target.name}:{exc}") from exc
