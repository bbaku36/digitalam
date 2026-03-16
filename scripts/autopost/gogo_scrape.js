#!/usr/bin/env node

const { JSDOM, VirtualConsole } = require("jsdom");

const MODE = process.argv[2];
const TARGET_DATE = (process.argv[3] || "").trim();

const ZODIAC_SIGNS = [
  "Хонь",
  "Үхэр",
  "Ихэр",
  "Мэлхий",
  "Арслан",
  "Охин",
  "Жинлүүр",
  "Хилэнц",
  "Нум",
  "Матар",
  "Хумх",
  "Загас",
];

function normalizeText(value) {
  return (value || "")
    .replace(/\u00a0/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function smallestPositive(values, fallback) {
  const filtered = values.filter((item) => typeof item === "number" && item >= 0);
  return filtered.length ? Math.min(...filtered) : fallback;
}

async function loadRenderedText(url) {
  const virtualConsole = new VirtualConsole();
  virtualConsole.on("jsdomError", () => {});
  const dom = await JSDOM.fromURL(url, {
    resources: "usable",
    runScripts: "dangerously",
    pretendToBeVisual: true,
    virtualConsole,
  });
  await sleep(5000);
  const text = normalizeText(dom.window.document.body.textContent || "");
  dom.window.close();
  return text;
}

async function postDaycolorHtml(targetDate) {
  const response = await fetch("https://gogo.mn/horoscope/daycolor", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
      "X-Requested-With": "XMLHttpRequest",
    },
    body: new URLSearchParams({ date: targetDate }).toString(),
  });

  if (!response.ok) {
    throw new Error(`daycolor_http_${response.status}`);
  }

  return response.text();
}

function populateSummaryActions(info) {
  const block = info.summary || info.block || "";

  const explicitGoodActivitiesMatch = block.match(/Эл өдөр\s+(.+?)\s+сайн\./u);
  if (explicitGoodActivitiesMatch) {
    info.good_activities = normalizeText(explicitGoodActivitiesMatch[1]);
  }

  const explicitCautionMatch = block.match(/Эл өдөр\s+.+?\s+сайн\.\s+(.+?)\s+муу\./u);
  if (explicitCautionMatch) {
    info.caution = normalizeText(explicitCautionMatch[1]);
  }

  if (info.good_activities && info.caution) {
    return;
  }

  const sentences = block
    .split(".")
    .map((item) => normalizeText(item))
    .filter(Boolean);

  if (!info.good_activities) {
    const goodSentence = sentences.find(
      (item) =>
        item.includes("сайн") &&
        !item.includes("аливаа үйлийг хийхэд эерэг сайн") &&
        !item.includes("сөрөг муу нөлөөтэй"),
    );
    if (goodSentence) {
      info.good_activities = normalizeText(
        goodSentence
          .replace(/^Эл өдөр\s+/u, "")
          .replace(/^Үл зохилдох\s+/u, "")
          .replace(/\s+сайн$/u, ""),
      );
    }
  }

  if (!info.caution) {
    const cautionSentence = sentences.find((item) => item.includes("муу"));
    if (cautionSentence) {
      info.caution = normalizeText(cautionSentence.replace(/\s+муу$/u, ""));
    }
  }
}

