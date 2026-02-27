# Facebook Auto Post (2-hour cadence, Global Tech + AI)

This project collects recent global technology and AI headlines from RSS feeds,
translates them into Mongolian, creates a Facebook-ready Mongolian summary, and posts it to a Facebook Page.

## Files

- `scripts/generate_and_post.py`: main script
- `.env.example`: environment template
- `.state/posted_items.json`: dedupe state (auto-created)

## Quick start

1. Create env file:
   ```bash
   cp .env.example .env
   ```
2. Fill `.env`:
   - `FACEBOOK_PAGE_ID`
   - `FACEBOOK_PAGE_ACCESS_TOKEN`
   - (Recommended) `OPENAI_API_KEY` for higher-quality Mongolian wording
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
   - `OPENAI_API_KEY` (optional but recommended)
4. Ensure workflow file exists:
   - `.github/workflows/facebook-autopost.yml`
5. Run once manually:
   - `Actions -> Facebook Auto Post -> Run workflow`

After that, it runs every 2 hours automatically by schedule.

### Schedule note

- Workflow cron is UTC: `0 */2 * * *`
- Mongolia is UTC+8, so runs at: 00:00, 02:00, 04:00, ... , 22:00 (Ulaanbaatar time)

## Notes

- Script tracks previously posted links in `.state/posted_items.json` to avoid repeats.
- In GitHub Actions, `.state/posted_items.json` is cached between runs for dedupe.
- If no fresh items are found, it falls back to top unposted items.
- Facebook API permissions must allow posting to the target Page.
- If `OPENAI_API_KEY` is set, headlines are rewritten with AI for more natural Mongolian.
- If `OPENAI_API_KEY` is missing or API fails, script falls back to basic machine translation.
