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
    ZODIAC_SIGN_DETAILS_MN,
    ZODIAC_SIGNS_MN,
)
from .env import now_in_content_timezone
from .gogo_source import build_gogo_source_context


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
    return (
        f"Өнөөдөр {now.year} оны {now.month} дугаар сарын {now.day}, "
        f"{WEEKDAY_MN[now.weekday()]} гараг."
    )


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
        "Өнөөдрийн үс засуулах, аян зам, үйл хийхийн зурхайг доор сийрүүлье:",
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
        "Тэмдэглэл: Энэ нь уламжлалт хэв маягаар өгсөн ерөнхий зурхайн чиглүүлэг болно.",
        "#ӨдрийнЗурхай #ҮсЗасуулах #АянЗам #DigitalLam",
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
    source_context = build_gogo_source_context(category, now_local)
    ai_post = ai_generate_generic_post(
        category,
        now_local,
        slot_hour=now_ctx.hour,
        source_context=source_context,
    )
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
