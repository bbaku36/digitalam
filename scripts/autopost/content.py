"""Content builders (AI-first with deterministic local fallbacks)."""

from __future__ import annotations

import os
import re
from datetime import timedelta

from .ai import ai_generate_generic_post
from .constants import (
    EVENING_INSIGHTS_MN,
    MANTRA_LIBRARY_MN,
    RELIGIOUS_FACTS_MN,
    TOMORROW_PREP_TIPS_MN,
    WEEKDAY_MN,
    ZODIAC_SIGN_DETAILS_MN,
    ZODIAC_SIGNS_MN,
)
from .env import now_in_content_timezone
from .gogo_source import build_gogo_source_context

GOGO_SOURCE_REQUIRED_CATEGORIES = {"horoscope", "zodiac_horoscope", "weekly_horoscope"}

HOROSCOPE_SECTION_HEADINGS = {
    "🌿 Өдрийн ерөнхий төлөв",
    "✂️ Үс засуулах тохиромж",
    "🛣️ Аян замд гарах",
    "📿 Үйл хийхэд сайн",
    "⚠️ Цээрлэх зүйл",
}
HOROSCOPE_FIXED_DISCLAIMER = "Энэхүү зурхай нь уламжлалт билгийн тооллын ерөнхий мэдээлэл болно."


def content_context_now():
    now = now_in_content_timezone()
    forced_hour_raw = os.getenv("FORCE_SLOT_HOUR", "").strip()
    if forced_hour_raw:
        try:
            forced_hour = int(forced_hour_raw)
            if 0 <= forced_hour <= 23:
                return now.replace(hour=forced_hour, minute=0, second=0, microsecond=0)
        except ValueError:
            pass
    return now


def format_mongolian_day_intro(now) -> str:
    return f"{now.year} оны {now.month} дугаар сарын {now.day}."


def _extract_source_value(source_context: str | None, prefix: str) -> str:
    if not source_context:
        return ""
    for line in source_context.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def _normalize_year_line(value: str) -> str:
    cleaned = value.strip().rstrip(".")
    cleaned = re.sub(r"\s*жилтнээ$", "", cleaned).strip()
    return cleaned


def _inject_horoscope_year_lines(text: str, source_context: str | None) -> str:
    favorable = _normalize_year_line(_extract_source_value(source_context, "Favorable years: "))
    caution = _normalize_year_line(_extract_source_value(source_context, "Caution years: "))
    if not favorable and not caution:
        return text

    lines = text.splitlines()
    cleaned_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Жилтэнд сайн/болгоомжтой:"):
            continue
        if stripped.startswith("✅ Сайн жилтэн:"):
            continue
        if stripped.startswith("⚠️ Болгоомжлох жилтэн:"):
            continue
        cleaned_lines.append(line)

    action_idx = next(
        (idx for idx, line in enumerate(cleaned_lines) if line.strip() == "📿 Үйл хийхэд сайн"),
        None,
    )
    if action_idx is None:
        return "\n".join(cleaned_lines).strip()

    next_heading_idx = next(
        (
            idx
            for idx in range(action_idx + 1, len(cleaned_lines))
            if cleaned_lines[idx].strip() in HOROSCOPE_SECTION_HEADINGS
        ),
        len(cleaned_lines),
    )
    insert_idx = next_heading_idx
    while insert_idx > action_idx + 1 and not cleaned_lines[insert_idx - 1].strip():
        insert_idx -= 1

    injected_lines: list[str] = []
    injected_lines.append("")
    if favorable:
        injected_lines.append(f"✅ Сайн жилтэн: {favorable}")
    if caution:
        injected_lines.append(f"⚠️ Болгоомжлох жилтэн: {caution}")

    if not injected_lines:
        return "\n".join(cleaned_lines).strip()

    updated_lines = cleaned_lines[:insert_idx] + injected_lines + cleaned_lines[insert_idx:]
    return "\n".join(updated_lines).strip()


