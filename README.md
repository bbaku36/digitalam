# Facebook Auto Post (Daily Slot Schedule + Weekly)

This project auto-posts Mongolian Facebook content with fixed time slots:
- `insight`: ухаарал болон урам өгөх үгс
- `horoscope`: өглөөний уламжлалт өдрийн зурхай (`Өнөөдөр ...` нээлт + ерөнхий төлөв/үс засуулах/аян зам/үйл хийх/цээрлэх)
- `zodiac_horoscope`: 12 ордын дэлгэрэнгүй өдрийн зурхай (intro + орд бүрийн heading/date range + богино paragraph)
- `daily_guidance`: өдрийн үйл (үс засуулах/аян замд гарах/үйл хийх/цээрлэх зүйл), хүсвэл гараар ажиллуулж болно
- `mantra`: daily mantra/meditation post
- `fact`: interesting religion/Buddhist facts
- `messenger_cta`: Messenger дээр асуулт авах CTA пост
- `evening_insight`: оройн богино ухаарал
- `tomorrow_prep`: маргаашийн бэлтгэл (1 зөвлөмж + ерөөл)
- `goodnight`: богино амгалан шөнийн пост
- `weekly`: 7 хоногийн зөвлөмж (үс засуулах өдөр + хол замд гарах өдөр + үйл хийх өдөр), manual/optional category
- `weekly_horoscope`: 7 хоногт 1 удаа `gogo.mn`-ийн өдөр тутмын эх сурвалж дээр суурилсан 7 хоногийн `үс засуулах / аян зам / үйл хийх` тойм

## Files

- `scripts/generate_and_post.py`: CLI entrypoint
- `scripts/autopost/runner.py`: main orchestration flow
- `scripts/autopost/content.py`: category content builders (AI-first, fallback code kept only as explicit opt-in)
- `scripts/autopost/schedule.py`: timeslot/category rules
- `scripts/autopost/facebook.py`: Facebook post API
- `scripts/autopost/state.py`: `.state` persistence helpers
- `scripts/autopost/env.py`: env/flag/timezone helpers
- `scripts/autopost/constants.py`: static content and category constants
- `.env.example`: environment template
- `.state/*.json`: posting state (auto-created)

## Quick start

1. Create env file:
   ```bash
   cp .env.example .env
   ```
2. Fill `.env`:
   - `FACEBOOK_PAGE_ID`
   - `FACEBOOK_PAGE_ACCESS_TOKEN`
   - `DEEPSEEK_API_KEY` and `AI_PROVIDER=deepseek`
3. Test in dry run mode:
   ```bash
   DRY_RUN=1 python3 scripts/generate_and_post.py
   ```
4. Run live post:
   ```bash
   DRY_RUN=0 python3 scripts/generate_and_post.py
   ```

## GitHub Actions (computer off байсан ч ажиллана)

1. Push this project to a GitHub repository.
2. In GitHub, open:
   `Settings -> Secrets and variables -> Actions -> New repository secret`
3. Add these secrets:
   - `FACEBOOK_PAGE_ID` (required)
   - `FACEBOOK_PAGE_ACCESS_TOKEN` (required)
   - `DEEPSEEK_API_KEY` (required for scheduled posting)
4. Ensure workflow file exists:
   - `.github/workflows/facebook-autopost.yml`
   - `.github/workflows/facebook-weekly-horoscope.yml` (optional weekly day-by-day almanac summary post)
5. Run once manually:
   - `Actions -> Facebook Auto Post -> Run workflow`
   - `force_slot_hour=8` өгвөл `08:00`-ийн `zodiac_horoscope` post-ийг шууд ажиллуулж болно
   - `post_category=zodiac_horoscope` өгвөл category-г шууд override хийж болно

After that, it runs automatically by schedule (Ulaanbaatar 06:00, 08:00, 14:00, 18:00, 22:00).

### Schedule note

- Workflow cron is split into separate UTC schedules:
  - `0 22 * * *` -> `06:00`
  - `0 0 * * *` -> `08:00`
  - `0 6 * * *` -> `14:00`
  - `0 10 * * *` -> `18:00`
  - `0 14 * * *` -> `22:00`
- Mongolia is UTC+8, so runs at: 06:00, 08:00, 14:00, 18:00, 22:00 (Ulaanbaatar time)
- Time slot map:
- `06:00` -> `horoscope`
- `08:00` -> `zodiac_horoscope`
  - `14:00` -> `insight`
  - `18:00` -> `fact`
  - `22:00` -> `tomorrow_prep`
- Scheduled run хоцорч эхэлсэн ч `github.event.schedule`-оор нь зөв category сонгодог.

## Category control

- Default mode: schedule-based category (`USE_TIME_SLOT_SCHEDULE=1`)
- Override category for one run:
  - `POST_CATEGORY=insight|horoscope|zodiac_horoscope|daily_guidance|mantra|fact|messenger_cta|evening_insight|tomorrow_prep|goodnight|weekly|weekly_horoscope`
  - Backward compatibility: `POST_CATEGORY=news` автоматаар `insight` гэж ойлгоно
- Slot test хийхдээ: `FORCE_SLOT_HOUR=6` (0-23)
- Optional category rotation (only when schedule mode is off):
  - `USE_TIME_SLOT_SCHEDULE=0`
  - `AUTO_CATEGORIES=insight,mantra,fact,horoscope`
- Pin controls:
  - Auto-pin workflow болон scheduled auto-pin оролдлого GitHub Actions дээр унтраалттай
  - Хэрэв дараа нь pin хэрэгтэй бол Page UI дээрээс гараар pin хийнэ

## Gemini Failure Alerts

- `ALERT_ON_GEMINI_FAILURE=1` үед Gemini generation алдагдвал alert trigger хийнэ.
- Alert channel:
  - `ALERT_WEBHOOK_URL` (generic webhook)
  - эсвэл `ALERT_TELEGRAM_BOT_TOKEN` + `ALERT_TELEGRAM_CHAT_ID`
- `ALERT_ON_DRY_RUN=0` default тул dry-run дээр alert явуулахгүй.

## Notes

- Script tracks posting history in `.state/` (e.g., `posted_items.json`, `post_meta.json`).
- In GitHub Actions, `.state/` is cached between runs to keep posting metadata.
- Facebook API permissions must allow posting to the target Page.
- If `DEEPSEEK_API_KEY` is set (with `AI_PROVIDER=deepseek`), each category content is generated via `deepseek-chat`.
- DeepSeek Chat is now the default provider; Gemini remains as an optional alternative.
- Default behavior is `REQUIRE_AI_CONTENT=1`: AI generation fail үед fallback руу унахгүй, run алдаатай зогсоно.
- Хэрэв fallback-ийг зориуд ашиглах шаардлагатай бол зөвхөн explicit байдлаар `REQUIRE_AI_CONTENT=0` гэж өгч асаана.
- `06:00`, `08:00`, мөн `weekly_horoscope` нь эхлээд `gogo.mn`-оос source facts татаж, дараа нь AI-аар rewrite хийдэг.
- `weekly_horoscope` нь `https://gogo.mn/horoscope/daycolor` endpoint-оос Даваа-Нямын 7 өдрийн мэдээллийг тус бүр авч нэг weekly summary болгодог.
- Node dependency хэрэгтэй тул local болон CI дээр `npm ci` ажиллуулна.