function parseCalendar(text) {
  const start = text.indexOf("Билгийн тооллын");
  if (start < 0) {
    throw new Error("calendar_block_not_found");
  }

  const end = smallestPositive(
    [
      text.indexOf("Шинэ мэдээ", start),
      text.indexOf("Онцлох мэдээ", start),
      text.indexOf("Тренд мэдээ", start),
    ],
    text.length,
  );
  const block = normalizeText(text.slice(start, end));

  const info = {
    source_url: "https://gogo.mn/horoscope",
    block,
  };

  const dateMatch = block.match(
    /Билгийн тооллын\s+(\d+)\s+(\d{4}\.\d{2}\.\d{2})\s*\/\s*([А-Яа-яӨөҮүЁё]+)\s+гараг\s+(.+?)\s+Үс засуулвал:\s*(.+?)\s+Наран ургах,\s*шингэх:\s*([0-9\.\-]+)/u,
  );
  if (dateMatch) {
    info.bilgiin_day = dateMatch[1];
    info.gregorian_date = dateMatch[2];
    info.weekday = dateMatch[3];
    info.lunar_day_text = normalizeText(dateMatch[4]);
    info.haircut_omen = normalizeText(dateMatch[5]);
    info.sun_times = normalizeText(dateMatch[6]);
  }

  const summaryMatch = block.match(/Аргын тооллын\s+.+$/u);
  if (summaryMatch) {
    info.summary = normalizeText(summaryMatch[0]);
  }

  const goodTimesMatch = block.match(/Өдрийн сайн цаг нь\s+(.+?)\s+болой\./u);
  if (goodTimesMatch) {
    info.good_times = normalizeText(goodTimesMatch[1]);
  }

  const travelMatch = block.match(/Хол газар яваар одогсод\s+(.+?)\./u);
  if (travelMatch) {
    info.travel = normalizeText(travelMatch[1]);
  }

  const haircutLineMatch = block.match(/Үс шинээр үргээлгэх буюу засуулахад\s+(.+?)\./u);
  if (haircutLineMatch) {
    info.haircut_line = normalizeText(haircutLineMatch[1]);
  }

  populateSummaryActions(info);

  return info;
}

function parseWesternToday(text, targetDate) {
  const dateSlash = targetDate.replace(/-/g, "/");
  const stopPattern =
    "(?:Өнөөдөр\\s+\\d{4}/\\d{2}/\\d{2}|Маргааш\\s+\\d{4}/\\d{2}/\\d{2}|Даваа\\s+\\d{4}/\\d{2}/\\d{2}|Мягмар\\s+\\d{4}/\\d{2}/\\d{2}|Лхагва\\s+\\d{4}/\\d{2}/\\d{2}|Пүрэв\\s+\\d{4}/\\d{2}/\\d{2}|Баасан\\s+\\d{4}/\\d{2}/\\d{2}|Бямба\\s+\\d{4}/\\d{2}/\\d{2}|Ням\\s+\\d{4}/\\d{2}/\\d{2}|Өнөөдөр\\s+Энэ\\s+долоо\\s+хоног|Шинэ мэдээ|Онцлох мэдээ|Тренд мэдээ)";
  const regex = new RegExp(`Өнөөдөр\\s+${dateSlash}\\s+(.+?)(?=${stopPattern})`, "gu");
  const paragraphs = [];

  for (const match of text.matchAll(regex)) {
    const value = normalizeText(match[1]);
    if (value) {
      paragraphs.push(value);
    }
  }

  if (paragraphs.length < ZODIAC_SIGNS.length) {
    throw new Error(`western_today_entries_too_few:${paragraphs.length}`);
  }

  const entries = ZODIAC_SIGNS.map((sign, index) => ({
    sign,
    text: paragraphs[index],
  }));

  return {
    source_url: "https://gogo.mn/horoscope/western/today",
    source_date: dateSlash,
    entries,
  };
}

