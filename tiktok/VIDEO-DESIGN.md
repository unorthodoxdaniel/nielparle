# Video design guidelines

The source of truth for how @nielparle videos look. The renderer (`tiktok/render.py`) reads the values in
the block below every time it runs, so **editing a value here changes the next render**. The rest of
this file explains the decisions and rules behind those values.

If you find a better design somewhere, change it here first. Small changes (a colour, a size, a
timing, a line of text) only need this file. Bigger changes (a new kind of card, moving captions to
another place, a new animation) need `render.py` too: ask Claude to "update the video design to match
VIDEO-DESIGN.md", and update the rules below so they stay true.

## Values

Edit the right-hand side. Colours are hex without `#`, sizes are pixels on the 1080×1920 frame,
times are seconds unless they end in `_ms`. `\n` in a text is a line break.

```tokens
# Colours (the nielparle.com palette)
colour.paper: f7f5f0
colour.ink: 181818
colour.muted: 6f6c66
colour.accent: d8492f
colour.accent_text: bd3c26
colour.caption_dim: bdb9b0

# Fonts (installed on macOS)
font.serif: Georgia
font.sans: Arial

# Type sizes
size.eyebrow: 23
size.eyebrow_spacing: 3.5
size.day: 108
size.line: 34
size.big: 46
size.caption: 52
size.caption_outline: 3.0
size.tag: 32

# Layout
layout.card_x: 170
layout.card_w: 740
layout.card_y: 185
layout.card_padding_top: 44
layout.card_padding_bottom: 30
# captions sit this many px above the laptop screen (found per clip); caption_y is the fallback
layout.caption_above_screen: 95
layout.caption_y: 935
layout.caption_margin: 150
layout.rule_w: 140
layout.rule_h: 3

# Timing
time.day_card: 4.0
time.plug_card: 4.0
time.like_at: 0.42
time.like_card: 3.6
time.comment_card: 6.0
time.fade_in_ms: 250
time.fade_out_ms: 300
time.rise: 18
time.rule_draw_ms: 500
time.fix_hold: 1.4

# Captions
# corrections: 1 shows correction tags (said → better) above captions, 0 hides them
caption.corrections: 0
caption.max_chars: 30
caption.question_wrap: 28

# Words on screen
text.format: EXERCICES DE SPONTANÉITÉ
text.of_day: N° {n} DU JOUR
text.day: Jour {day}
text.day_line: de publications jusqu'à ce que je\nparle couramment français.
text.plug_eyebrow: ENVIE D'ESSAYER ?
text.plug_big: parlons.nielparle.com
text.plug_small: GRATUIT  ·  AUSSI EN ANGLAIS
text.like_eyebrow: SI ÇA T'A PLU
text.like_big: Un petit like, et abonne-toi\npour la suite !
text.comment_eyebrow: DIS-LE EN COMMENTAIRE
text.comment_default: Et toi, tu aurais répondu quoi ?

# Post caption (caption.txt)
post.hashtags: #apprendrelefrançais #français #apprentissage #francophone #parlerfrançais
post.plug: Tu veux essayer ? parlons.nielparle.com (aussi en anglais)

# HDR: how bright "paper" is in the HLG picture. 0.75 = HLG reference white, 1.0 = full HDR peak
# (TikTok's own text sits at peak; a whole card at peak glares on HDR phones)
hdr.white_level: 0.8
```

## The idea

The videos should look like nielparle.com: editorial, calm, paper and ink. Not app-like, not
"TikTok-y". Text supports the speaking; it never competes with it. Everything on screen is either
**information the viewer can't get from the picture** or **a reason to keep watching or come back**.

## Rules

### Brand
- Same palette as the website: warm paper, near-black ink, muted grey, one restrained red.
- **Georgia** (serif) for anything to be read as a title: the day, the card headlines, questions.
  **Arial** (sans) for captions, labels and tags.
- Labels ("eyebrows") are uppercase, letter-spaced, small and muted, like the site's `.eyebrow`.
- A short red **rule** is the only decoration. No icons, emoji, gradients, rounded boxes or shadows.