def _normalize_horoscope_post(text: str, date_intro: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    heading_idx = next(
        (idx for idx, line in enumerate(lines) if line.strip() == "🌿 Өдрийн ерөнхий төлөв"),
        None,
    )

    if heading_idx is not None:
        biligiin_line = next(
            (line.strip() for line in lines[:heading_idx] if line.strip().startswith("Билгийн тооллын")),
            "",
        )
        rebuilt_lines = [date_intro, "Өдрийн үс засуулах, аян зам, үйл хийхийн зурхай."]
        if biligiin_line:
            rebuilt_lines.append(biligiin_line)
        rebuilt_lines.append("")
        rebuilt_lines.extend(lines[heading_idx:])
        lines = rebuilt_lines
    else:
        lines = [
            "Өдрийн үс засуулах, аян зам, үйл хийхийн зурхай."
            if "Өнөөдрийн үс засуулах, аян зам, үйл хийхийн зурхай" in line
            else line
            for line in lines
        ]

    cleaned_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        cleaned_lines.append(line)

    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()
    if cleaned_lines:
        last_line = cleaned_lines[-1].strip().lower()
        if any(marker in last_line for marker in ("зурхай", "тэмдэглэл", "зөвлөмж", "ерөнхий мэдээлэл")):
            cleaned_lines.pop()
            while cleaned_lines and not cleaned_lines[-1].strip():
                cleaned_lines.pop()

    cleaned_lines.extend(
        [
            "",
            HOROSCOPE_FIXED_DISCLAIMER,
            "",
            "#ӨдрийнЗурхай #ҮсЗасуулах #АянЗамдГарах #замдгарах",
        ]
    )
    return "\n".join(cleaned_lines).strip()


def build_insight_post_fallback() -> str:
    return ""


def build_horoscope_post_fallback() -> str:
    now = content_context_now()
    seed = int(now.strftime("%Y%m%d")) + now.hour

    general_lines = [
        "Эл өдөр сэтгэлээ төв байлгаж, үг хэлээ зөөллөж явбал өлзийтэй.",
        "Эл өдөр аливаа үйлээ яаруу бус, дэс дараатай хийвэл хийморь тогтоно.",
        "Эл өдөр тайван хичээнгүй явбал санасан хэрэг саад багатай бүтнэ.",
    ]
    hair_lines = [
        "Үс шинээр үргээлгэх буюу засуулахад амгалан жаргалан дэлгэрэх сайн.",
        "Үс шинээр үргээлгэх буюу засуулахад өнгө зүс сэргэж, сэтгэл өег байх сайн.",
        "Үс шинээр үргээлгэх буюу засуулахад бие сэтгэл цэлмэж, хийморь тэгширнэ.",
    ]
    travel_lines = [
        "Хол газар яваар одогсод баруун мөрөө гаргавал аян зам өлзийтэй байна.",
        "Хол газар яваар одогсод урд мөрөө гаргавал ажил бүтэмжтэй, саад багатай.",
        "Хол газар яваар одогсод зүүн мөрөө гаргавал зам харгуй тайван байна.",
    ]
    good_deed_lines = [
        "Эл өдөр буян номын үйл, маань тарни унших, ариусган цэвэрлэх үйлд сайн.",
        "Эл өдөр ахмадын ерөөл авах, гэр орноо ариусгах, засал номд оролцоход сайн.",
        "Эл өдөр сүсэг бишрэлтэй явж, өргөл хандив, буян хишгийн үйл хийхэд сайн.",
    ]
    caution_lines = [
        "Хэрүүл тэмцэл үүсгэх, муу үг хэлэх, амласнаа эвдэх үйл цээрлэвэл зохистой.",
        "Архи дарс хэтрүүлэх, бусдын сэтгэл гомдоох, яаруу уур гаргах үйл цээрлэвэл зохистой.",
        "Хов жив тараах, дэмий зардал гаргах, омтгой аашлах үйл цээрлэвэл зохистой.",
    ]

    lines = [
        format_mongolian_day_intro(now),
        "",
        "Өдрийн үс засуулах, аян зам, үйл хийхийн зурхай.",
        "",
        "🌿 Өдрийн ерөнхий төлөв",
        general_lines[seed % len(general_lines)],
        "",
        "✂️ Үс засуулах тохиромж",
        hair_lines[(seed + 1) % len(hair_lines)],
        "",
        "🛣️ Аян замд гарах",
        travel_lines[(seed + 2) % len(travel_lines)],
        "",
        "📿 Үйл хийхэд сайн",
        good_deed_lines[(seed + 3) % len(good_deed_lines)],
        "",
        "⚠️ Цээрлэх зүйл",
        caution_lines[(seed + 4) % len(caution_lines)],
        "",
        "Өтгөсийн сануулга: Биеэ энхрийлж, үгээ гамнаж, үйлээ ариунаар авч яваарай.",
        HOROSCOPE_FIXED_DISCLAIMER,
        "#ӨдрийнЗурхай #ҮсЗасуулах #АянЗамдГарах #замдгарах",
    ]
    return "\n".join(lines).strip()


def build_zodiac_horoscope_post_fallback() -> str:
    now = content_context_now()
    now_local = now.strftime("%Y-%m-%d")
    seed = int(now.strftime("%Y%m%d")) + now.hour
    intro_lines = [
        "Өнөөдрийн од эрхсийн ерөнхий нөлөө тогтуун, бодлогоширсон өнгөтэй байгаа тул санхүү, харилцаа, ажил хэрэг дээрээ тэнцвэртэй хандах нь чухал өдөр байна.",
        "Өнөөдөр хариуцлага, дотоод төвлөрөл, ойрын хүмүүсийн харилцаанд уужуу байдал түлхүү мэдрэгдэнэ.",
        "Өдрийн ерөнхий урсгал нь шийдэмгий боловч яаруу бус байж, мөнгө санхүү болон харилцаандаа бодолтой хандахыг сануулж байна.",
    ]
    area_lines = [
        "ажил хэрэг дээрээ",
        "санхүүгийн асуудалдаа",
        "гэр бүл, харилцаандаа",
        "дотоод төвлөрөлдөө",
        "эрч хүч, амралтдаа",
        "шинэ санаа, төлөвлөгөөндөө",
    ]
    action_lines = [
        "яаруу шийдвэр гаргалгүй, нэг ажлаа гүйцээж байж дараагийн алхмаа хийгээрэй.",
        "хэт их амлалт өгөхөөс зайлсхийж, хийж чадах зүйлдээ төвлөрвөл бүтэмжтэй.",
        "ойрын хүмүүсийнхээ үгийг сонсож, зөөлөн харилцвал ашигтай.",
        "илүү зардал, хэрэггүй маргаанаас хол байвал өдөр жигд өнгөрнө.",
        "санаагаа цэгцэлж, тайван хэмнэлээр явбал үр дүн гарна.",
        "өөрийн мэдрэмжээ сонссон ч бодит байдлаа нягталж алхвал сайн.",
    ]
    closing_lines = [
        "Оройг нам гүмхэн, өөртөө цаг гарган өнгөрөөвөл тустай.",
        "Багахан тэвчээр өнөөдрийн олон асуудлыг зөөллөх болно.",
        "Шийдвэр гаргахдаа сэтгэл хөдлөлөө биш, бодит нөхцөлөө түрүүлж харвал зөв.",
    ]

    lines = [
        f"12 ордын зурхай ({now_local})",
        "",
        intro_lines[seed % len(intro_lines)],
        "",
    ]
    for idx, (symbol, label, date_range) in enumerate(ZODIAC_SIGN_DETAILS_MN):
        area = area_lines[(seed + idx) % len(area_lines)]
        action = action_lines[(seed * 2 + idx) % len(action_lines)]
        closing = closing_lines[(seed * 3 + idx) % len(closing_lines)]
        lines.append(f"{symbol} {label} ({date_range})")
        lines.append(
            f"Өнөөдөр {area} илүү няхуур хандвал ашигтай. {action} {closing}"
        )
        lines.append("")
    lines.extend(
        [
            "Тэмдэглэл: Энэ нь ордын ерөнхий зурхай бөгөөд хувь хүний нөхцөлөөс хамаарч өөр байна.",
            "#12Орд #ӨдрийнЗурхай #ОрдныЗурхай #DigitalLam",
        ]
    )
    return "\n".join(lines).strip()


def build_mantra_post_fallback() -> str:
    now = now_in_content_timezone()
    now_local = now.strftime("%Y-%m-%d")
    seed = int(now.strftime("%Y%m%d"))
    variant_offset_raw = os.getenv("MANTRA_VARIANT_OFFSET", "0").strip()
    try:
        variant_offset = int(variant_offset_raw)
    except ValueError:
        variant_offset = 0
    total_mantras = len(MANTRA_LIBRARY_MN)
    pick_count = min(3, total_mantras)
    start = (seed + variant_offset) % total_mantras if total_mantras else 0

    picked = (
        [MANTRA_LIBRARY_MN[(start + i) % total_mantras] for i in range(pick_count)]
        if total_mantras
        else [
            (
                "Ум мани бад мэ хум",
                "Энэрэл, нигүүлслийн сэтгэлийг бадрааж, дотоод амар амгаланг дэмжинэ.",
                "21 эсвэл 108 удаа давтаж болно.",
            )
        ]
    )

    lines = [
        f"Өдрийн маань, тарни ба төвлөрөл ({now_local})",
        "",
        "Өнөөдрийн тарни (Монгол крилл галиг):",
    ]

    for idx, (mantra, description, repeat_hint) in enumerate(picked, start=1):
        lines.append(f"{idx}. {mantra}")
        lines.append(f"Тайлбар: {description} ({repeat_hint})")
        if idx != len(picked):
            lines.append("")

    lines.extend(
        [
            "",
            "Өнөөдрийн 3 практик алхам:",
            "1) Нэг удаа удаан, гүн амьсгаа 10 цикл хийх",
            "2) Утаснаас 20 минут хөндийрч нам гүмд суух",
            "3) Нэг хүнд талархал илэрхийлэх",
            "",
            "Сэтгэлээ амрааж, үйлдээ төвлөрөх өдөр байг.",
            "#Маань #Тарни #Бясалгал #DigitalLam",
        ]
    )
    return "\n".join(lines).strip()


def build_fact_post_fallback() -> str:
    now = now_in_content_timezone()
    now_local = now.strftime("%Y-%m-%d")
    facts_per_post = 5
    seed = int(now.strftime("%Y%m%d"))
    start = seed % len(RELIGIOUS_FACTS_MN)

    picked = [RELIGIOUS_FACTS_MN[(start + i) % len(RELIGIOUS_FACTS_MN)] for i in range(facts_per_post)]

    lines = [
        f"Оройн сонирхолтой шашны баримтууд ({now_local})",
        "",
        "Орой тайван суух энэ мөчид бодолд нэмэр болох товч баримтууд:",
        "",
    ]
    for i, fact in enumerate(picked, start=1):
        lines.append(f"{i}. {fact}")
    lines.extend(
        [
            "",
            "Та аль баримтыг илүү дэлгэрэнгүй тайлбарлуулахыг хүсвэл коммент бичээрэй.",
            "#ШашныБаримт #БуддынСургаал #СүнслэгБоловсрол #DigitalLam",
        ]
    )
    return "\n".join(lines).strip()


def build_daily_guidance_post_fallback() -> str:
    now = now_in_content_timezone()
    date_label = now.strftime("%Y-%m-%d")
    seed = int(now.strftime("%Y%m%d"))

    hair_note = [
        "үс засуулах бол тайван сэтгэлээр, ажил үйлээ цэгцэлсний дараа хөдөлбөл сайн.",
        "үсээ засвал өнгө зүс сэргэж, хийж буй ажилдаа анхаарал төвлөрөхөд дэмтэй гэж үзнэ.",
        "үс засуулахад гэмгүй өдөр, гэхдээ ам нээж хэрүүл бүү өдөө.",
    ][seed % 3]
    travel_note = [
        "аян замд гарах бол эд хэрэгсэл, замын хүнс, унаагаа урьдчилан шалга.",
        "хол ойрын замд явахад тайван хөдөлж, ахмадын ерөөл аваад гарахыг бэлгэшээнэ.",
        "замд гарах бол яарахгүй, чиг зүгээ нэг мөр болгоод хөдөлбөл сайн.",
    ][(seed + 1) % 3]
    action_note = [
        "гэр орноо ариусган цэгцлэх, ном унших, маань тарни уншихад сайн.",
        "буяны сэтгэл гаргаж, ахмад настандаа туслах, амласнаа биелүүлэхэд сайн.",
        "алдсан ажлаа нөхөх, бичиг цаасаа янзлах, эв эеийг сахихад сайн.",
    ][(seed + 2) % 3]
    avoid_note = [
        "хэрүүл маргаан эхлүүлэх, муу үг амнаасаа гаргахыг цээрлэ.",
        "дэмий зардал, яаруу амлалт, хөнгөн хийсвэр шийдвэрээс болгоомжил.",
        "архи дарс, хүний сэтгэл гонсойлгох үг, хуучин гомдол сөхөхийг цээрлэ.",
    ][(seed + 3) % 3]

    lines = [
        f"Өдрийн үйл, шарын шашны чиглүүлэг ({date_label})",
        "",
        f"Үс засуулах: {hair_note}",
        f"Аян замд гарах: {travel_note}",
        f"Үйл хийхэд сайн: {action_note}",
        f"Цээрлэх зүйл: {avoid_note}",
        "",
        "Өвгөдийн ёсонд өдөр тутмын үйлд тэвчээр, цэгц, амны билиг гурав хамт явдаг.",
        "Тэмдэглэл: Энэ нь уламжлалт шарын шашны хэв маягаар өгсөн ерөнхий чиглүүлэг бөгөөд хувь хүний нөхцөлөөс хамаарч өөр байна.",
        "#ӨдрийнҮйл #ШарынШашныЗурхай #ҮсЗасуулах #АянЗам #DigitalLam",
    ]
    return "\n".join(lines).strip()


def build_messenger_cta_post_fallback() -> str:
    lines = [
        "Оройн нууц захидлын цонх нээлттэй байна.",
        "",
        "Сэтгэл дээрээ тээж яваа зүйлээ anonymous байдлаар хуваалцаж болно.",
        "Нүглээ наминчлах, харамсал, айдас, эргэлзээгээ нэрээ дурдахгүй бичиж болно.",
        "Манай Messenger чат руу 'Нууц' гэж эхлүүлээд сэтгэлээ уудлаарай.",
        "",
        "Тэмдэглэл: Хариулт нь уламжлалт, сүнслэг чиглүүлэг болно. Нэрээ бичих шаардлагагүй.",
        "#НууцЗахидал #СэтгэлээУудалъя #Messenger #DigitalLam",
    ]
    return "\n".join(lines).strip()


def build_evening_insight_post_fallback() -> str:
    now = now_in_content_timezone()
    seed = int(now.strftime("%Y%m%d"))
    start = seed % len(EVENING_INSIGHTS_MN)
    picked = [EVENING_INSIGHTS_MN[(start + i) % len(EVENING_INSIGHTS_MN)] for i in range(3)]

    lines = [
        f"Оройн ухаарал, өтгөсийн захиас ({now.strftime('%Y-%m-%d')})",
        "",
    ]
    for idx, line in enumerate(picked, start=1):
        lines.append(f"{idx}. {line}")
    lines.extend(
        [
            "",
            "Оройн бодол цэгцтэй унтвал маргаашийн зам өөрөө шулууддаг.",
            "#ОройнУхаарал #ӨтгөсийнЗахиас #ТайванСэтгэл #DigitalLam",
        ]
    )
    return "\n".join(lines).strip()


def build_tomorrow_prep_post_fallback() -> str:
    now = now_in_content_timezone()
    seed = int(now.strftime("%Y%m%d"))
    tip = TOMORROW_PREP_TIPS_MN[seed % len(TOMORROW_PREP_TIPS_MN)]
    blessing = [
        "Маргаашийн алхам тань тод, сэтгэл тань амгалан байг.",
        "Маргааш таны ажил үйлсэд бүтэмж, сэтгэлд тайван байдал ерөөе.",
        "Шинэ өдөр танд зөв шийдвэр, зөөлөн ухаарал авчраг.",
    ][(seed + 1) % 3]

    lines = [
        "Маргаашийн бэлтгэл, өтгөсийн үг",
        "",
        f"1 зөвлөмж: {tip}",
        f"Ерөөл: {blessing}",
        "",
        "Өнөө оройгоо цэгцтэй өндөрлүүлбэл маргаашийн ажил нэгэнт талдаа орсон байдаг.",
        "#МаргаашийнБэлтгэл #ӨтгөсийнҮг #Ерөөл #DigitalLam",
    ]
    return "\n".join(lines).strip()


def build_goodnight_post_fallback() -> str:
    lines = [
        "Амар амгалан шөнө хүсье.",
        "Өнөөдрийн түгшүүрээ амьсгалаараа зөөлөн тавиад, тайван нойрсоорой.",
        "#АмарАмгаланШөнө #ТайванНойр #DigitalLam",
    ]
    return "\n".join(lines).strip()


def build_weekly_post_fallback() -> str:
    now = now_in_content_timezone()
    monday = now - timedelta(days=now.weekday())
    sunday = monday + timedelta(days=6)
    iso = now.isocalendar()
    seed = iso.year * 100 + iso.week

    hair_idx = seed % 7
    travel_idx = (seed * 3 + 2) % 7
    if travel_idx == hair_idx:
        travel_idx = (travel_idx + 2) % 7
    deed_idx = (seed * 5 + 1) % 7
    while deed_idx in {hair_idx, travel_idx}:
        deed_idx = (deed_idx + 1) % 7

    hair_date = monday + timedelta(days=hair_idx)
    travel_date = monday + timedelta(days=travel_idx)
    deed_date = monday + timedelta(days=deed_idx)

    lines = [
        f"7 хоногийн чиглүүлэг ({monday.strftime('%Y-%m-%d')} - {sunday.strftime('%Y-%m-%d')})",
        "",
        f"Үс засуулахад сайн өдөр: {WEEKDAY_MN[hair_idx]} ({hair_date.strftime('%m.%d')})",
        "Зорилгоо цэгцэлж, шинэ эхлэл хийхэд төвлөрвөл сайн.",
        "",
        f"Хол замд гарахад сайн өдөр: {WEEKDAY_MN[travel_idx]} ({travel_date.strftime('%m.%d')})",
        "Замдаа тайван төлөвлөж, аюулгүй байдлаа эхэнд тавиарай.",
        "",
        f"Үйл хийхэд сайн өдөр: {WEEKDAY_MN[deed_idx]} ({deed_date.strftime('%m.%d')})",
        "Гэр орноо ариусгах, бичиг цаасаа цэгцлэх, буяны үйлд шамдахад зохистой.",
        "",
        "Тэмдэглэл: Энэ нь уламжлалт шарын шашны хэв маягаар өгсөн ерөнхий чиглүүлэг бөгөөд хувь хүний нөхцөлөөс хамаарч өөр байна.",
        "#7ХоногийнЗөвлөмж #ШарынШашныЗурхай #ҮсЗасуулах #АянЗам #DigitalLam",
    ]
    return "\n".join(lines).strip()


def build_weekly_horoscope_post_fallback() -> str:
    now = now_in_content_timezone()
    monday = now - timedelta(days=now.weekday())
    sunday = monday + timedelta(days=6)
    iso = now.isocalendar()
    seed = iso.year * 100 + iso.week

    intro_lines = [
        "Энэ 7 хоногт үс засуулах, аян замд гарах, үйл хийхийн ерөнхий хэмнэлийг өдрөөр нь сийрүүлэв.",
        "Долоо хоногийн эх сурвалжийг өдрөөр нь харж, үс засуулах, аян зам, үйл хийхийн товч чигийг нэгтгэн хүргэж байна.",
        "7 хоногийн турш өдөр бүрийн үс засуулах, зам мөр, үйл хийхийн чигийг тоймлон хүргэж байна.",
    ]
    hair_lines = [
        "Үс засуулахад тэвчүү байвал зохистой.",
        "Үс засуулахад болгоомжтой хандах өдөр.",
        "Үс засуулахад гэмгүй, тайван өдөр.",
    ]
    travel_lines = [
        "Аян замд гарах бол зам мөрөө тайван бодоорой.",
        "Хол ойрын замд гарах бол чиг зүгээ нягтлаарай.",
        "Замд гарах бол яаруу бус хөдөлбөл зохистой.",
    ]
    action_lines = [
        "Гэр орон, сүсэг ном, цэгцтэй үйлд дөхөм.",
        "Буян ном, ариусгах, дотоод сахилгадаа анхаарахад сайн.",
        "Ажил үйлээ дэс дараатай авч явахад дөхөм.",
    ]

    lines = [
        f"7 хоногийн үйл, үс засуулах, аян замын тойм ({monday.strftime('%Y.%m.%d')}-{sunday.strftime('%Y.%m.%d')})",
        "",
        intro_lines[seed % len(intro_lines)],
        "",
    ]
    for idx in range(7):
        current = monday + timedelta(days=idx)
        lines.append(f"📅 {WEEKDAY_MN[idx]} ({current.strftime('%m.%d')})")
        lines.append(f"Үс засуулах: {hair_lines[(seed + idx) % len(hair_lines)]}")
        lines.append(f"Аян зам: {travel_lines[(seed * 2 + idx) % len(travel_lines)]}")
        lines.append(f"Үйл хийхэд сайн: {action_lines[(seed * 3 + idx) % len(action_lines)]}")
        lines.append("")
    lines.extend(
        [
            "7 хоногийн тойм",
            f"Үс засуулахад дөхөм өдөр: {WEEKDAY_MN[seed % 7]} ({(monday + timedelta(days=seed % 7)).strftime('%m.%d')})",
            f"Аян замд гарахад дөхөм өдөр: {WEEKDAY_MN[(seed + 2) % 7]} ({(monday + timedelta(days=(seed + 2) % 7)).strftime('%m.%d')})",
            f"Үйл хийхэд сайн өдөр: {WEEKDAY_MN[(seed + 4) % 7]} ({(monday + timedelta(days=(seed + 4) % 7)).strftime('%m.%d')})",
            "",
            "Тэмдэглэл: Энэ нь 7 хоногийн ерөнхий уламжлалт чиглүүлэг бөгөөд өдөр тутмын эх сурвалж дээр тулгуурлан товчилсон тойм болно.",
            "#7ХоногийнТойм #ҮсЗасуулах #АянЗам #DigitalLam",
        ]
    )
    return "\n".join(lines).strip()


def build_category_post(category: str) -> str:
    now_ctx = content_context_now()
    now_local = now_ctx.strftime("%Y-%m-%d %H:%M")
    source_context = build_gogo_source_context(category, now_local)
    ai_post = ai_generate_generic_post(
        category,
        now_local,
        slot_hour=now_ctx.hour,
        source_context=source_context,
    )
    if ai_post:
        if category == "horoscope":
            return _normalize_horoscope_post(
                _inject_horoscope_year_lines(ai_post, source_context),
                format_mongolian_day_intro(now_ctx),
            )
        return ai_post
    if category in GOGO_SOURCE_REQUIRED_CATEGORIES and not source_context:
        return ""

    if category == "insight":
        return build_insight_post_fallback()
    if category == "horoscope":
        return _normalize_horoscope_post(
            _inject_horoscope_year_lines(build_horoscope_post_fallback(), source_context),
            format_mongolian_day_intro(now_ctx),
        )
    if category == "zodiac_horoscope":
        return build_zodiac_horoscope_post_fallback()
    if category == "daily_guidance":
        return build_daily_guidance_post_fallback()
    if category == "mantra":
        return build_mantra_post_fallback()
    if category == "messenger_cta":
        return build_messenger_cta_post_fallback()
    if category == "evening_insight":
        return build_evening_insight_post_fallback()
    if category == "tomorrow_prep":
        return build_tomorrow_prep_post_fallback()
    if category == "goodnight":
        return build_goodnight_post_fallback()
    if category == "fact":
        return build_fact_post_fallback()
    if category == "weekly_horoscope":
        return build_weekly_horoscope_post_fallback()
    return build_weekly_post_fallback()
