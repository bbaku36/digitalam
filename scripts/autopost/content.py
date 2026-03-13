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
        f"Өтгөсийн ухаарал, өдрийн сануулга ({now_local})",
        "",
        "Өнөөдөр сэтгэлдээ тогтоож явах 5 үг:",
        "",
    ]
    for i, quote in enumerate(picked, start=1):
        lines.append(f"{i}. {quote}")
    lines.extend(
        [
            "",
            "Өвгөдийн үг уртдаа биш, яг цагтаа хүрсэндээ үнэ цэнтэй байдаг.",
            "#ӨтгөсийнУхаарал #ӨдрийнСануулга #СэтгэлийнДэмжлэг #DigitalLam",
        ]
    )
    return "\n".join(lines).strip()


def build_horoscope_post_fallback() -> str:
    now = content_context_now()
    now_local = now.strftime("%Y-%m-%d")
    seed = int(now.strftime("%Y%m%d")) + now.hour

    general_lines = [
        "сэтгэлээ яаруу бус, төв байлгавал үйлс урагшилна.",
        "чимээгүй төвлөрөл өнөөдрийн хийморийг тэгшлэнэ.",
        "үл ялиг тэвчээр том маргааныг дарна.",
    ]
    hair_lines = [
        "үсээ засвал өнгө зүс сэргэж, дотоод шийдэмгий байдал чангарна гэж үзнэ.",
        "үс засуулах бол яаруу газар бус, тайван орчин сонговол зохино.",
        "үс засуулж болно, гэхдээ нэг ажлаа гүйцээж байж хөдөлбөл өлзийтэй.",
    ]
    travel_lines = [
        "аян замд гарах бол эд хэрэгсэл, унаа тэрэгний бэлтгэлээ давхар шалга.",
        "замд гарахад хар үг, муу ёр дагуулалгүй, тайван хөдөлбөл сайн.",
        "хол ойрын замд явах бол ахмадын ерөөл авч, яаралгүй хөдөлбөл зохино.",
    ]
    good_deed_lines = [
        "ариун цэвэрлэх, гэр орноо цэгцлэх, лам багш ахмадад хүндэтгэл үзүүлэхэд сайн.",
        "ном унших, маань тарни унших, тангарагтай ажлаа дуусгахад сайн.",
        "буяны сэтгэл гаргаж, бусдад дэм өгөх, эв эеийг сахихад сайн.",
    ]
    caution_lines = [
        "хэрүүл өдөх, ам нээж муу үг хэлэх, яаруу амлалт өгөхийг цээрлэ.",
        "архи дарс, дэмий зардал, хөнгөн хийсвэр шийдвэрээс болгоомжил.",
        "хүний сэтгэл гонсойлгох, амласнаа эвдэх, уурын үгээр түрэхийг цээрлэ.",
    ]

    lines = [
        f"Өдрийн зурхай ({now_local})",
        "",
        f"Өдрийн ерөнхий төлөв: {general_lines[seed % len(general_lines)]}",
        "",
        f"Үс засуулах: {hair_lines[(seed + 1) % len(hair_lines)]}",
        f"Аян замд гарах: {travel_lines[(seed + 2) % len(travel_lines)]}",
        f"Үйл хийхэд сайн: {good_deed_lines[(seed + 3) % len(good_deed_lines)]}",
        f"Цээрлэх зүйл: {caution_lines[(seed + 4) % len(caution_lines)]}",
        "",
        "Өтгөсийн сануулга: хийж буй үйлээ цэгцтэй, хэлэх үгээ гамтай авч яваарай.",
        "Тэмдэглэл: Энэ нь уламжлалт шарын шашны хэв маягаар өгсөн ерөнхий чиглүүлэг бөгөөд хувь хүний нөхцөлөөс хамаарч өөр байна.",
        "#ШарынШашныЗурхай #ӨдрийнЗурхай #ҮсЗасуулах #АянЗам #DigitalLam",
    ]
    return "\n".join(lines).strip()


def build_zodiac_horoscope_post_fallback() -> str:
    now = content_context_now()
    now_local = now.strftime("%Y-%m-%d")
    seed = int(now.strftime("%Y%m%d")) + now.hour
    focus_topics = [
        "ажил үйлс",
        "гэр бүл, харилцаа",
        "санхүү, зарлага",
        "сэтгэл, төвлөрөл",
        "эрч хүч, амралт",
        "суралцах, мэдлэг",
    ]
    action_tips = [
        "яаруу шийдвэрээс зайлсхийвэл зохино.",
        "нэг гол ажлаа барьж явбал өлзийтэй.",
        "ам нээхээсээ өмнө бодвол сайн.",
        "илүү зардал гаргахгүй байвал зохистой.",
        "тайван, цэгцтэй явбал бүтэмжтэй.",
        "ахмадын үгийг сонсвол тус болно.",
    ]

    lines = [
        f"12 ордын зурхай ({now_local})",
        "",
        "Өнөөдрийн ерөнхий төлөв: жижиг боловч зөв алхам бүр үр өгөөжтэй байна.",
        "",
    ]
    for idx, sign in enumerate(ZODIAC_SIGNS_MN):
        focus = focus_topics[(seed + idx) % len(focus_topics)]
        action = action_tips[(seed * 2 + idx) % len(action_tips)]
        lines.append(f"{sign}: {focus} дээр анхаарвал сайн, {action}")
    lines.extend(
        [
            "",
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

    hair_idx = seed % 7
    travel_idx = (seed * 3 + 1) % 7
    if travel_idx == hair_idx:
        travel_idx = (travel_idx + 2) % 7
    deed_idx = (seed * 5 + 2) % 7
    while deed_idx in {hair_idx, travel_idx}:
        deed_idx = (deed_idx + 1) % 7

    hair_date = monday + timedelta(days=hair_idx)
    travel_date = monday + timedelta(days=travel_idx)
    deed_date = monday + timedelta(days=deed_idx)

    lines = [
        f"7 хоногийн шарын шашны зурхай ({monday.strftime('%Y-%m-%d')} - {sunday.strftime('%Y-%m-%d')})",
        "",
        "Ерөнхий чиг: энэ 7 хоногт яаруу их үйлээс илүү цэгцтэй жижиг үйл өлзий дагуулна.",
        "",
        f"Үс засуулахад дөхөм өдөр: {WEEKDAY_MN[hair_idx]} ({hair_date.strftime('%m.%d')})",
        "Өнгө зүсээ сэргээж, сэтгэлээ төвлөрүүлэх ажилтай давхцуулбал сайн.",
        "",
        f"Аян замд гарахад дөхөм өдөр: {WEEKDAY_MN[travel_idx]} ({travel_date.strftime('%m.%d')})",
        "Замын бэлтгэлээ базааж, яаралгүй хөдөлбөл бүтэмжтэй.",
        "",
        f"Үйл хийхэд сайн өдөр: {WEEKDAY_MN[deed_idx]} ({deed_date.strftime('%m.%d')})",
        "Гэр орноо ариусгах, бичиг цаасаа янзлах, буяны үйлд шамдахад сайн.",
        "",
        "Цээрлэх зүйл: хэрүүл өдөөх, яаруу амлалт өгөх, дэмий зардал гаргахыг аль болох цээрлэ.",
        "",
        "Тэмдэглэл: Энэ нь уламжлалт шарын шашны хэв маягаар өгсөн ерөнхий чиглүүлэг бөгөөд хувь хүний нөхцөлөөс хамаарч өөр байна.",
        "#7ХоногийнЗурхай #ШарынШашныЗурхай #АянЗам #ҮсЗасуулах #DigitalLam",
    ]
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
