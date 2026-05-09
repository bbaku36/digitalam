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
    hair_panel_class = "hair-good" if hair_status == "Тохиромжтой" else "hair-bad"

    source_travel = _extract_source_value(source_context, "Travel direction: ")
    travel_text = parsed.get("travel_text", "")
    if source_travel:
        travel_text = f"Хол газар яваар одогсод {source_travel.rstrip('.')}."
    travel_status = _travel_status(source_travel or travel_text)

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

    favorable_emoji = _emoji_for_years(favorable_years)
    caution_emoji = _emoji_for_years(caution_years)

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
        --gold: #d4af37;
        --gold-glow: rgba(212, 175, 55, 0.4);
        --text-gold: #f3e5ab;
        --deep-void: #07050f;
        --nebula-purple: rgba(88, 28, 135, 0.3);
        --nebula-teal: rgba(13, 148, 136, 0.2);
        --glass-white: rgba(255, 255, 255, 0.03);
        --ink: #f8fafc;
        --muted: #94a3b8;
      }}
      * {{ box-sizing: border-box; }}
      html, body {{ margin: 0; background: var(--deep-void); font-family: 'Montserrat', sans-serif; color: var(--ink); width: 1080px; height: 1350px; overflow: hidden; }}
      .page {{ display: flex; justify-content: center; padding: 0; width: 1080px; height: 1350px; }}

      .card {{
        width: 1080px;
        height: 1350px;
        background:
          radial-gradient(circle at 10% 20%, var(--nebula-purple), transparent 40%),
          radial-gradient(circle at 90% 80%, var(--nebula-teal), transparent 40%),
          radial-gradient(circle at 50% 50%, rgba(20, 10, 40, 1), var(--deep-void) 80%);
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(212, 175, 55, 0.15);
        display: flex;
        flex-direction: column;
      }}

      /* Decorative Mandala SVG in Background - More subtle and pushed back */
      .card::before {{
        content: "";
        position: absolute;
        top: -220px;
        right: -220px;
        width: 900px;
        height: 900px;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='45' stroke='%23d4af37' stroke-width='0.1' fill='none' opacity='0.05'/%3E%3Ccircle cx='50' cy='50' r='35' stroke='%23d4af37' stroke-width='0.08' fill='none' opacity='0.04'/%3E%3Cpath d='M50 5 L50 95 M5 50 L95 50' stroke='%23d4af37' stroke-width='0.05' opacity='0.03'/%3E%3C/svg%3E");
        background-size: contain;
        background-repeat: no-repeat;
        pointer-events: none;
        z-index: 0;
        opacity: 0.5;
      }}
      
      .content {{ padding: 64px 80px 56px; position: relative; z-index: 2; flex: 1; display: flex; flex-direction: column; }}

      header {{ text-align: center; margin-bottom: 56px; }}

      .date-badge {{
        display: inline-block;
        background: var(--gold);
        color: var(--deep-void);
        padding: 14px 52px;
        border-radius: 99px;
        font-family: 'Montserrat', sans-serif;
        font-size: 36px;
        font-weight: 800;
        margin-bottom: 32px;
        box-shadow: 0 14px 40px rgba(0,0,0,0.5), 0 0 28px var(--gold-glow);
        letter-spacing: -0.01em;
      }}

      .title {{
        margin: 0;
        font-family: 'Playfair Display', serif;
        font-size: 92px;
        font-weight: 700;
        letter-spacing: 0.03em;
        color: var(--text-gold);
        text-shadow: 0 0 40px var(--gold-glow);
        text-transform: uppercase;
        line-height: 1;
      }}
      .subtitle {{
        margin: 20px 0 0;
        color: var(--muted);
        font-size: 22px;
        font-weight: 400;
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
        background: var(--glass-white);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 6px;
        padding: 32px;
        position: relative;
      }}

      .overview-section {{ grid-column: span 2; border: none; background: transparent; padding: 0; text-align: center; margin-bottom: 12px; }}
      .overview-section h2 {{
        font-family: 'Playfair Display', serif;
        font-size: 32px;
        color: var(--gold);
        margin: 0 0 20px;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        opacity: 0.9;
      }}
      .overview-section p {{
        font-size: 26px;
        line-height: 1.65;
        max-width: 90%;
        margin: 0 auto;
        font-weight: 300;
        color: #e2e8f0;
      }}

      .animal-grid {{ display: flex; justify-content: space-around; gap: 56px; margin-bottom: 4px; grid-column: span 2; padding: 0 60px; }}
      .animal-item {{ text-align: center; flex: 1; }}

      .animal-seal {{
        width: 150px;
        height: 150px;
        margin: 0 auto 22px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(212, 175, 55, 0.15), transparent);
        border: 1px solid rgba(212, 175, 55, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        box-shadow: 0 10px 32px rgba(0,0,0,0.4);
      }}
      .animal-seal::after {{
        content: "";
        position: absolute;
        top: 8px; left: 8px; right: 8px; bottom: 8px;
        border: 1px dashed rgba(212, 175, 55, 0.2);
        border-radius: 50%;
      }}

      .animal-emoji {{
        font-size: 76px;
        filter: sepia(1) saturate(4) brightness(0.9) drop-shadow(0 4px 8px rgba(0,0,0,0.5));
        z-index: 2;
      }}

      .animal-label {{ font-size: 15px; font-weight: 800; text-transform: uppercase; color: var(--muted); letter-spacing: 0.22em; margin-bottom: 8px; }}
      .animal-names {{ font-size: 26px; font-weight: 700; color: var(--text-gold); text-shadow: 0 0 12px var(--gold-glow); }}

      .panel {{ display: flex; flex-direction: column; gap: 12px; }}
      .panel-title {{
        font-family: 'Playfair Display', serif;
        font-size: 26px;
        color: var(--text-gold);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: flex;
        align-items: center;
        gap: 12px;
      }}
      .panel-icon {{ font-size: 22px; opacity: 0.75; }}
      .panel-status {{ font-size: 16px; font-weight: 700; color: var(--gold); margin-left: auto; border: 1px solid var(--gold); padding: 4px 10px; letter-spacing: 0.05em; }}
      .panel-content {{ font-size: 21px; line-height: 1.55; color: var(--muted); font-weight: 400; }}

      .list-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 32px; grid-column: span 2; margin-top: 4px; }}
      .list-box-title {{
        font-size: 18px;
        font-weight: 800;
        text-transform: uppercase;
        color: var(--text-gold);
        letter-spacing: 0.12em;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 12px;
      }}
      .list-box-title::after {{ content: ""; height: 1px; flex: 1; background: rgba(212, 175, 55, 0.15); }}

      .list-items {{ display: grid; gap: 12px; }}
      .item {{ display: flex; align-items: flex-start; gap: 12px; font-size: 20px; line-height: 1.45; color: #cbd5e1; font-weight: 400; }}
      .item-mark {{ font-size: 18px; margin-top: 2px; }}
      .item-mark.good {{ color: #10b981; }}
      .item-mark.bad {{ color: #fb7185; }}

      .footer {{ margin-top: auto; padding-top: 28px; text-align: center; opacity: 0.45; }}
      .footer p {{ font-size: 14px; letter-spacing: 0.3em; text-transform: uppercase; line-height: 1.5; }}

      .suudal-badge {{
        display: inline-block;
        margin-top: 14px;
        padding: 6px 18px;
        border: 1px solid rgba(212, 175, 55, 0.3);
        font-size: 14px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--gold);
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
              <div class="animal-item">
                <div class="animal-seal">
                  <div class="animal-emoji">{_escape(favorable_emoji)}</div>
                </div>
                <div class="animal-label">Сайн жилтэн</div>
                <div class="animal-names">{_escape(", ".join(favorable_years))}</div>
              </div>
              <div class="animal-item">
                <div class="animal-seal">
                  <div class="animal-emoji">{_escape(caution_emoji)}</div>
                </div>
                <div class="animal-label">Болгоомжлох</div>
                <div class="animal-names">{_escape(", ".join(caution_years))}</div>
              </div>
            </div>

            <section class="section-card panel">
              <div class="panel-title">
                <span class="panel-icon">✂️</span>
                <span>Үс засуулах</span>
                <span class="panel-status">{_escape(hair_status)}</span>
              </div>
              <div class="panel-content">{_escape(hair_text)}</div>
            </section>
            
            <section class="section-card panel">
              <div class="panel-title">
                <span class="panel-icon">🧭</span>
                <span>Аян замд</span>
                <span class="panel-status">{_escape(travel_status)}</span>
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


def generate_horoscope_card_image(
    *,
    post_text: str,
    source_context: str | None,
    slug: str,
) -> Path:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node_not_found_for_image_card")

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    html_path = GENERATED_DIR / f"{slug}.html"
    png_path = GENERATED_DIR / f"{slug}.png"

    html_content = _build_horoscope_html(post_text, source_context)
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
        raise RuntimeError("horoscope_card_png_missing")
    return png_path


def cleanup_generated_card_assets(image_path: str | Path) -> None:
    path = Path(image_path)
    related_paths = [path, path.with_suffix(".html")]
    for target in related_paths:
        try:
            if target.exists():
                target.unlink()
        except OSError as exc:
            raise RuntimeError(f"failed_to_cleanup_generated_asset:{target.name}:{exc}") from exc
