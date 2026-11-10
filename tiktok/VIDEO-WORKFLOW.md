# TikTok prep: workflow

Turns raw roulette takes into finished, ready-to-post videos for @nielparle. You record, drop the
clips in a folder, and pick finished videos out of another folder to upload anywhere (TikTok,
Instagram, YouTube Shorts). No editing in the app.

## Folders (`video-content/`, in the main checkout, never in git)

| folder               | what's in it                                                                 |
|----------------------|------------------------------------------------------------------------------|
| `unused footage/`    | every clip you record, straight off the phone                                |
| `used footage/`      | clips that are finished with (moved there automatically after posting)       |
| `reference footage/` | videos that went live; used to know which prompts are already done            |
| `ready/jour-<N>/<n>-…/`| one folder per video: `caption.txt`, `edit.json` (and `video.mp4`, `captions.srt` from the render route) |
| `.work/`             | caches (screen readings, audio, fonts); safe to delete                        |

What's kept in git is [`ledger.json`](ledger.json): every prompt that's been posted, so a prompt is
never used twice. Parlons is only read from, never changed.

## Daily routine

1. Drop new clips into `unused footage/`, then `npm run tiktok -- scan`. It reads the laptop screen in
   every clip (Apple's text recognition) and finds each take: from the roulette spin that landed on
   the prompt to the end of the timer. Spins you skipped, timers you stopped early (under 20 s),
   prompts already posted and repeats in the backlog are left out.
2. Ask Claude: **"prep the TikToks"** (or run `npm run tiktok -- next 2 --day 83`, after confirming
   the Jour number, see below). That makes one folder per video in `ready/<today>/`, numbered N° 1, N° 2, … and transcribes it (Whisper, offline).
3. **Captions check.** Claude goes through `edit.json`: fixes Whisper's mishearings (your own French
   stays exactly as you said it), notes corrections for later (hidden while `caption.corrections`
   is 0 in `VIDEO-DESIGN.md`), and writes the comment question. You
   get a short list of the corrections in chat; say "ok" or change any of them. To read it yourself:
   `npm run tiktok -- review`.
4. `npm run tiktok -- render ready/<date>/<folder>` burns everything in (about 3–4 minutes a video).
5. Upload `video.mp4`, paste `caption.txt`. Then `npm run tiktok -- posted ready/<date>/<folder>`
   logs the prompt and moves the clip to `used footage/` once all its takes are used.

`npm run tiktok -- backlog` shows what's left. Don't like a take? `npm run tiktok -- skip <folder>`
and it's never offered again. Posted the day's first video from the app? `next 1 --number 2` makes
the next one N° 2.

### Which Jour number? Always confirm first

Jour numbers follow **posting**, not the calendar: some days there's no post, or only one. The
ledger remembers the last posted number (`npm run tiktok -- day` shows it; `day 90` sets it if you
posted without the tool) and the next video is that + 1. The number is burned into the video, so it
is **never guessed**: `edits` and `next` refuse to run without `--day N`. Whoever runs this (you,
Claude, Codex) first says "next is Jour 83, right?" and waits for a yes. `posted` moves the last
number forward.

### In Edits (Instagram's editor on the Mac)

Keep Edits open (its automation setting on), then ask Claude: **"prep the TikToks in Edits"**.
Claude confirms the Jour number with you first (see above).

1. `npm run tiktok -- edits 6 --day 83` makes one Edits project per take, two per Jour from 83 (so 6
   takes = Jour 83, 84, 85), each named for the Jour it goes out: `Jour 83 · N°1 · prompt`,
   `Jour 83 · N°2 · …`. Folders are `ready/jour-83/…`.
   Each has the clip cut from the roulette spin to 2 s after your last word (past the timer if you
   kept talking), the Jour title in Advercase with the English line under it, "exercices de
   spontanéité", and French captions from Edits' own auto-captions (free, and exactly what you
   said), small and just above the laptop. `--per-day 1` for one a day.
