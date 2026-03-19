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
      :root {{
        --ink: #10203a;
        --muted: #5b6b83;
        --card: #ffffff;
        --line: rgba(148, 163, 184, 0.18);
        --indigo: #4338ca;
        --indigo-soft: #eef2ff;
        --blue-soft: #eff6ff;
        --cyan-soft: #ecfeff;
        --emerald-soft: #ecfdf5;
        --rose-soft: #fff1f2;
        --amber-soft: #fff7ed;
      }}
      * {{ box-sizing: border-box; }}
      html, body {{ margin: 0; background: #ffffff; font-family: "SF Pro Display", "Segoe UI", sans-serif; color: var(--ink); }}
      .page {{ display: flex; justify-content: center; padding: 0; }}
      .card {{
        width: 100%;
        max-width: 720px;
        border-radius: 36px;
        overflow: hidden;
        background:
          radial-gradient(circle at top left, rgba(99, 102, 241, 0.08), transparent 26%),
          radial-gradient(circle at bottom right, rgba(14, 165, 233, 0.10), transparent 22%),
          var(--card);
      }}
      .content {{ padding: 24px 26px 20px; }}
      .date-chip {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 14px 24px 16px;
        border: 1px solid rgba(99, 102, 241, 0.14);
        border-radius: 24px;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(238, 242, 255, 0.92));
        box-shadow: 0 12px 26px rgba(99, 102, 241, 0.08);
      }}
      .date-chip-value {{
        color: #312e81;
        font-size: 32px;
        line-height: 1;
        font-weight: 900;
        letter-spacing: -0.04em;
      }}
      .title {{
        margin: 14px 0 8px;
        font-family: "Iowan Old Style", "Palatino Linotype", serif;
        font-size: 38px;
        line-height: 0.98;
        font-weight: 700;
        letter-spacing: -0.05em;
      }}
      .subtitle {{
        margin: 0;
        color: var(--muted);
        font-size: 14px;
        line-height: 1.5;
        font-weight: 600;
      }}
      .hero-grid {{
        display: grid;
        grid-template-columns: 1.3fr 0.9fr;
        gap: 12px;
        margin-top: 20px;
        align-items: stretch;
      }}
      .overview {{
        display: flex;
        gap: 14px;
        margin-top: 0;
        padding: 16px;
        border: 1px solid rgba(125, 211, 252, 0.35);
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(239, 246, 255, 0.92), rgba(255, 255, 255, 0.8));
      }}
      .icon-box {{
        width: 48px;
        height: 48px;
        flex: 0 0 auto;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(125, 211, 252, 0.2);
        font-size: 22px;
      }}
      .overview h2, .panel h3 {{ margin: 0 0 4px; font-size: 17px; line-height: 1.2; }}
      .overview p, .panel p, .list-item {{ margin: 0; font-size: 13px; line-height: 1.55; color: var(--muted); font-weight: 600; }}
      .suudal {{
        display: inline-flex;
        align-items: center;
        margin-top: 8px;
        padding: 6px 10px;
        border-radius: 12px;
        background: rgba(79, 70, 229, 0.08);
        color: #4338ca;
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }}
      .year-grid {{ display: grid; gap: 12px; }}
      .year-card, .panel {{ border-radius: 28px; border: 1px solid var(--line); background: rgba(255, 255, 255, 0.74); }}
      .year-card {{ padding: 14px 14px; text-align: center; }}
      .animal {{ font-size: 25px; margin-bottom: 8px; }}
      .label {{ margin-bottom: 4px; font-size: 10px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.16em; }}
      .label.good {{ color: #059669; }}
      .label.warn {{ color: #e11d48; }}
      .year-value {{ font-size: 16px; font-weight: 800; line-height: 1.2; }}
      .detail-grid, .list-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }}
      .panel {{ position: relative; overflow: hidden; padding: 16px 16px 16px 18px; }}
      .panel::before {{ content: ""; position: absolute; top: 12px; bottom: 12px; left: 0; width: 5px; border-radius: 999px; }}
      .panel-head {{ display: flex; align-items: flex-start; gap: 10px; margin-bottom: 0; }}
      .panel-icon {{
        width: 40px; height: 40px; display: inline-flex; align-items: center; justify-content: center;
        border-radius: 14px; background: rgba(255, 255, 255, 0.92); border: 1px solid rgba(255, 255, 255, 0.6); font-size: 20px;
      }}
      .hair-good {{ background: var(--emerald-soft); border-color: rgba(16, 185, 129, 0.18); }}
      .hair-good::before {{ background: #10b981; }}
      .hair-bad {{ background: var(--rose-soft); border-color: rgba(251, 113, 133, 0.18); }}
      .hair-bad::before {{ background: #f43f5e; }}
      .travel {{ background: var(--cyan-soft); border-color: rgba(34, 211, 238, 0.2); }}
      .travel::before {{ background: #06b6d4; }}
      .list-card {{ padding: 18px 18px; }}
      .good-card {{ margin-top: 0; background: var(--emerald-soft); border-color: rgba(16, 185, 129, 0.16); }}
      .bad-card {{ margin-top: 0; background: var(--amber-soft); border-color: rgba(251, 146, 60, 0.16); }}
      .list-title {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; font-size: 17px; font-weight: 800; }}
      .list-badge {{
        width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center;
        border-radius: 999px; font-size: 16px;
      }}
      .list-badge.good {{ background: rgba(16, 185, 129, 0.12); }}
      .list-badge.bad {{ background: rgba(244, 63, 94, 0.1); }}
      .bullet-list {{ display: grid; gap: 8px; }}
      .list-item {{ display: flex; align-items: flex-start; gap: 8px; }}
      .dot {{ margin-top: 2px; font-size: 14px; line-height: 1; font-weight: 900; }}
      .dot.good {{ color: #059669; }}
      .dot.bad {{ color: #e11d48; }}
      .footer {{ margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(148, 163, 184, 0.14); text-align: center; }}
      .footer p {{ margin: 0; color: #94a3b8; font-size: 9px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.18em; }}
      strong {{ color: #0f172a; }}
    </style>
  </head>
  <body>
    <main class="page">
      <article class="card">
        <div class="content">
          <header>
            <div class="date-chip"><div class="date-chip-value">{_escape(compact_date)}</div></div>
            <h1 class="title">Өдрийн Зурхай</h1>
            <p class="subtitle">{_escape(biligiin_line)}</p>
          </header>

          <section class="hero-grid">
            <section class="overview">
              <div class="icon-box">✨</div>
              <div>
                <h2>Өдрийн ерөнхий төлөв</h2>
                <p>{_escape(general_text)}</p>
                <div class="suudal">Суудал: {_escape(suudal)}</div>
              </div>
            </section>

            <section class="year-grid">
              <div class="year-card">
                <div class="animal">{_escape(favorable_emoji)}</div>
                <div class="label good">Сайн жилтэн</div>
                <div class="year-value">{_escape(", ".join(favorable_years))}</div>
              </div>
              <div class="year-card">
                <div class="animal">{_escape(caution_emoji)}</div>
                <div class="label warn">Болгоомжлох</div>
                <div class="year-value">{_escape(", ".join(caution_years))}</div>
              </div>
            </section>
          </section>

          <section class="detail-grid">
            <div class="panel {hair_panel_class}">
              <div class="panel-head">
                <div class="panel-icon">✂️</div>
                <div>
                  <h3>Үс засуулах: {_escape(hair_status)}</h3>
                  <p>{_escape(hair_text)}</p>
                </div>
              </div>
            </div>
            <div class="panel travel">
              <div class="panel-head">
                <div class="panel-icon">🧭</div>
                <div>
                  <h3>Аян замд гарах: {_escape(travel_status)}</h3>
                  <p>{_escape(travel_text)}</p>
                </div>
              </div>
            </div>
          </section>

          <section class="list-grid">
            <section class="panel list-card good-card">
              <div class="list-title">
                <div class="list-badge good">✓</div>
                <div>Үйл хийхэд сайн</div>
              </div>
              <div class="bullet-list">
                {good_activities_html}
              </div>
            </section>

            <section class="panel list-card bad-card">
              <div class="list-title">
                <div class="list-badge bad">✕</div>
                <div>Цээрлэх зүйлс</div>
              </div>
              <div class="bullet-list">
                {caution_html}
              </div>
            </section>
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
            "--full-page",
            "--viewport-size=720,720",
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
