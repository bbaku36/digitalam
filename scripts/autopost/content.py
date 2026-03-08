"""Content builders (AI-first with deterministic local fallbacks)."""

from __future__ import annotations

import os
from datetime import timedelta

from .ai import ai_generate_generic_post
from .constants import (
    EVENING_INSIGHTS_MN,
    INSIGHT_QUOTES_MN,
    MANTRA_LIBRARY_MN,
    RELIGIOUS_FACTS_MN,
    TOMORROW_PREP_TIPS_MN,
    WEEKDAY_MN,
    ZODIAC_SIGNS_MN,
)
from .env import now_in_content_timezone


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


def build_insight_post_fallback() -> str:
    now = now_in_content_timezone()
    now_local = now.strftime("%Y-%m-%d")
    lines_per_post = 5
    seed = int(now.strftime("%Y%m%d"))
    start = seed % len(INSIGHT_QUOTES_MN)

    picked = [INSIGHT_QUOTES_MN[(start + i) % len(INSIGHT_QUOTES_MN)] for i in range(lines_per_post)]

    lines = [
        f"Өдрийн ухаарал ба урам өгөх үгс ({now_local})",
        "",
        "Өнөөдрийн урам, ухаарал:",
        "",
    ]
    for i, quote in enumerate(picked, start=1):
        lines.append(f"{i}. {quote}")
    lines.extend(
        [
            "",
            "Танд хамгийн их хүрсэн нэг мөрийг коммент дээр үлдээгээрэй.",
            "#ӨдрийнУхаарал #УрамӨгөхҮгс #СэтгэлийнДэмжлэг #DigitalLam",
        ]
    )
    return "\n".join(lines).strip()