2. Claude reads the captions in `ready/jour-<N>/<folder>/edit.json`, writes the English under each
   line (what you meant, short, natural English, in pale yellow so it reads apart from the white
   French) and fixes only words Edits misheard.
3. `npm run tiktok -- english <folder>` puts the English lines into the project and writes
   `caption.txt` next to it, ready to paste:
   `Jour N de publications jusqu'à ce que je parle couramment français. 🇫🇷 <prompt>`, then
   `Exercices de spontanéité`, then 5 hashtags (`#apprendrelefrançais #français #francophone` plus
   two about the prompt's topic, from `hashtags` in `edit.json`). `npm run tiktok -- caption
   <folder>` rewrites just the caption. The fixed parts are `POST` in [`edits.py`](edits.py).
4. Check the project in Edits, export or post from there, then `npm run tiktok -- posted <folder>`.

Edits can only open files in `~/Movies`, so clips are hard-linked into `~/Movies/nielparle` (no
extra disk space). The look (fonts, sizes, positions) is `LOOK` in [`edits.py`](edits.py).

#### For an AI agent doing this (Claude, Codex, …)

"Prep the TikToks in Edits" means:

1. Check Edits is reachable: `.venv/bin/python tiktok/edits_client.py` prints `"home"` or
   `"editor"`. If it can't connect, ask for Edits to be opened. Outside Claude Code, set
   `EDITS_URL` (e.g. `http://127.0.0.1:19501/mcp`) and `EDITS_TOKEN` from Edits' connect command.
2. New clips in `unused footage/`? Run `npm run tiktok -- scan`. Then `npm run tiktok -- backlog`.
   **Ask him which Jour number to start at** (`npm run tiktok -- day` shows last posted + 1: say
   "next is Jour 83, right?") and wait for his yes. Never guess it. Then build what's asked:
   `npm run tiktok -- edits <N> --day <D>` (two per Jour; `--per-day 1` if he posts once a day).
3. For each new folder in `ready/jour-<N>/`, edit `edit.json` → `captions[]`:
   - `fr`: leave it as `heard`, except words the caption model clearly misheard (nonsense, or
     the on-screen prompt read aloud wrongly). **Never correct his French**: grammar mistakes,
     restarts and "euh" stay. Mistakes are left on purpose so native speakers correct them in
     the comments.
   - `en`: what he meant, in natural, casual English, one line per caption, about 45 characters
     at most (longer lines wrap onto the laptop). Keep hesitations light ("uh…"). Not word for
     word.
   - `hashtags`: two hashtags about the prompt's topic, in French (e.g. `["#cinéma", "#films"]`).
4. `npm run tiktok -- english <folder>` for each (it also writes `caption.txt`), then list the
   projects for review. Don't
   export or post: he reviews in Edits first.
5. After he posts one: `npm run tiktok -- posted <folder>`. If he says a prompt went out
   without the tool, add it to `tiktok/ledger.json` → `covered` so it's never built again.

### Going back to the app

`render <folder> --clean` also writes `clean.mp4`: the same cut with no text. Upload that, paste
`caption.txt`, and add text and auto-captions in TikTok as before. `captions.srt` has the corrected
captions if a platform takes subtitle files (YouTube does).

## Design

Everything about how the videos look (colours, fonts, sizes, timings, the words on the cards) lives
in [`VIDEO-DESIGN.md`](VIDEO-DESIGN.md). The renderer reads it on every render, so edit it there.
What the project is for: [`VIDEO-PROJECT.md`](VIDEO-PROJECT.md).

## Setup (once per machine)

```
npm install
npm run tiktok:setup
```

Needs macOS (Apple text recognition, `swiftc`). Whisper's `large-v3-turbo` model (~1.6 GB)
downloads on first use. The parlons prompt bank is read with its public key from `~/parlons/.env`,
or from `PARLONS_SUPABASE_URL` / `PARLONS_SUPABASE_KEY`; it's only used to spell a prompt exactly.
