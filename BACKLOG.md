# Backlog

Things we've decided to do later, with enough context that someone (or a fresh Claude chat) can pick them up without the original conversation. Newest thinking first within each section. Move an item to "Done" when it ships.

## Planned

### Auto-discover the latest TikTok videos

**Goal:** `npm run videos` finds the newest 6 videos for @nielparle by itself. Today you have to paste each video URL (`npm run videos -- <url>`).

**Where things live**
- `scripts/videos.mjs` fetches each video's title and cover from TikTok's official oEmbed endpoint, downloads the cover into `src/assets/videos/`, and writes `src/data/videos.json`.
- `src/components/VideoSection.astro` renders that JSON as a static strip of linked covers. Astro converts the covers to WebP at build time.

**How discovery would work**
1. Fetch `https://www.tiktok.com/embed/@nielparle?lang=fr` (the page TikTok's creator embed uses).
2. Parse the JSON inside `<script id="__FRONTITY_CONNECT_STATE__">`.
3. Read `source.data["/embed/@nielparle?lang=fr"].videoList`. Each item has `id`, `desc` and `coverUrl`; the list held 10 videos when checked.
4. Build each URL as `https://www.tiktok.com/@nielparle/video/<id>`, keep the newest 6, then reuse the existing oEmbed and cover-download steps.

**Constraints and why**
- **This data is TikTok's internal page state, not a public API.** It can change without notice and may be against their terms of use. The script must fail loudly (clear error, non-zero exit) and leave `videos.json` and the covers untouched if parsing fails or returns nothing, so a TikTok change can never break the site.
- **Titles and covers still come from oEmbed** because that endpoint is official and stable. Only the list of IDs comes from the fragile source.
- **No new dependencies.** Plain Node `fetch` and string/JSON parsing are enough.
- **The official TikTok API is ruled out.** It needs an approved app, OAuth and stored tokens, which means a backend. We chose not to add one.

**Optional follow-up: scheduled refresh.** A GitHub Action (or a Netlify build hook on a timer) that runs the script and commits any change would make the strip update with no action from you. It adds infrastructure and a bot that commits to `main`, so only do it if the manual command becomes a chore.

## Nice to have

Small items from the pre-launch QA audit. None blocks anything.

- **Back button after signing up.** The form isn't reset before it navigates to `/merci/`. In browsers that restore pages from their back/forward cache, the button could still say "Envoi…". Not reproduced. Fix: reset the form state on `pageshow`.
- **404 page metadata.** Its canonical URL points at `/404/`, which doesn't exist, and its description uses a straight apostrophe (`'`) instead of `’`.
- **Article dates and time zones.** `Intl.DateTimeFormat` in `ArticleLayout.astro` and `NotesList.astro` should get `timeZone: 'UTC'`. Dates are stored as UTC midnight, so a build machine in a US time zone would show the day before. Netlify builds in UTC, so it's harmless today.
- **Reduced motion.** `scroll-behavior: smooth` in `src/styles/global.css` should only apply under `prefers-reduced-motion: no-preference`.
- **Placeholder contrast.** The email placeholder is 4.2:1 against the background (4.5:1 is the AA target). There's a proper label, so this is minor.
- **Tiny polish:** the "→" in the subscribe button is read aloud by screen readers; the video section has two `h2`s; there's no `og:image:alt`; `--gutter` in `global.css` is unused; `README.md` is still the Astro starter text.
- **Old video covers pile up.** `scripts/videos.mjs` never deletes covers for videos that fall off the list.
- **Bot protection on the signup form.** There's none beyond what Kit does. Probably fine at this scale.
- **Privacy page and hosting logs.** `/confidentialite/` doesn't mention that Netlify (the host) keeps its own server logs. Left out on purpose because we only state what we can verify; add a line if you want it to be complete.

## Decisions we've made (and why)

Kept here so nobody reopens them by accident.

- **The homepage has no "Notes" section until an article is published.** The starter article is `draft: true`. Drafts get no route, no sitemap entry and no nav link. The section appears on its own when the first non-draft article exists.
- **Newsletter uses our own form markup, not Kit's embed.** Kit's `ck.5.js` and generated stylesheet would have overridden the site's design and shown English error text. Instead the form posts directly to Kit's public endpoint (form 9977355) with `fetch`, and shows short French messages. It still works as a normal form post if JavaScript is off. No API key or backend is involved; the form ID is public by design.
- **`/merci/` and `/bienvenue/` are `noindex` and left out of the sitemap.** They're only meaningful after signing up. They are deliberately *not* blocked in `robots.txt`, because search engines must be able to fetch a page to see its `noindex`.
- **`/confidentialite/` is indexable and in the sitemap.** A privacy page should be findable.
- **The TikTok creator embed was removed.** It showed "overload-protect" on every load, locally and in production, and we couldn't fix it from our side. The replacement is a static strip of linked covers with no third-party scripts. That also means the privacy page can truthfully say the site loads no external content. If a video embed ever comes back, update the "Services externes" section.
- **Video covers are stored in the repo,** not linked from TikTok. TikTok's cover URLs are signed and expire.
- **Umami is restricted with `data-domains="nielparle.com"`.** That makes the tracker ignore localhost and Netlify Deploy Previews. `www.nielparle.com` redirects to the apex (checked), so those visits are still counted.
- **The site is fully static** (Astro, no adapter). Nothing runs on a server, which is why anything that needs a server (an editor UI, analytics proxying, subscription handling) is deliberately handled elsewhere.

## Done

- Site identity, favicon and OG image, `robots.txt` and sitemap.
- Kit newsletter integration and the confirmation pages.
- Static video strip replacing the TikTok embed.
- Umami analytics and the privacy page.
- Pre-launch QA fixes: hero spacing, focus indicator, error contrast, hero image size and crop, small-screen heading overflow, JS-only `novalidate`.