### Contrast (checked against the light wall and the brown wardrobe)
- Cards are **ink on paper** (about 17:1), so they read on any background.
- Red **text** only appears on paper, in the darker red `accent_text` (about 5:1). The bright
  `accent` red is only used for rules, never for text.
- Captions are paper-coloured with an ink outline, so they read on both the wall and a dark shirt.
- Never put text straight on the footage without an outline or a card behind it.

### Two places for text, nothing else
1. **The card slot (top).** One paper card at a time, in this order:
   1. 0–4 s: the **day card**: eyebrow (`N° 2 DU JOUR · EXERCICES DE SPONTANÉITÉ`; the `N°` part only
      from the second video of a day), **Jour N** large, red rule, the series line in italics.
   2. Right after: the **parlons card**: where the roulette on the laptop comes from.
   3. About 42 % in: **like + follow**. Late enough that people are invested, early enough that most
      are still watching. Skipped if the video is too short to keep it apart from the next card.
   4. Last 6 s: the **comment question**, specific to the prompt (written per video during the
      captions check). A question people can answer in a few words gets more comments.
2. **The caption slot (just above the laptop).** Captions, and correction tags just above them.
   The camera framing changes between recordings, so the laptop's position is found in each clip
   (from the app's header on screen) and the captions sit `caption_above_screen` px above it.

The prompt is **not** shown as text: it's already readable on the laptop. Repeating it would be clutter.

### Captions
- Exactly what was said, mistakes included, with only Whisper's mishearings fixed. Pauses and
  restarts can stay.
- Short lines (about 34 characters), broken at sentences and pauses. A lone word is joined to the
  next line when they're close.
- **Words light up as they're spoken** (dim until said, then paper). Keeps eyes on the text and
  helps learners follow.
- Lines never overlap: a line ends when the next one starts.

### Corrections: off for now
- **Currently off** (`caption.corrections: 0`). Mistakes are left in so native speakers feel invited
  to correct them in the comments, and so an AI-written correction that sounds unnatural can never
  end up on screen.
- The captions check still records corrections in `edit.json` (as `fix`), so turning them back on
  later needs no extra work, just `caption.corrections: 1`.
- When on: a small **paper tag** above the caption: ~~what was said~~ → **better** (dark red), with an
  optional short note; at most one per caption line, about 3–5 per video, only real mistakes
  (grammar, agreement, faux amis, prepositions), never spoken-French habits like `c'est les…`.

### Motion
- Cards and tags **fade in while rising** a few pixels; they fade out in place. Short (a quarter
  second), never bouncy.
- The red rule **draws itself** from the left as the card appears.
- Nothing moves while it's being read.

### Safe area
TikTok's own buttons and text cover about the top 150 px, the right 140 px and the bottom 380 px of
the 1080×1920 frame. Cards sit from y = 185, captions wrap within a 150 px margin on each side, and
the bottom of the frame is left to the laptop.

### Picture and sound
- **Brightness.** Measured on posted videos: TikTok draws its own text at full HDR peak; the wall
  sits around 57 % signal. Paper is set to 80 %: brighter than the wall, without a glaring card.
- **HDR is kept.** The iPhone records HLG HDR and TikTok keeps it, so the footage is never converted;
  text is drawn into the HDR picture with colours converted to match (`hdr.white_level`).
- No filters, no colour grade, no music. Audio as recorded.
- The cut: from the roulette spin that lands on the prompt to just after the last word (never past
  the timer). Skipped spins and takes where the timer was stopped early are left out.

### Post caption (`caption.txt`)
`Jour N de publications jusqu'à ce que je parle couramment français. 🇫🇷 Exercices de spontanéité :
« prompt »`, then the comment question, the parlons line and up to five hashtags.

## Changelog

Record design changes here so the reason isn't lost.

- **2026-10-27**: Captions placed per clip just above the laptop (framing varies). Paper raised from
  HLG reference white (75 %) to 80 %.
- **2026-10-27**: Correction tags turned off: let native speakers do the correcting in the comments
  (engagement), and avoid unnatural AI corrections on screen.
- **2026-10-27**: First version. The prompt was dropped from the screen (the laptop shows it). All
  text moved to ink-on-paper cards after contrast checks on the wall. Red text limited to the darker
  red. Karaoke captions and correction tags added for retention.
