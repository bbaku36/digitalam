"""AI post generation for each content category."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .constants import MANTRA_LIBRARY_MN, WEEKDAY_MN, ZODIAC_SIGN_DETAILS_MN, ZODIAC_SIGNS_MN
from .http import urlopen_with_retry

MORNING_TERMS = [
    "өглөө",
    "өглөөний",
    "өглөөний мэнд",
    "өглөө мэнд",
]

LAST_AI_STATUS: dict[str, str | bool] = {
    "used_ai": False,
    "provider_used": "",
    "gemini_failed": False,
    "gemini_failure_reason": "",
    "deepseek_failed": False,
    "deepseek_failure_reason": "",
}

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / ".state"
GEMINI_KEY_STATE_FILE = STATE_DIR / "gemini_key_state.json"
APPROVED_MANTRA_LINES = tuple(item[0] for item in MANTRA_LIBRARY_MN)
APPROVED_ZODIAC_SIGNS = tuple(ZODIAC_SIGNS_MN)
BUDDHIST_ALMANAC_CATEGORIES = {"horoscope", "daily_guidance", "weekly", "weekly_horoscope"}
BUDDHIST_ALMANAC_BANNED_PHRASES = (
    "анхилам агаар",
    "ерөнхий зорилго",
    "дэлгэрэнгүй зүйл",
    "өргөн хүрээний аялал",
    "урт хугацааны төлөвлөгөө",
    "оюун санаагаа нэгтгэх",
    "стратеги",
    "фокус",
    "карьер",
    "бизнес",
    "контент",
    "брэнд",
    "төсөл",
    "даалгавар",
    "план",
    "төвд мөрөө",
    "бичиг цаас",
    "хэлэлцээр",
    "гэрээ хийх",
    "засварлах",
)
TRADITIONAL_ALMANAC_MARKERS = (
    "эл өдөр",
    "үс шинээр үргээлгэх",
    "үс засуулбал",
    "үс засуулахад",
    "хол газар",
    "яваар одогсод",
    "мөрөө гаргавал",
    "буян номын",
    "өлзийтэй",
    "цээрлэвэл зохистой",
    "тохиромжгүй",
    "биеэ энхрийлүүштэй",
)
TRADITIONAL_ACTION_WORDS = (
    "буян",
    "ном",
    "маань",
    "засал",
    "ариусгах",
    "тахилга",
    "ерөөл",
)
TRADITIONAL_DIRECTION_WORDS = (
    "зүүн",
    "баруун",
    "урд",
    "өмнө",
    "хойш",
)
DISALLOWED_AFFECTIONATE_TERMS = (
    "хайрт",
    "хонгор",
    "хонгор минь",
    "хайрт минь",
    "хонгорхон",
    "зүрх минь",
)


def _set_last_ai_status(
    *,
    used_ai: bool,
    provider_used: str,
    gemini_failed: bool,
    gemini_failure_reason: str = "",
    deepseek_failed: bool = False,
    deepseek_failure_reason: str = "",
) -> None:
    global LAST_AI_STATUS
    LAST_AI_STATUS = {
        "used_ai": used_ai,
        "provider_used": provider_used,
        "gemini_failed": gemini_failed,
        "gemini_failure_reason": gemini_failure_reason,
        "deepseek_failed": deepseek_failed,
        "deepseek_failure_reason": deepseek_failure_reason,
    }


def get_last_ai_status() -> dict[str, str | bool]:
    return dict(LAST_AI_STATUS)


def _mask_key(value: str) -> str:
    if len(value) <= 12:
        return "***"
    return f"{value[:8]}...{value[-4:]}"


def get_gemini_api_keys() -> list[str]:
    keys: list[str] = []
    raw = os.getenv("GEMINI_API_KEYS", "").strip()
    if raw:
        for part in raw.split(","):
            item = part.strip()
            if item and item not in keys:
                keys.append(item)

    single = os.getenv("GEMINI_API_KEY", "").strip()
    if single and single not in keys:
        keys.append(single)

    for env_name in ("GEMINI_API_KEY_2", "GEMINI_API_KEY2"):
        extra = os.getenv(env_name, "").strip()
        if extra and extra not in keys:
            keys.append(extra)

    return keys


def _load_gemini_next_index(total: int) -> int:
    if total <= 0:
        return 0
    if not GEMINI_KEY_STATE_FILE.exists():
        return 0
    try:
        data = json.loads(GEMINI_KEY_STATE_FILE.read_text(encoding="utf-8"))
        idx = int(data.get("next_index", 0))
        return idx % total
    except Exception:
        return 0


def _save_gemini_next_index(next_index: int) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        GEMINI_KEY_STATE_FILE.write_text(
            json.dumps({"next_index": int(next_index)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _is_rate_limited_http_error(code: int, details: str) -> bool:
    low = details.lower()
    return code == 429 or "too many requests" in low or "resource_exhausted" in low


def apply_time_context(user_prompt: str, slot_hour: int | None) -> str:
    if slot_hour is None:
        return user_prompt

    if slot_hour >= 18:
        return (
            f"{user_prompt} "
            f"Current local time slot is {slot_hour:02d}:00 (evening/night). "
            "Do not use morning greetings or morning wording."
        )
    if slot_hour >= 12:
        return (
            f"{user_prompt} "
            f"Current local time slot is {slot_hour:02d}:00 (afternoon). "
            "Do not use morning greetings or morning wording."
        )
    return (
        f"{user_prompt} "
        f"Current local time slot is {slot_hour:02d}:00 (morning/daytime)."
    )


def violates_time_of_day(text: str, slot_hour: int | None) -> bool:
    if slot_hour is None or slot_hour < 12:
        return False
    lower = text.lower()
    return any(term in lower for term in MORNING_TERMS)


def _has_tibetan_chars(text: str) -> bool:
    return any("\u0F00" <= ch <= "\u0FFF" for ch in text)


def _normalize_mantra_text(text: str) -> str:
    cleaned = re.sub(r"[^А-Яа-яӨөҮүЁёA-Za-z0-9 ]+", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _approved_mantra_set() -> set[str]:
    return {_normalize_mantra_text(line) for line in APPROVED_MANTRA_LINES}


def _approved_mantra_list_text() -> str:
    return "\n".join(f"- {line}" for line in APPROVED_MANTRA_LINES)


def _format_mongolian_day_intro(now_local: str) -> str:
    date_only = now_local.split()[0].strip()
    parsed = datetime.strptime(date_only, "%Y-%m-%d")
    return (
        f"Өнөөдөр {parsed.year} оны {parsed.month} дугаар сарын {parsed.day}, "
        f"{WEEKDAY_MN[parsed.weekday()]} гараг."
    )


def _validate_buddhist_almanac_output(category: str, text: str) -> tuple[bool, str]:
    lower = text.lower()
    non_empty_lines = [line.strip() for line in text.splitlines() if line.strip()]
    first_line = non_empty_lines[0].lower() if non_empty_lines else ""
    if "*" in text:
        return False, "contains_markdown_emphasis"
    for phrase in BUDDHIST_ALMANAC_BANNED_PHRASES:
        if phrase in lower:
            slug = re.sub(r"[^a-z0-9]+", "_", phrase.encode("ascii", "ignore").decode("ascii")).strip("_")
            return False, f"contains_modern_phrase_{slug or 'generic'}"

    heading_map = {
        "horoscope": (
            "өдрийн ерөнхий төлөв",
            "үс засуулах",
            "аян замд гарах",
            "үйл хийхэд сайн",
            "цээрлэх зүйл",
        ),
        "daily_guidance": (
            "үс засуулах",
            "аян замд гарах",
            "үйл хийхэд сайн",
            "цээрлэх зүйл",
        ),
        "weekly": (
            "үс засуулахад сайн өдөр",
            "хол замд гарахад сайн өдөр",
            "үйл хийхэд сайн өдөр",
        ),
        "weekly_horoscope": (
            "ерөнхий чиг",
            "үс засуулахад дөхөм өдөр",
            "аян замд гарахад дөхөм өдөр",
            "үйл хийхэд сайн өдөр",
            "цээрлэх зүйл",
        ),
    }
    for heading in heading_map.get(category, ()):
        if heading not in lower:
            return False, f"missing_heading_{re.sub(r'[^a-z0-9]+', '_', heading.encode('ascii', 'ignore').decode('ascii')).strip('_') or 'section'}"

    if category in {"horoscope", "daily_guidance"}:
        if category == "horoscope":
            if not first_line.startswith("өнөөдөр "):
                return False, "missing_gregorian_intro"
            if "оны" not in first_line or "дугаар сарын" not in first_line or "гараг" not in first_line:
                return False, "invalid_gregorian_intro"
            if any(re.match(r"^\d+\)", line) for line in non_empty_lines):
                return False, "numbered_sections_not_allowed"
        if not any(marker in lower for marker in ("үс шинээр үргээлгэх", "үс засуулбал", "үс засуулахад")):
            return False, "missing_traditional_hair_phrase"
        if not any(marker in lower for marker in ("хол газар", "яваар одогсод", "мөрөө гаргавал")):
            return False, "missing_traditional_travel_phrase"
        if "мөрөө гаргавал" in lower and not any(word in lower for word in TRADITIONAL_DIRECTION_WORDS):
            return False, "missing_direction_for_travel_phrase"
        if not any(word in lower for word in TRADITIONAL_ACTION_WORDS):
            return False, "missing_traditional_action_word"
        if not any(marker in lower for marker in ("эл өдөр", "буян номын", "өлзийтэй")):
            return False, "missing_traditional_day_phrase"

    marker_hits = sum(1 for marker in TRADITIONAL_ALMANAC_MARKERS if marker in lower)
    required_marker_hits = 3
    if category in {"weekly", "weekly_horoscope"}:
        required_marker_hits = 2
    if marker_hits < required_marker_hits:
        return False, "missing_traditional_almanac_tone"

    return True, ""


def _validate_zodiac_horoscope_output(text: str) -> tuple[bool, str]:
    lower = text.lower()
    if "12 орд" not in lower and "ордын зурхай" not in lower:
        return False, "missing_zodiac_title"
    non_empty_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(non_empty_lines) < 15:
        return False, "zodiac_post_too_short"
    first_line = non_empty_lines[0].lower()
    if "12 орд" not in first_line and "ордын зурхай" not in first_line:
        return False, "missing_zodiac_title_line"
    if any("өдрийн ерөнхий төлөв" in line.lower() for line in non_empty_lines):
        return False, "old_zodiac_format_detected"

    heading_lines = 0
    for sign, (symbol, label, date_range) in zip(APPROVED_ZODIAC_SIGNS, ZODIAC_SIGN_DETAILS_MN):
        accepted_headings = (
            f"{symbol} {label} ({date_range})",
            f"{symbol} {sign} ({date_range})",
        )
        if not any(heading in text for heading in accepted_headings):
            return False, f"missing_heading_{label}"
        heading_lines += 1
    if heading_lines != len(ZODIAC_SIGN_DETAILS_MN):
        return False, "invalid_sign_heading_count"

    return True, ""


def _validate_category_output(category: str, text: str) -> tuple[bool, str]:
    lower = text.lower()
    for term in DISALLOWED_AFFECTIONATE_TERMS:
        if term in lower:
            slug = re.sub(r"[^a-z0-9]+", "_", term.encode("ascii", "ignore").decode("ascii")).strip("_")
            return False, f"contains_affectionate_term_{slug or 'generic'}"

    if category in BUDDHIST_ALMANAC_CATEGORIES:
        return _validate_buddhist_almanac_output(category, text)
    if category == "zodiac_horoscope":
        return _validate_zodiac_horoscope_output(text)

    if category != "mantra":
        return True, ""

    if _has_tibetan_chars(text):
        return False, "contains_tibetan_script"
    if "тайлбар" not in text.lower():
        return False, "missing_explanation_section"

    numbered_lines = re.findall(r"(?m)^\s*\d+\.\s+(.+)$", text)
    if len(numbered_lines) != 3:
        return False, "missing_numbered_mantra_lines"

    allowed = _approved_mantra_set()
    for line in numbered_lines:
        norm = _normalize_mantra_text(line)
        if norm not in allowed:
            return False, "non_canonical_mantra_line"

    explanation_count = len(re.findall(r"(?im)^\s*тайлбар\s*:", text))
    if explanation_count < 3:
        return False, "missing_explanation_for_each_mantra"

    return True, ""


def _temperature_for_category(category: str) -> float:
    if category == "mantra":
        return 0.35
    if category in BUDDHIST_ALMANAC_CATEGORIES:
        return 0.25
    if category in {"insight", "evening_insight", "tomorrow_prep"}:
        return 0.65
    return 0.55


def _variation_seed() -> str:
    explicit = os.getenv("POST_VARIATION_SEED", "").strip()
    if explicit:
        return explicit
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")


def _append_variation_seed(user_prompt: str) -> str:
    seed = _variation_seed()
    return f"{user_prompt} Unique variation seed: {seed}. Do not print this seed in output."


def _apply_elder_voice_style(system_prompt: str, user_prompt: str) -> tuple[str, str]:
    system_suffix = (
        " Voice and persona: sound like a very wise Mongolian elder speaking with calm authority, "
        "lived experience, restraint, and benevolent warmth. The writing should feel seasoned and "
        "trustworthy, not hype-driven, salesy, childish, or generic. "
        "Never address the reader with romantic or overly intimate pet names such as 'хайрт', 'хонгор', or similar language."
    )
    user_suffix = (
        " The voice must feel like a sharp, perceptive Mongolian elder giving measured guidance. "
        "Avoid slang, clickbait, exaggerated mysticism, empty motivational filler, and romantic/intimate forms of address."
    )
    return f"{system_prompt}{system_suffix}", f"{user_prompt}{user_suffix}"


def _append_source_context(user_prompt: str, source_context: str | None) -> str:
    if not source_context:
        return user_prompt
    return (
        f"{user_prompt}\n\n"
        "Use the following source facts as input. Preserve factual details, but rewrite in fresh wording "
        "and do not copy long sentences verbatim.\n"
        f"{source_context}"
    )


def _build_mantra_repair_prompts(now_local: str, validation_reason: str, previous_text: str) -> tuple[str, str]:
    system_prompt = (
        "You are a Mongolian spiritual content writer. "
        "Return ONLY a Mongolian Facebook post with strict formatting. "
        "Do not use Tibetan script. Use Mongolian Cyrillic transliteration only. "
        "Use ONLY mantra lines from the approved list, spelling must be exact."
    )
    trimmed = previous_text.strip()
    if len(trimmed) > 900:
        trimmed = trimmed[:900]
    approved_list = _approved_mantra_list_text()
    user_prompt = (
        f"Rewrite the mantra post for {now_local}. Previous draft failed with reason: {validation_reason}. "
        "Choose exactly 3 mantra lines from this approved list and keep spelling unchanged:\n"
        f"{approved_list}\n\n"
        "Required output format:\n"
        "Өдрийн маань, тарни ба төвлөрөл (...)\n"
        "\n"
        "Өнөөдрийн тарни (Монгол крилл галиг):\n"
        "1. [approved mantra]\n"
        "Тайлбар: ...\n"
        "\n"
        "2. [approved mantra]\n"
        "Тайлбар: ...\n"
        "\n"
        "3. [approved mantra]\n"
        "Тайлбар: ...\n"
        "\n"
        "Өнөөдрийн 3 практик алхам:\n"
        "1) ...\n"
        "2) ...\n"
        "3) ...\n"
        "\n"
        "#Маань #Тарни #Бясалгал #DigitalLam\n"
        "\n"
        "Bad previous draft (for fixing):\n"
        f"{trimmed}\n"
    )
    return system_prompt, _append_variation_seed(user_prompt)


def _build_buddhist_almanac_repair_prompts(
    category: str,
    now_local: str,
    validation_reason: str,
    previous_text: str,
) -> tuple[str, str]:
    system_prompt = (
        "You are a Mongolian Buddhist almanac writer. "
        "Return ONLY a Mongolian Facebook post in terse, formulaic Mongolian bilgiin toolol diction. "
        "Do not use modern self-help, business, planning, coaching, or motivational language. "
        "Use plain text only. Do not use markdown emphasis, asterisks, bullets, or decorative formatting. "
        "Prefer terse traditional phrasing such as: "
        "'Эл өдөр ...', "
        "'Үс шинээр үргээлгэх буюу засуулахад ...', "
        "'Хол газар яваар одогсод ... мөрөө гаргавал ...', "
        "'Эл өдөр ... үйлд сайн.', "
        "'... үйл цээрлэвэл зохистой.'"
    )
    trimmed = previous_text.strip()
    if len(trimmed) > 900:
        trimmed = trimmed[:900]

    required_formats = {
        "horoscope": (
            "Өнөөдөр 2026 оны 3 дугаар сарын 14, Бямба гараг.\n"
            "Өнөөдрийн үс засуулах, аян зам, үйл хийхийн зурхайг доор сийрүүлье:\n"
            "🌿 Өдрийн ерөнхий төлөв\n"
            "Эл өдөр ...\n"
            "✂️ Үс засуулах тохиромж\n"
            "Үс шинээр үргээлгэх буюу засуулахад ...\n"
            "🛣️ Аян замд гарах\n"
            "Хол газар яваар одогсод зүүн, баруун, урд, өмнө, эсвэл хойш мөрөө гаргавал ...\n"
            "📿 Үйл хийхэд сайн\n"
            "Эл өдөр ... үйлд сайн.\n"
            "⚠️ Цээрлэх зүйл\n"
            "... үйл цээрлэвэл зохистой.\n"
            "Тэмдэглэл: Энэ нь уламжлалт, ерөнхий чиглүүлэг.\n"
            "#ӨдрийнЗурхай #ҮсЗасуулах #АянЗам #DigitalLam"
        ),
        "daily_guidance": (
            "Өдрийн үйл, шарын шашны чиглүүлэг (...)\n"
            "Үс засуулах: Үс шинээр үргээлгэх буюу засуулахад ...\n"
            "Аян замд гарах: Хол газар яваар одогсод зүүн, баруун, урд, өмнө, эсвэл хойш мөрөө гаргавал ...\n"
            "Үйл хийхэд сайн: Эл өдөр ... үйлд сайн.\n"
            "Цээрлэх зүйл: ... үйл цээрлэвэл зохистой.\n"
            "Тэмдэглэл: Энэ нь уламжлалт, ерөнхий чиглүүлэг.\n"
            "#ШарынШашныЗурхай #ӨдрийнЗурхай #ҮсЗасуулах #АянЗам #DigitalLam"
        ),
        "weekly": (
            "7 хоногийн чиглүүлэг (...)\n"
            "Үс засуулахад сайн өдөр: ...\n"
            "Хол замд гарахад сайн өдөр: ...\n"
            "Үйл хийхэд сайн өдөр: ...\n"
            "Тэмдэглэл: Энэ нь уламжлалт, ерөнхий чиглүүлэг.\n"
            "#ШарынШашныЗурхай ..."
        ),
        "weekly_horoscope": (
            "7 хоногийн шарын шашны зурхай (...)\n"
            "Ерөнхий чиг: Эл 7 хоногт ... өлзийтэй.\n"
            "Үс засуулахад дөхөм өдөр: Үс засуулахад ...\n"
            "Аян замд гарахад дөхөм өдөр: Хол газар яваар одогсод ... мөрөө гаргавал ...\n"
            "Үйл хийхэд сайн өдөр: Буян номын ... үйлд сайн.\n"
            "Цээрлэх зүйл: ... үйл цээрлэвэл зохистой.\n"
            "Тэмдэглэл: Энэ нь уламжлалт, ерөнхий чиглүүлэг.\n"
            "#ШарынШашныЗурхай ..."
        ),
    }
    user_prompt = (
        f"Rewrite the {category} post for {now_local}. Previous draft failed with reason: {validation_reason}. "
        "Use strict Mongolian Buddhist almanac phrasing. "
        "Use plain text only. Do not use markdown emphasis or asterisks anywhere. "
        "Forbidden words and tone: зорилго, төлөвлөгөө, стратеги, фокус, анхилам агаар, өргөн хүрээний аялал, урт хугацааны төлөвлөгөө, бичиг цаас, хэлэлцээр, гэрээ хийх, coaching-style explanation. "
        "Prefer traditional religious acts such as буян ном, маань тарни, засал, ариусгах, тахилга, ерөөл. "
        "Keep each section to one sentence maximum and do not explain the reasoning. "
        "Required output pattern:\n"
        f"{required_formats.get(category, '')}\n\n"
        "Bad previous draft (for fixing):\n"
        f"{trimmed}\n"
    )
    return system_prompt, _append_variation_seed(user_prompt)


def _build_zodiac_repair_prompts(
    now_local: str,
    validation_reason: str,
    previous_text: str,
) -> tuple[str, str]:
    system_prompt = (
        "You are a Mongolian daily zodiac horoscope editor. "
        "Return ONLY a Mongolian Facebook post in clean plain text. "
        "Keep the exact 12-sign structure and exact sign heading order. "
        "Never address the reader with affectionate or intimate pet names such as "
        "'хайрт', 'хонгор', 'хонгор минь', 'хайрт минь', 'хонгорхон', or 'зүрх минь'. "
        "Do not switch to Buddhist almanac language."
    )
    trimmed = previous_text.strip()
    if len(trimmed) > 1200:
        trimmed = trimmed[:1200]
    user_prompt = (
        f"Rewrite today's 12-sign zodiac horoscope for {now_local}. "
        f"Previous draft failed with reason: {validation_reason}. "
        "Keep the exact title format '12 ордын зурхай (YYYY-MM-DD)'. "
        "Keep exactly these 12 headings in this exact order and exact spelling:\n"
        "♈ Хонины орд (3/21 - 4/19)\n"
        "♉ Үхрийн орд (4/20 - 5/20)\n"
        "♊ Ихрийн орд (5/21 - 6/21)\n"
        "♋ Мэлхийн орд (6/22 - 7/22)\n"
        "♌ Арслангийн орд (7/23 - 8/22)\n"
        "♍ Охины орд (8/23 - 9/22)\n"
        "♎ Жинлүүрийн орд (9/23 - 10/23)\n"
        "♏ Хилэнцийн орд (10/24 - 11/21)\n"
        "♐ Нумын орд (11/22 - 12/21)\n"
        "♑ Матрын орд (12/22 - 1/19)\n"
        "♒ Хумхын орд (1/20 - 2/18)\n"
        "♓ Загасны орд (2/19 - 3/20)\n"
        "Remove any affectionate direct address and keep the tone neutral, clean, and editorial. "
        "Each sign must have a 2-3 sentence paragraph under its heading. "
        "End with a short disclaimer and exactly these hashtags: #12Орд #ӨдрийнЗурхай #ОрдныЗурхай #DigitalLam\n\n"
        "Bad previous draft (for fixing):\n"
        f"{trimmed}\n"
    )
    return system_prompt, _append_variation_seed(user_prompt)


def build_prompts(
    category: str,
    now_local: str,
    slot_hour: int | None = None,
    source_context: str | None = None,
) -> tuple[str, str] | None:
    if category == "insight":
        system_prompt = (
            "You are a Mongolian spiritual writer. Write a concise Facebook post with "
            "4-6 short insight and motivation lines in Mongolian. Tone should be warm, "
            "grounded, and practical, not preachy. Avoid medical, legal, or financial "
            "advice. End with 3-4 relevant hashtags."
        )
        user_prompt = (
            f"Generate today's insight and motivational quote post for {now_local}. "
            "Format as a short intro and numbered list."
        )
    elif category == "horoscope":
        day_intro = _format_mongolian_day_intro(now_local)
        system_prompt = (
            "You are a Mongolian Buddhist almanac-style writer. "
            "Write a concise Facebook post in Mongolian in the style of traditional Mongolian Yellow Buddhism daily guidance. "
            "Do not use Western zodiac signs, Chinese zodiac animals, birth years, or 12-sign readings. "
            "Open with a Gregorian date sentence in Mongolian, then a short lead-in sentence, then use exactly these section headings: "
            "1) '🌿 Өдрийн ерөнхий төлөв', "
            "2) '✂️ Үс засуулах тохиромж', "
            "3) '🛣️ Аян замд гарах', "
            "4) '📿 Үйл хийхэд сайн', "
            "5) '⚠️ Цээрлэх зүйл'. "
            "Use concise, seasoned almanac diction with a little more explanation than a one-line calendar note, but keep it compact. "
            "Prefer phrasing patterns like 'Эл өдөр ...', 'Үс шинээр үргээлгэх буюу засуулахад ...', "
            "'Хол газар яваар одогсод ... мөрөө гаргавал ...', 'Эл өдөр ... үйлд сайн.', "
            "'... үйл цээрлэвэл зохистой.' "
            "Do not use modern self-help or productivity language such as зорилго, төлөвлөгөө, стратеги, фокус, анхилам агаар, өргөн хүрээний аялал. "
            "The travel line must include a real direction word before 'мөрөө гаргавал', such as зүүн, баруун, урд, өмнө, or хойш. "
            "Do not number the sections. The headings should appear exactly as plain emoji-plus-title lines. "
            "Use plain text only, no markdown emphasis. "
            "If source facts are provided, use them as the factual basis for the biligiin line, haircut meaning, travel direction, good activities, and caution items. "
            "Keep it practical, restrained, and respectful. Avoid fear tactics and any medical, legal, or financial advice."
        )
        user_prompt = (
            f"Generate today's Mongolian Buddhist-style daily guidance post for {now_local}. "
            f"The first line must be exactly: {day_intro} "
            "If source facts are provided, the second non-empty line should begin with 'Билгийн тооллын' and summarize the supplied biligiin information in one sentence. "
            "Then add the exact line 'Өнөөдрийн үс засуулах, аян зам, үйл хийхийн зурхайг доор сийрүүлье:' "
            "Each section should contain 1-2 short sentences only. "
            "Do not use any numbering like '1)' or '2)' before the section headings. "
            "The hair section must use traditional wording around 'Үс шинээр үргээлгэх буюу засуулахад ...'. "
            "The travel section must mention 'Хол газар яваар одогсод ... мөрөө гаргавал ...' and include a real direction word such as зүүн, баруун, урд, өмнө, or хойш. "
            "The action section must say 'Эл өдөр ... үйлд сайн.' and should prefer traditional religious acts such as буян ном, маань тарни, засал, ариусгах, тахилга, ерөөл. "
            "The caution section must end in a traditional warning such as '... үйл цээрлэвэл зохистой.' "
            "Finish with a short plain-text disclaimer and exactly these hashtags: #ӨдрийнЗурхай #ҮсЗасуулах #АянЗам #DigitalLam"
        )
    elif category == "zodiac_horoscope":
        system_prompt = (
            "You are a Mongolian daily zodiac horoscope writer. "
            "Write a Facebook post in Mongolian for exactly these 12 zodiac signs only: "
            f"{', '.join(APPROVED_ZODIAC_SIGNS)}. "
            "Do not use Chinese zodiac animals or Buddhist almanac language. "
            "Use this structure exactly: "
            "1) title, "
            "2) one short introductory paragraph about the day's overall astrological mood, "
            "3) 12 sign sections in the same order as listed above, "
            "4) one short disclaimer, "
            "5) hashtags. "
            "Each sign section must have a heading line with the zodiac symbol, Mongolian sign label, and date range, "
            "followed by a short paragraph of 2-3 sentences. "
            "The tone should feel like a polished Mongolian Facebook horoscope post: readable, specific, and slightly editorial, not mystical nonsense. "
            "If source facts are provided, keep each sign aligned with its supplied GoGo meaning, but rewrite the wording instead of copying it. "
            "Avoid medical, legal, or financial guarantees."
        )
        user_prompt = (
            f"Generate today's 12-sign zodiac horoscope post for {now_local}. "
            "Open with the exact title '12 ордын зурхай (YYYY-MM-DD)' using the actual local date. "
            "Then write one short intro paragraph summarizing the day's general tendency across most signs. "
            "After that, include exactly these 12 sign sections in this exact order and exact heading format:\n"
            "♈ Хонины орд (3/21 - 4/19)\n"
            "♉ Үхрийн орд (4/20 - 5/20)\n"
            "♊ Ихрийн орд (5/21 - 6/21)\n"
            "♋ Мэлхийн орд (6/22 - 7/22)\n"
            "♌ Арслангийн орд (7/23 - 8/22)\n"
            "♍ Охины орд (8/23 - 9/22)\n"
            "♎ Жинлүүрийн орд (9/23 - 10/23)\n"
            "♏ Хилэнцийн орд (10/24 - 11/21)\n"
            "♐ Нумын орд (11/22 - 12/21)\n"
            "♑ Матрын орд (12/22 - 1/19)\n"
            "♒ Хумхын орд (1/20 - 2/18)\n"
            "♓ Загасны орд (2/19 - 3/20)\n"
            "Each sign must have its heading on one line and a 2-3 sentence paragraph underneath. "
            "Do not use bullet points or numbering. "
            "If source facts are provided, use them as the factual basis for each sign paragraph. You may keep the tone editorial and clean, but do not drift away from the supplied source meaning. "
            "You may mention broad themes like responsibility, money, relationships, creativity, or timing, but avoid fake precision or risky claims. "
            "Finish with a short disclaimer and exactly these hashtags: #12Орд #ӨдрийнЗурхай #ОрдныЗурхай #DigitalLam"
        )
    elif category == "daily_guidance":
        system_prompt = (
            "You are a Mongolian Buddhist daily guidance writer. "
            "Write a concise Facebook post in Mongolian with these sections: "
            "1) 'Үс засуулах', "
            "2) 'Аян замд гарах', "
            "3) 'Үйл хийхэд сайн', "
            "4) 'Цээрлэх зүйл'. "
            "The style must sound like traditional Mongolian Yellow Buddhist day guidance. "
            "Use terse, formulaic almanac diction. Prefer phrases such as 'Үс шинээр үргээлгэх буюу засуулахад ...', "
            "'Хол газар яваар одогсод ... мөрөө гаргавал ...', 'Эл өдөр ... үйлд сайн.', "
            "'... үйл цээрлэвэл зохистой.' "
            "Action suggestions should prefer traditional religious acts such as буян ном, маань тарни, засал, ариусгах, тахилга, ерөөл. "
            "Do not use modern self-help or productivity language such as зорилго, төлөвлөгөө, стратеги, фокус, анхилам агаар, бичиг цаас, хэлэлцээр, гэрээ хийх. "
            "Keep it practical and traditional, avoid fear language, wild mystical claims, and risky advice."
        )
        user_prompt = (
            f"Generate today's guidance post for {now_local}. "
            "Include a short intro, the 4 required sections, one short closing line, a brief disclaimer that it is traditional general guidance, and 4-5 hashtags. "
            "Each section must be one sentence maximum. The travel section should use a real direction word if it mentions 'мөрөө гаргавал'."
        )
    elif category == "mantra":
        approved_list = _approved_mantra_list_text()
        system_prompt = (
            "You are a Mongolian spiritual content writer. "
            "Write a daily mantra and meditation Facebook post in Mongolian. "
            "Mantras must be written only in Mongolian Cyrillic transliteration, not Tibetan script. "
            "Use ONLY mantra lines from the approved list below, spelling must be exact. "
            "Use this structure exactly: "
            "1) section title for mantra lines, "
            "2) include exactly 3 numbered mantra lines, each matching one approved mantra, "
            "3) each mantra line followed by a Mongolian explanation line starting with 'Тайлбар:', "
            "4) a short 3-minute calmness practice, "
            "5) closing hashtags.\n"
            "Approved mantra list:\n"
            f"{approved_list}"
        )
        user_prompt = (
            f"Generate today's mantra post for {now_local}. "
            "Pick exactly 3 mantra lines from the approved list and keep their spelling unchanged. "
            "Do not include any Tibetan script characters."
        )
    elif category == "messenger_cta":
        system_prompt = (
            "You are a Mongolian social media copywriter for a spiritual service page. "
            "Write a short CTA post in Mongolian inviting users to anonymously share confession-like "
            "thoughts, regrets, or emotional burdens through Messenger. "
            "The tone must be gentle, non-judgmental, and confidential. "
            "Ask users to start the message with one trigger word and mention that names are optional."
        )
        user_prompt = (
            f"Generate today's anonymous Messenger CTA post for {now_local}. "
            "Include: short opening, confidentiality note, clear trigger keyword, and short disclaimer "
            "that responses are traditional/spiritual guidance."
        )
    elif category == "evening_insight":
        system_prompt = (
            "You are a Mongolian evening reflection writer. "
            "Write a short evening wisdom post in Mongolian with 3-4 concise lines "
            "for reflection and calmness. End with hashtags."
        )
        user_prompt = f"Generate tonight's evening insight post for {now_local}."
    elif category == "tomorrow_prep":
        system_prompt = (
            "You are a Mongolian evening routine writer. "
            "Write a short Facebook post in Mongolian for late evening, around 22:00. "
            "The post must sound like something to read before sleep: calm, practical, and settled. "
            "Focus on what to prepare tonight for tomorrow, not what to do in the morning. "
            "Use 3 short parts: "
            "1) one line to slow down and close the day, "
            "2) one practical line about preparing tonight for tomorrow, "
            "3) one short blessing line. "
            "Do not use morning greetings, morning mood, or phrases about waking up. "
            "Avoid the words 'өглөө', 'өглөөний', 'өглөө босоод'. "
            "Keep it concise and warm."
        )
        user_prompt = (
            f"Generate tonight's tomorrow-prep post for {now_local}. "
            "It should read like a 22:00 post before sleep. "
            "Mention one small thing to prepare tonight, such as clothes, notes, bag, desk, or priorities for tomorrow. "
            "Do not mention morning, waking up, or early hours. "
            "End with 2-3 hashtags."
        )
    elif category == "goodnight":
        system_prompt = (
            "You are a Mongolian spiritual page writer. "
            "Write a very short goodnight post in Mongolian with calm tone, "
            "a single intention line for restful sleep, and 2-3 hashtags."
        )
        user_prompt = f"Generate tonight's short goodnight post for {now_local}."
    elif category == "fact":
        system_prompt = (
            "You are a Mongolian Buddhist educator writing for a Facebook page. "
            "Write a concise evening Facebook post of interesting, verifiable religion/Buddhist facts. "
            "This post is for around 18:00, so the tone should feel like an early-evening reading post, not a morning greeting. "
            "Include 4-6 short facts, keep tone respectful and practical, and avoid "
            "controversial claims that require deep citation. Do not include medical, "
            "legal, or financial advice. Do not use morning greetings or the words 'өглөө', 'өглөөний', 'өглөөний мэнд'. "
            "End with 3-4 hashtags."
        )
        user_prompt = (
            f"Generate today's interesting religion facts post for {now_local} in Mongolian. "
            "It should read naturally for the 18:00 time slot. "
            "Format as a short evening intro and a numbered list. "
            "Do not greet the reader as if it were morning."
        )
    elif category == "weekly":
        system_prompt = (
            "You are a Mongolian spiritual calendar writer. Create one weekly pinned post "
            "in Mongolian with these exact sections: "
            "1) 'Үс засуулахад сайн өдөр', "
            "2) 'Хол замд гарахад сайн өдөр', "
            "3) 'Үйл хийхэд сайн өдөр'. "
            "Each section must include one weekday and one short practical note. "
            "The tone should match traditional Mongolian Yellow Buddhist guidance and terse bilgiin toolol diction. "
            "Do not use modern coaching, planning, or motivational language. "
            "Add 2-3 supportive lines, a short disclaimer that it is traditional general guidance, and hashtags. Keep it concise and respectful."
        )
        user_prompt = (
            f"Generate this week's pinned guidance post for {now_local}. "
            "Include the 3 required weekday sections and keep the language practical and seasoned."
        )
    elif category == "weekly_horoscope":
        system_prompt = (
            "You are a Mongolian Buddhist weekly almanac writer. "
            "Write a weekly Facebook post in Mongolian in the style of traditional Mongolian Yellow Buddhism guidance. "
            "Do not use Western zodiac signs, Chinese zodiac animals, birth years, or 12-sign readings. "
            "Include these sections exactly once: "
            "1) 'Ерөнхий чиг', "
            "2) 'Үс засуулахад дөхөм өдөр', "
            "3) 'Аян замд гарахад дөхөм өдөр', "
            "4) 'Үйл хийхэд сайн өдөр', "
            "5) 'Цээрлэх зүйл'. "
            "Use terse, formulaic almanac diction and avoid modern self-help language. "
            "Prefer phrases such as 'Эл 7 хоногт ... өлзийтэй.', 'Хол газар яваар одогсод ... мөрөө гаргавал ...', "
            "'Буян номын ... үйлд сайн.', and '... үйл цээрлэвэл зохистой.' "
            "Use plain text only, no markdown emphasis, no asterisks. "
            "Keep it concise, practical, respectful, and free of medical, legal, or financial guarantees."
        )
        user_prompt = (
            f"Generate this week's Mongolian Buddhist-style weekly guidance post for {now_local}. "
            "Include a title with the week range, the 5 required sections, a short disclaimer that it is traditional general guidance, and 4-5 hashtags. "
            "Use plain text only and do not add markdown emphasis or asterisks. "
            "Make sure the body includes at least a few traditional phrases like өлзийтэй, буян номын, хол газар яваар одогсод, мөрөө гаргавал, эсвэл цээрлэвэл зохистой."
        )
    else:
        return None

    return _apply_elder_voice_style(
        system_prompt,
        _append_variation_seed(
            _append_source_context(
                apply_time_context(user_prompt, slot_hour),
                source_context,
            )
        ),
    )


def call_openai(
    system_prompt: str,
    user_prompt: str,
    category: str,
    timeout_sec: int,
    temperature: float = 0.4,
) -> tuple[str | None, str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None, "missing_openai_api_key"

    model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
    url = f"{base_url}/chat/completions"

    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urlopen_with_retry(req, timeout_sec, f"OpenAI {category} post request") as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if content:
            return content, ""
        return None, "openai_empty_content"
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        print(f"[WARN] OpenAI {category} HTTP error: {details}")
        return None, f"openai_http_error_{exc.code}"
    except Exception as exc:
        return None, f"openai_exception_{type(exc).__name__}"


def call_deepseek(
    system_prompt: str,
    user_prompt: str,
    category: str,
    timeout_sec: int,
    temperature: float = 0.4,
) -> tuple[str | None, str]:
    """Call DeepSeek API (OpenAI-compatible format)."""
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return None, "missing_deepseek_api_key"

    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").strip().rstrip("/")
    url = f"{base_url}/chat/completions"
    timeout_override_raw = os.getenv(
        "DEEPSEEK_TIMEOUT_SEC",
        "120" if model == "deepseek-reasoner" else "90",
    ).strip()
    max_tokens_raw = os.getenv(
        "DEEPSEEK_MAX_TOKENS",
        "1800" if model == "deepseek-reasoner" else "1400",
    ).strip()
    try:
        request_timeout_sec = max(1, int(timeout_override_raw))
    except ValueError:
        request_timeout_sec = 120 if model == "deepseek-reasoner" else 90
    try:
        max_tokens = max(256, int(max_tokens_raw))
    except ValueError:
        max_tokens = 1800 if model == "deepseek-reasoner" else 1400

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
    }
    if model != "deepseek-reasoner":
        payload["temperature"] = temperature
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urlopen_with_retry(req, request_timeout_sec, f"DeepSeek {category} post request") as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if content:
            return content, ""
        return None, "deepseek_empty_content"
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        print(f"[WARN] DeepSeek {category} HTTP error: {details}")
        return None, f"deepseek_http_error_{exc.code}"
    except Exception as exc:
        return None, f"deepseek_exception_{type(exc).__name__}"


def call_gemini(
    system_prompt: str,
    user_prompt: str,
    category: str,
    timeout_sec: int,
    temperature: float = 0.4,
) -> tuple[str | None, str]:
    api_keys = get_gemini_api_keys()
    if not api_keys:
        return None, "missing_gemini_api_key"

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").strip().rstrip("/")
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}],
            }
        ],
        "generationConfig": {
            "temperature": temperature,
        },
    }

    total = len(api_keys)
    start_index = _load_gemini_next_index(total)
    reasons: list[str] = []

    for offset in range(total):
        key_index = (start_index + offset) % total
        api_key = api_keys[key_index]
        url = f"{base_url}/models/{model}:generateContent?key={api_key}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urlopen_with_retry(
                req,
                timeout_sec,
                f"Gemini {category} post request (key {key_index + 1}/{total})",
            ) as response:
                raw = response.read().decode("utf-8")
            data = json.loads(raw)
            candidates = data.get("candidates") or []
            if not candidates:
                reasons.append(f"gemini_empty_candidates_k{key_index + 1}")
                continue

            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
            if not text:
                reasons.append(f"gemini_empty_text_k{key_index + 1}")
                continue

            # True round-robin start point for next run, independent of which key succeeded.
            next_index = (start_index + 1) % total
            _save_gemini_next_index(next_index)
            if total > 1:
                print(
                    f"[INFO] Gemini key {key_index + 1}/{total} succeeded "
                    f"({_mask_key(api_key)}). Next run starts at key {next_index + 1}/{total}."
                )
            return text, ""
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            if _is_rate_limited_http_error(exc.code, details):
                reason = f"gemini_rate_limited_k{key_index + 1}"
                print(
                    f"[WARN] Gemini key {key_index + 1}/{total} rate-limited "
                    f"({_mask_key(api_key)}), switching key."
                )
            else:
                reason = f"gemini_http_error_{exc.code}_k{key_index + 1}"
                print(f"[WARN] Gemini {category} HTTP error on key {key_index + 1}/{total}: {details}")
            reasons.append(reason)
            continue
        except Exception as exc:
            reasons.append(f"gemini_exception_{type(exc).__name__}_k{key_index + 1}")
            continue

    _save_gemini_next_index((start_index + 1) % max(1, total))
    return None, ";".join(reasons) if reasons else "gemini_all_keys_failed"


def ai_generate_generic_post(
    category: str,
    now_local: str,
    timeout_sec: int = 40,
    slot_hour: int | None = None,
    source_context: str | None = None,
) -> str | None:
    prompts = build_prompts(category, now_local, slot_hour, source_context=source_context)
    if not prompts:
        _set_last_ai_status(
            used_ai=False,
            provider_used="",
            gemini_failed=False,
            gemini_failure_reason="no_prompt_for_category",
        )
        return None
    system_prompt, user_prompt = prompts
    temperature = _temperature_for_category(category)

    provider = os.getenv("AI_PROVIDER", "").strip().lower()
    if provider == "gemini":
        result, reason = call_gemini(system_prompt, user_prompt, category, timeout_sec, temperature)
        if result and violates_time_of_day(result, slot_hour):
            print(f"[WARN] Rejected {category} AI text due to morning wording in {slot_hour}:00 slot")
            _set_last_ai_status(
                used_ai=False,
                provider_used="gemini",
                gemini_failed=True,
                gemini_failure_reason="time_guard_rejected",
            )
            return None
        if result:
            valid, validation_reason = _validate_category_output(category, result)
            if not valid:
                print(f"[WARN] Rejected {category} AI text due to format guard: {validation_reason}")
                if category == "mantra":
                    repair_system, repair_user = _build_mantra_repair_prompts(
                        now_local=now_local,
                        validation_reason=validation_reason,
                        previous_text=result,
                    )
                    retry_result, retry_reason = call_gemini(
                        repair_system,
                        repair_user,
                        category,
                        timeout_sec,
                        temperature,
                    )
                    if retry_result:
                        retry_valid, retry_validation_reason = _validate_category_output(
                            category,
                            retry_result,
                        )
                        if retry_valid and not violates_time_of_day(retry_result, slot_hour):
                            _set_last_ai_status(
                                used_ai=True,
                                provider_used="gemini",
                                gemini_failed=False,
                                gemini_failure_reason="",
                            )
                            return retry_result
                        if not retry_valid:
                            validation_reason = retry_validation_reason
                        else:
                            validation_reason = "time_guard_rejected"
                    elif retry_reason:
                        validation_reason = retry_reason
                elif category in BUDDHIST_ALMANAC_CATEGORIES:
                    repair_system, repair_user = _build_buddhist_almanac_repair_prompts(
                        category=category,
                        now_local=now_local,
                        validation_reason=validation_reason,
                        previous_text=result,
                    )
                    retry_result, retry_reason = call_gemini(
                        repair_system,
                        repair_user,
                        category,
                        timeout_sec,
                        temperature,
                    )
                    if retry_result:
                        retry_valid, retry_validation_reason = _validate_category_output(
                            category,
                            retry_result,
                        )
                        if retry_valid and not violates_time_of_day(retry_result, slot_hour):
                            _set_last_ai_status(
                                used_ai=True,
                                provider_used="gemini",
                                gemini_failed=False,
                                gemini_failure_reason="",
                            )
                            return retry_result
                        if not retry_valid:
                            validation_reason = retry_validation_reason
                        else:
                            validation_reason = "time_guard_rejected"
                    elif retry_reason:
                        validation_reason = retry_reason
                elif category == "zodiac_horoscope":
                    repair_system, repair_user = _build_zodiac_repair_prompts(
                        now_local=now_local,
                        validation_reason=validation_reason,
                        previous_text=result,
                    )
                    retry_result, retry_reason = call_gemini(
                        repair_system,
                        repair_user,
                        category,
                        timeout_sec,
                        temperature,
                    )
                    if retry_result:
                        retry_valid, retry_validation_reason = _validate_category_output(
                            category,
                            retry_result,
                        )
                        if retry_valid and not violates_time_of_day(retry_result, slot_hour):
                            _set_last_ai_status(
                                used_ai=True,
                                provider_used="gemini",
                                gemini_failed=False,
                                gemini_failure_reason="",
                            )
                            return retry_result
                        if not retry_valid:
                            validation_reason = retry_validation_reason
                        else:
                            validation_reason = "time_guard_rejected"
                    elif retry_reason:
                        validation_reason = retry_reason
                _set_last_ai_status(
                    used_ai=False,
                    provider_used="gemini",
                    gemini_failed=True,
                    gemini_failure_reason=validation_reason,
                )
                return None
        if result:
            _set_last_ai_status(
                used_ai=True,
                provider_used="gemini",
                gemini_failed=False,
                gemini_failure_reason="",
            )
            return result
        _set_last_ai_status(
            used_ai=False,
            provider_used="gemini",
            gemini_failed=True,
            gemini_failure_reason=reason or "gemini_unknown_error",
        )
        return result
    if provider == "openai":
        result, reason = call_openai(system_prompt, user_prompt, category, timeout_sec, temperature)
        if result and violates_time_of_day(result, slot_hour):
            print(f"[WARN] Rejected {category} AI text due to morning wording in {slot_hour}:00 slot")
            _set_last_ai_status(
                used_ai=False,
                provider_used="openai",
                gemini_failed=False,
                gemini_failure_reason="time_guard_rejected",
            )
            return None
        if result:
            valid, validation_reason = _validate_category_output(category, result)
            if not valid:
                print(f"[WARN] Rejected {category} AI text due to format guard: {validation_reason}")
                _set_last_ai_status(
                    used_ai=False,
                    provider_used="openai",
                    gemini_failed=False,
                    gemini_failure_reason=validation_reason,
                )
                return None
        _set_last_ai_status(
            used_ai=bool(result),
            provider_used="openai",
            gemini_failed=False,
            gemini_failure_reason=reason if not result else "",
        )
        return result

    if provider == "deepseek":
        result, reason = call_deepseek(system_prompt, user_prompt, category, timeout_sec, temperature)
        if result and violates_time_of_day(result, slot_hour):
            print(f"[WARN] Rejected {category} AI text due to morning wording in {slot_hour}:00 slot")
            _set_last_ai_status(
                used_ai=False,
                provider_used="deepseek",
                gemini_failed=False,
                deepseek_failed=True,
                deepseek_failure_reason="time_guard_rejected",
            )
            return None
        if result:
            valid, validation_reason = _validate_category_output(category, result)
            if not valid:
                print(f"[WARN] Rejected {category} AI text due to format guard: {validation_reason}")
                if category in BUDDHIST_ALMANAC_CATEGORIES:
                    repair_system, repair_user = _build_buddhist_almanac_repair_prompts(
                        category=category,
                        now_local=now_local,
                        validation_reason=validation_reason,
                        previous_text=result,
                    )
                    retry_result, retry_reason = call_deepseek(
                        repair_system,
                        repair_user,
                        category,
                        timeout_sec,
                        temperature,
                    )
                    if retry_result:
                        retry_valid, retry_validation_reason = _validate_category_output(
                            category,
                            retry_result,
                        )
                        if retry_valid and not violates_time_of_day(retry_result, slot_hour):
                            _set_last_ai_status(
                                used_ai=True,
                                provider_used="deepseek",
                                gemini_failed=False,
                                deepseek_failed=False,
                                deepseek_failure_reason="",
                            )
                            return retry_result
                        if not retry_valid:
                            validation_reason = retry_validation_reason
                        else:
                            validation_reason = "time_guard_rejected"
                    elif retry_reason:
                        validation_reason = retry_reason
                elif category == "zodiac_horoscope":
                    repair_system, repair_user = _build_zodiac_repair_prompts(
                        now_local=now_local,
                        validation_reason=validation_reason,
                        previous_text=result,
                    )
                    retry_result, retry_reason = call_deepseek(
                        repair_system,
                        repair_user,
                        category,
                        timeout_sec,
                        temperature,
                    )
                    if retry_result:
                        retry_valid, retry_validation_reason = _validate_category_output(
                            category,
                            retry_result,
                        )
                        if retry_valid and not violates_time_of_day(retry_result, slot_hour):
                            _set_last_ai_status(
                                used_ai=True,
                                provider_used="deepseek",
                                gemini_failed=False,
                                deepseek_failed=False,
                                deepseek_failure_reason="",
                            )
                            return retry_result
                        if not retry_valid:
                            validation_reason = retry_validation_reason
                        else:
                            validation_reason = "time_guard_rejected"
                    elif retry_reason:
                        validation_reason = retry_reason
                _set_last_ai_status(
                    used_ai=False,
                    provider_used="deepseek",
                    gemini_failed=False,
                    deepseek_failed=True,
                    deepseek_failure_reason=validation_reason,
                )
                return None
        _set_last_ai_status(
            used_ai=bool(result),
            provider_used="deepseek",
            gemini_failed=False,
            deepseek_failed=not bool(result),
            deepseek_failure_reason=reason if not result else "",
        )
        return result

    # Auto mode: prefer Gemini if key exists, then DeepSeek, then OpenAI.
    gemini_failed = False
    gemini_failure_reason = ""
    deepseek_failed = False
    deepseek_failure_reason = ""

    if get_gemini_api_keys():
        result, reason = call_gemini(system_prompt, user_prompt, category, timeout_sec, temperature)
        if result and violates_time_of_day(result, slot_hour):
            print(f"[WARN] Rejected {category} AI text due to morning wording in {slot_hour}:00 slot")
            gemini_failed = True
            gemini_failure_reason = "time_guard_rejected"
            result = None
        if result:
            valid, validation_reason = _validate_category_output(category, result)
            if not valid:
                print(f"[WARN] Rejected {category} AI text due to format guard: {validation_reason}")
                if category == "mantra":
                    repair_system, repair_user = _build_mantra_repair_prompts(
                        now_local=now_local,
                        validation_reason=validation_reason,
                        previous_text=result,
                    )
                    retry_result, retry_reason = call_gemini(
                        repair_system,
                        repair_user,
                        category,
                        timeout_sec,
                        temperature,
                    )
                    if retry_result:
                        retry_valid, retry_validation_reason = _validate_category_output(
                            category,
                            retry_result,
                        )
                        if retry_valid and not violates_time_of_day(retry_result, slot_hour):
                            _set_last_ai_status(
                                used_ai=True,
                                provider_used="gemini",
                                gemini_failed=False,
                                gemini_failure_reason="",
                            )
                            return retry_result
                        if not retry_valid:
                            validation_reason = retry_validation_reason
                        else:
                            validation_reason = "time_guard_rejected"
                    elif retry_reason:
                        validation_reason = retry_reason
                elif category == "zodiac_horoscope":
                    repair_system, repair_user = _build_zodiac_repair_prompts(
                        now_local=now_local,
                        validation_reason=validation_reason,
                        previous_text=result,
                    )
                    retry_result, retry_reason = call_gemini(
                        repair_system,
                        repair_user,
                        category,
                        timeout_sec,
                        temperature,
                    )
                    if retry_result:
                        retry_valid, retry_validation_reason = _validate_category_output(
                            category,
                            retry_result,
                        )
                        if retry_valid and not violates_time_of_day(retry_result, slot_hour):
                            _set_last_ai_status(
                                used_ai=True,
                                provider_used="gemini",
                                gemini_failed=False,
                                gemini_failure_reason="",
                            )
                            return retry_result
                        if not retry_valid:
                            validation_reason = retry_validation_reason
                        else:
                            validation_reason = "time_guard_rejected"
                    elif retry_reason:
                        validation_reason = retry_reason
                gemini_failed = True
                gemini_failure_reason = validation_reason
                result = None
        if result:
            _set_last_ai_status(
                used_ai=True,
                provider_used="gemini",
                gemini_failed=False,
                gemini_failure_reason="",
            )
            return result
        gemini_failed = True
        gemini_failure_reason = reason or "gemini_unknown_error"

    # DeepSeek fallback (auto mode)
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if deepseek_key:
        result, reason = call_deepseek(system_prompt, user_prompt, category, timeout_sec, temperature)
        if result and violates_time_of_day(result, slot_hour):
            print(f"[WARN] Rejected {category} AI text due to morning wording in {slot_hour}:00 slot")
            deepseek_failed = True
            deepseek_failure_reason = "time_guard_rejected"
            result = None
        if result:
            valid, validation_reason = _validate_category_output(category, result)
            if not valid:
                print(f"[WARN] Rejected {category} AI text due to format guard: {validation_reason}")
                if category in BUDDHIST_ALMANAC_CATEGORIES:
                    repair_system, repair_user = _build_buddhist_almanac_repair_prompts(
                        category=category,
                        now_local=now_local,
                        validation_reason=validation_reason,
                        previous_text=result,
                    )
                    retry_result, retry_reason = call_deepseek(
                        repair_system,
                        repair_user,
                        category,
                        timeout_sec,
                        temperature,
                    )
                    if retry_result:
                        retry_valid, retry_validation_reason = _validate_category_output(
                            category,
                            retry_result,
                        )
                        if retry_valid and not violates_time_of_day(retry_result, slot_hour):
                            _set_last_ai_status(
                                used_ai=True,
                                provider_used="deepseek",
                                gemini_failed=gemini_failed,
                                gemini_failure_reason=gemini_failure_reason,
                                deepseek_failed=False,
                                deepseek_failure_reason="",
                            )
                            return retry_result
                        if not retry_valid:
                            validation_reason = retry_validation_reason
                        else:
                            validation_reason = "time_guard_rejected"
                    elif retry_reason:
                        validation_reason = retry_reason
                elif category == "zodiac_horoscope":
                    repair_system, repair_user = _build_zodiac_repair_prompts(
                        now_local=now_local,
                        validation_reason=validation_reason,
                        previous_text=result,
                    )
                    retry_result, retry_reason = call_deepseek(
                        repair_system,
                        repair_user,
                        category,
                        timeout_sec,
                        temperature,
                    )
                    if retry_result:
                        retry_valid, retry_validation_reason = _validate_category_output(
                            category,
                            retry_result,
                        )
                        if retry_valid and not violates_time_of_day(retry_result, slot_hour):
                            _set_last_ai_status(
                                used_ai=True,
                                provider_used="deepseek",
                                gemini_failed=gemini_failed,
                                gemini_failure_reason=gemini_failure_reason,
                                deepseek_failed=False,
                                deepseek_failure_reason="",
                            )
                            return retry_result
                        if not retry_valid:
                            validation_reason = retry_validation_reason
                        else:
                            validation_reason = "time_guard_rejected"
                    elif retry_reason:
                        validation_reason = retry_reason
                deepseek_failed = True
                deepseek_failure_reason = validation_reason
                result = None
        if result:
            _set_last_ai_status(
                used_ai=True,
                provider_used="deepseek",
                gemini_failed=gemini_failed,
                gemini_failure_reason=gemini_failure_reason,
                deepseek_failed=False,
                deepseek_failure_reason="",
            )
            return result
        deepseek_failed = True
        deepseek_failure_reason = deepseek_failure_reason or reason or "deepseek_unknown_error"

    result, openai_reason = call_openai(system_prompt, user_prompt, category, timeout_sec, temperature)
    if result and violates_time_of_day(result, slot_hour):
        print(f"[WARN] Rejected {category} AI text due to morning wording in {slot_hour}:00 slot")
        _set_last_ai_status(
            used_ai=False,
            provider_used="openai",
            gemini_failed=gemini_failed,
            gemini_failure_reason=gemini_failure_reason or "time_guard_rejected",
            deepseek_failed=deepseek_failed,
            deepseek_failure_reason=deepseek_failure_reason,
        )
        return None
    if result:
        valid, validation_reason = _validate_category_output(category, result)
        if not valid:
            print(f"[WARN] Rejected {category} AI text due to format guard: {validation_reason}")
            _set_last_ai_status(
                used_ai=False,
                provider_used="openai",
                gemini_failed=gemini_failed,
                gemini_failure_reason=gemini_failure_reason or validation_reason,
                deepseek_failed=deepseek_failed,
                deepseek_failure_reason=deepseek_failure_reason,
            )
            return None
    _set_last_ai_status(
        used_ai=bool(result),
        provider_used="openai" if result else "",
        gemini_failed=gemini_failed,
        gemini_failure_reason=gemini_failure_reason or (openai_reason if not result else ""),
        deepseek_failed=deepseek_failed,
        deepseek_failure_reason=deepseek_failure_reason,
    )
    return result