def build_horoscope_post_fallback() -> str:
    now_local = now_in_content_timezone().strftime("%Y-%m-%d")
    lines = [
        f"Өдрийн зурхай ({now_local})",
        "",
        "Өнөөдрийн ерөнхий энерги: тайван төлөвлөж, бага багаар хэрэгжүүлэхэд сайн өдөр.",
        "",
    ]
    for idx, sign in enumerate(ZODIAC_SIGNS_MN, start=1):
        focus = [
            "ажил ба зорилт",
            "харилцаа холбоо",
            "эрч хүч ба сахилга",
            "санхүүгийн хэмнэлт",
            "суралцах ба өөрийгөө хөгжүүлэх",
            "амралт ба дотоод төвлөрөл",
        ][idx % 6]
        lines.append(f"{idx}. {sign}: {focus} дээр жижиг алхмаа тууштай хийвэл сайн үр дүн гарна.")
    lines.extend(
        [
            "",
            "Орой 5 минут нам гүмд сууж, маргаашийн 1 чухал ажлаа тодорхойлоорой.",
            "#Зурхай #ӨдрийнЗөвлөмж #DigitalLam",
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
        f"Шашны сонирхолтой баримтууд ({now_local})",
        "",
        "Өнөөдрийн товч баримтууд:",
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

    hair_idx = seed % 7
    travel_idx = (seed * 2 + 3) % 7
    if travel_idx == hair_idx:
        travel_idx = (travel_idx + 1) % 7
    avoid_idx = (seed * 3 + 5) % 7
    while avoid_idx in {hair_idx, travel_idx}:
        avoid_idx = (avoid_idx + 1) % 7

    hair_note = [
        "дотоод шийдэмгий байдлаа нэмэхэд төвлөрвөл сайн.",
        "шинэ эхлэл төлөвлөхөд эерэг нөлөөтэй өдөр.",
        "ажлаа цэгцлэх эрч хүч нэмэгдэх хандлагатай.",
    ][seed % 3]
    travel_note = [
        "замын бэлтгэлээ урьдчилж шалгаад хөдөлбөл зохистой.",
        "яарахгүй, төлөвлөгөөтэй явахад бүтэмжтэй өдөр.",
        "аюулгүй байдлаа нэгдүгээрт тавибал өлзийтэй.",
    ][(seed + 1) % 3]
    avoid_note = [
        "яаруу амлалт өгөхөөс зайлсхийгээрэй.",
        "маргаантай сэдвийг хурц үгээр эхлүүлэхгүй байхыг зөвлөе.",
        "хэт их зардалтай шийдвэрийг өнөөдөр түр хойшлуулбал зохино.",
    ][(seed + 2) % 3]

    lines = [
        f"Өдрийн үйл, чиглүүлэг ({date_label})",
        "",
        f"Үс засуулахад тохиромжтой өдөр: {WEEKDAY_MN[hair_idx]} — {hair_note}",
        f"Замд гарахад сайн чиг: {WEEKDAY_MN[travel_idx]} — {travel_note}",
        f"Өнөөдрийн цээрлэх зүйл: {WEEKDAY_MN[avoid_idx]} — {avoid_note}",
        "",
        "Тэмдэглэл: Энэ нь уламжлалт, ерөнхий чиглүүлэг бөгөөд хувь хүний нөхцөлөөс хамаарч өөр байна.",
        "#ӨдрийнҮйл #ҮсЗасуулах #ЗамдГарах #DigitalLam",
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
        f"Оройн ухаарал ({now.strftime('%Y-%m-%d')})",
        "",
    ]
    for idx, line in enumerate(picked, start=1):
        lines.append(f"{idx}. {line}")
    lines.extend(
        [
            "",
            "#ОройнУхаарал #ТайванСэтгэл #DigitalLam",
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
        "Маргаашийн бэлтгэл",
        "",
        f"1 зөвлөмж: {tip}",
        f"Ерөөл: {blessing}",
        "",
        "#МаргаашийнБэлтгэл #Ерөөл #DigitalLam",
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

    hair_date = monday + timedelta(days=hair_idx)
    travel_date = monday + timedelta(days=travel_idx)

    lines = [
        f"7 хоногийн чиглүүлэг ({monday.strftime('%Y-%m-%d')} - {sunday.strftime('%Y-%m-%d')})",
        "",
        f"Үс засуулахад сайн өдөр: {WEEKDAY_MN[hair_idx]} ({hair_date.strftime('%m.%d')})",
        "Зорилгоо цэгцэлж, шинэ эхлэл хийхэд төвлөрвөл сайн.",
        "",
        f"Хол замд гарахад сайн өдөр: {WEEKDAY_MN[travel_idx]} ({travel_date.strftime('%m.%d')})",
        "Замдаа тайван төлөвлөж, аюулгүй байдлаа эхэнд тавиарай.",
        "",
        "Тэмдэглэл: Энэ нь уламжлалт, ерөнхий чиглүүлэг бөгөөд хувь хүний нөхцөлөөс хамаарч өөр байна.",
        "#7ХоногийнЗөвлөмж #ӨдрийнУхаарал #DigitalLam",
    ]
    return "\n".join(lines).strip()


def build_weekly_horoscope_post_fallback() -> str:
    now = now_in_content_timezone()
    monday = now - timedelta(days=now.weekday())
    sunday = monday + timedelta(days=6)
    iso = now.isocalendar()
    seed = iso.year * 100 + iso.week

    focus_topics = [
        "ажлын төлөвлөлт",
        "харилцаа, ойлголцол",
        "сэтгэлийн төвлөрөл",
        "санхүүгийн сахилга",
        "суралцах, ур чадвар",
        "амралт ба тэнцвэр",
    ]
    action_tips = [
        "нэг гол зорилтоо тодорхой бич",
        "өдөр бүр 20 минут төвлөрсөн ажил хий",
        "ярихаасаа өмнө нэг амьсгаа аваад бод",
        "шаардлагагүй зардлаа энэ 7 хоног хязгаарла",
        "өөрт хэрэгтэй нэг шинэ зүйл сур",
        "унтах цагтаа тогтвортой бай",
    ]
    caution_tips = [
        "яаравчилсан шийдвэрээс зайлсхий",
        "үл ойлголцлыг хурцдуулах үг бүү хэрэглэ",
        "амралтаа хэт хойшлуулахгүй бай",
        "амлалтаа хэтрүүлж өгөхөөс болгоомжил",
    ]

    lines = [
        f"7 хоногийн ордуудын зурхай ({monday.strftime('%Y-%m-%d')} - {sunday.strftime('%Y-%m-%d')})",
        "",
        "Ерөнхий чиг: тогтвортой жижиг алхмууд энэ 7 хоногт хамгийн том үр дүн авчирна.",
        "",
    ]

    for idx, sign in enumerate(ZODIAC_SIGNS_MN, start=1):
        focus = focus_topics[(seed + idx) % len(focus_topics)]
        action = action_tips[(seed * 2 + idx) % len(action_tips)]
        caution = caution_tips[(seed * 3 + idx) % len(caution_tips)]
        lines.append(f"{idx}. {sign}: {focus} дээр ахиц гарна. {action}; {caution}.")

    lines.extend(
        [
            "",
            "Тэмдэглэл: Энэ нь уламжлалт, ерөнхий чиглүүлэг бөгөөд хувь хүний нөхцөлөөс хамаарч өөр байна.",
            "#7ХоногийнЗурхай #Орд #СүнслэгЧиглүүлэг #DigitalLam",
        ]
    )
    return "\n".join(lines).strip()


def build_category_post(category: str) -> str:
    now_ctx = content_context_now()
    now_local = now_ctx.strftime("%Y-%m-%d %H:%M")
    ai_post = ai_generate_generic_post(category, now_local, slot_hour=now_ctx.hour)
    if ai_post:
        return ai_post

    if category == "insight":
        return build_insight_post_fallback()
    if category == "horoscope":
        return build_horoscope_post_fallback()
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