function parseWesternWeek(text) {
  const start = text.indexOf("Энэ долоо хоногт (");
  if (start < 0) {
    throw new Error("western_week_block_not_found");
  }

  const tail = text.slice(start);
  const rawParts = tail.split(/Энэ\s+долоо\s+хоногт\s+\(/u).slice(1);
  const entries = [];
  const weeklyStopPattern =
    /(?:Шинэ мэдээ|Онцлох мэдээ|Тренд мэдээ|Өнөөдөр\s+Энэ\s+долоо\s+хоног|Өнөөдөр\s+Энэ\s+долоо\s+хоног\s+Энэ\s+сар|Энэ\s+сар\s+Энэ\s+жил|Зан\s+байдал|Амжилт\s+бүтээл|Эрүүл\s+мэнд|Ажил\s+мэргэжил|Хайр\s+дурлал,\s*гэр\s+бүл|Эрэгтэй|Эмэгтэй|Зохицол\s+нийцэл|Махбод).*$/u;

  for (const rawPart of rawParts) {
    const closingIdx = rawPart.indexOf(")");
    if (closingIdx < 0) {
      continue;
    }
    const dateRange = normalizeText(rawPart.slice(0, closingIdx));
    let body = normalizeText(rawPart.slice(closingIdx + 1));
    body = normalizeText(body.replace(weeklyStopPattern, ""));
    if (dateRange && body) {
      entries.push({ date_range: dateRange, text: body });
    }
  }

  if (entries.length < ZODIAC_SIGNS.length) {
    throw new Error(`western_week_entries_too_few:${entries.length}`);
  }

  return {
    source_url: "https://gogo.mn/horoscope/western/week",
    source_range: entries[0].date_range,
    entries: ZODIAC_SIGNS.map((sign, index) => ({
      sign,
      text: entries[index].text,
    })),
  };
}

function parseCalendarDayHtml(html, targetDate) {
  const virtualConsole = new VirtualConsole();
  virtualConsole.on("jsdomError", () => {});
  const dom = new JSDOM(`<body>${html}</body>`, { virtualConsole });
  const block = normalizeText(dom.window.document.body.textContent || "");
  dom.window.close();

  if (!block) {
    throw new Error("calendar_day_block_not_found");
  }

  const info = {
    source_url: "https://gogo.mn/horoscope",
    source_endpoint: "https://gogo.mn/horoscope/daycolor",
    source_date: targetDate,
    block,
  };

  const dateMatch = block.match(
    /Билгийн тооллын\s+(\d+)\s+(\d{4}\.\d{2}\.\d{2})\s*\/\s*([А-Яа-яӨөҮүЁё]+)\s+гараг\s+(.+?)\s+Үс засуулвал:\s*(.+?)\s+Наран ургах,\s*шингэх:\s*([0-9\.\-]+)/u,
  );
  if (dateMatch) {
    info.bilgiin_day = dateMatch[1];
    info.gregorian_date = dateMatch[2];
    info.weekday = dateMatch[3];
    info.lunar_day_text = normalizeText(dateMatch[4]);
    info.haircut_omen = normalizeText(dateMatch[5]);
    info.sun_times = normalizeText(dateMatch[6]);
  }

  const summaryMatch = block.match(/Аргын тооллын\s+.+$/u);
  if (summaryMatch) {
    info.summary = normalizeText(summaryMatch[0]);
  }

  const goodTimesMatch = block.match(/Өдрийн сайн цаг нь\s+(.+?)\s+болой\./u);
  if (goodTimesMatch) {
    info.good_times = normalizeText(goodTimesMatch[1]);
  }

  const travelMatch = block.match(/Хол газар яваар одогсод\s+(.+?)\./u);
  if (travelMatch) {
    info.travel = normalizeText(travelMatch[1]);
  }

  const haircutLineMatch = block.match(/Үс шинээр үргээлгэх буюу засуулахад\s+(.+?)\./u);
  if (haircutLineMatch) {
    info.haircut_line = normalizeText(haircutLineMatch[1]);
  }

  populateSummaryActions(info);

  return info;
}

async function main() {
  if (!MODE) {
    throw new Error("missing_mode");
  }
  if (!TARGET_DATE) {
    throw new Error("missing_target_date");
  }

  if (MODE === "calendar") {
    const text = await loadRenderedText("https://gogo.mn/horoscope");
    process.stdout.write(`${JSON.stringify(parseCalendar(text), null, 2)}\n`);
    return;
  }

  if (MODE === "western_today") {
    const text = await loadRenderedText("https://gogo.mn/horoscope/western/today");
    process.stdout.write(`${JSON.stringify(parseWesternToday(text, TARGET_DATE), null, 2)}\n`);
    return;
  }

  if (MODE === "western_week") {
    const text = await loadRenderedText("https://gogo.mn/horoscope/western/week");
    process.stdout.write(`${JSON.stringify(parseWesternWeek(text), null, 2)}\n`);
    return;
  }

  if (MODE === "calendar_day") {
    const html = await postDaycolorHtml(TARGET_DATE);
    process.stdout.write(`${JSON.stringify(parseCalendarDayHtml(html, TARGET_DATE), null, 2)}\n`);
    return;
  }

  throw new Error(`unsupported_mode:${MODE}`);
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : String(error)}\n`);
  process.exit(1);
});
