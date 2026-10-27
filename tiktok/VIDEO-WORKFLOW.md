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
| `ready/<date>/<n>-…/`| one folder per finished video: `video.mp4`, `caption.txt`, `captions.srt`    |
| `.work/`             | caches (screen readings, audio, fonts); safe to delete                        |

What's kept in git is [`ledger.json`](ledger.json): every prompt that's been posted, so a prompt is
never used twice. Parlons is only read from, never changed.

## Daily routine

1. Drop new clips into `unused footage/`, then `npm run tiktok -- scan`. It reads the laptop screen in
   every clip (Apple's text recognition) and finds each take: from the roulette spin that landed on
   the prompt to the end of the timer. Spins you skipped, timers you stopped early (under 20 s),
   prompts already posted and repeats in the backlog are left out.
2. Ask Claude: **"prep today's TikToks"** (or run `npm run tiktok -- next 2`). That makes one folder
   per video in `ready/<today>/`, numbered N° 1, N° 2, … and transcribes it (Whisper, offline).
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
