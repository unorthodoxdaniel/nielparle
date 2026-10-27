"""Renders one TikTok from its edit.json: titles, captions, corrections and CTAs, burned in.

The footage stays HDR (BT.2020 HLG, like the iPhone recorded it and like TikTok keeps it).
Text is drawn straight into the HLG picture with colours converted to HLG, so nothing is
tone-mapped and the footage looks exactly as recorded.
"""
import shutil
import subprocess
from pathlib import Path

W, H = 1080, 1920
DESIGN_FILE = Path(__file__).with_name("VIDEO-DESIGN.md")
FONT_DIRS = [Path("/System/Library/Fonts/Supplemental"), Path("/System/Library/Fonts"),
             Path("/Library/Fonts"), Path.home() / "Library" / "Fonts"]


def design():
    """Values from the ```tokens block in VIDEO-DESIGN.md (the source of truth)."""
    text = DESIGN_FILE.read_text()
    block = text.split("```tokens", 1)[1].split("```", 1)[0]
    d = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = (x.strip() for x in line.split(":", 1))
        if key.split(".")[0] in ("colour", "font", "text", "post"):
            d[key] = value.replace("\\n", "\n")
            continue
        d[key] = float(value) if "." in value else int(value)
    return d


def ts(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def esc(s):
    return s.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def srt_ts(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def wrap(text, width):
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + ([cur] if cur else [])


def karaoke(cue):
    """Words light up as they're spoken (\\k: each word turns from dim to paper when it starts).
    Falls back to plain text if the words were edited into a different count."""
    words, timed = cue["text"].split(), cue.get("words") or []
    if len(words) != len(timed):
        return esc(cue["text"])
    starts = [t[1] for t in timed]
    out = [f"{{\\k{max(0, round((starts[0] - cue['s']) * 100))}}}"]
    for i, w in enumerate(words):
        d = round((starts[i + 1] - starts[i]) * 100) if i + 1 < len(words) else 100
        out.append(f"{{\\k{max(1, d)}}}{esc(w)}{' ' if i + 1 < len(words) else ''}")
    return "".join(out)


def build_ass(edit, colour):
    D = design()
    level = D["hdr.white_level"]
    c = {k: colour(D[f"colour.{v}"], level) for k, v in dict(
        paper="paper", ink="ink", muted="muted", accent="accent", red="accent_text", dim="caption_dim").items()}
    serif, sans = D["font.serif"], D["font.sans"]
    T = lambda key, **kw: esc(D[f"text.{key}"].format(**kw))  # on-screen words
    dur = edit["source_end"] - edit["source_start"]
    timer = edit["timer_start"]
    fade_in, fade_out, rise = D["time.fade_in_ms"], D["time.fade_out_ms"], D["time.rise"]
    card_x, card_w, card_y = D["layout.card_x"], D["layout.card_w"], D["layout.card_y"]
    cap_y, margin = edit.get("caption_y") or D["layout.caption_y"], D["layout.caption_margin"]

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Eyebrow,{sans},{D['size.eyebrow']},{c['muted']},{c['muted']},{c['paper']},{c['paper']},1,0,0,0,100,100,{D['size.eyebrow_spacing']},0,1,0,0,8,0,0,0,1
Style: Day,{serif},{D['size.day']},{c['ink']},{c['ink']},{c['paper']},{c['paper']},0,0,0,0,100,100,0,0,1,0,0,8,0,0,0,1
Style: Line,{serif},{D['size.line']},{c['ink']},{c['ink']},{c['paper']},{c['paper']},0,1,0,0,100,100,0,0,1,0,0,8,0,0,0,1
Style: Big,{serif},{D['size.big']},{c['ink']},{c['ink']},{c['paper']},{c['paper']},0,0,0,0,100,100,0,0,1,0,0,8,0,0,0,1
Style: Caption,{sans},{D['size.caption']},{c['paper']},{c['dim']},{c['ink']},{c['ink']},1,0,0,0,100,100,0,0,1,{D['size.caption_outline']},0,2,{margin},{margin},0,1
Style: Tag,{sans},{D['size.tag']},{c['ink']},{c['ink']},{c['paper']},{c['paper']},1,0,0,0,100,100,0,0,3,14,0,2,{margin},{margin},0,1
Style: Shape,{sans},10,{c['paper']},{c['paper']},{c['paper']},{c['paper']},0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []

    def add(start, end, style, text, layer=1):
        if end - start > 0.05:
            ev.append(f"Dialogue: {layer},{ts(start)},{ts(end)},{style},,0,0,0,,{text}")

    def at(x, y, rise=rise, fade=(fade_in, fade_out)):
        return f"\\move({x},{y + rise},{x},{y},0,{fade_in + 100})\\fad({fade[0]},{fade[1]})"

    # row heights follow the type sizes
    def rows_h(style, text):
        n = text.count("\\N") + 1
        return {"Eyebrow": D["size.eyebrow"] * 1.74, "Day": D["size.day"] * 1.18,
                "Line": D["size.line"] * 1.24 * n, "Big": D["size.big"] * 1.26 * n}[style]

    def card(start, end, rows):
        """A paper card in the top slot. rows: (style, text, extra_tags) or ("Rule", gap)."""
        heights = [r[1] if r[0] == "Rule" else rows_h(r[0], r[1]) for r in rows]
        h = round(D["layout.card_padding_top"] + sum(heights) + D["layout.card_padding_bottom"])
        add(start, end, "Shape", f"{{{at(card_x, card_y)}\\c{c['paper']}\\p1}}m 0 0 l {card_w} 0 l {card_w} {h} l 0 {h}{{\\p0}}",
            layer=0)
        y = card_y + D["layout.card_padding_top"]
        rw, rh, draw = D["layout.rule_w"], D["layout.rule_h"], D["time.rule_draw_ms"]
        for row, height in zip(rows, heights):
            if row[0] == "Rule":  # short accent rule that draws itself from the left
                x0 = W // 2 - rw // 2
                add(start, end, "Shape", f"{{{at(x0, round(y + 8))}\\c{c['accent']}\\p1"
                    f"\\clip({x0},0,{x0},{H})\\t({fade_in},{fade_in + draw},\\clip({x0},0,{x0 + rw},{H}))}}"
                    f"m 0 0 l {rw} 0 l {rw} {rh} l 0 {rh}{{\\p0}}", layer=2)
            else:
                add(start, end, row[0], f"{{{at(W // 2, round(y))}{row[2] if len(row) > 2 else ''}}}{row[1]}", layer=2)
            y += height

    # 1. Day card: eyebrow, "Jour N", accent rule, series line
    day_end = D["time.day_card"]
    eyebrow = T("format")
    if edit.get("of_day", 1) > 1:
        eyebrow = f"{T('of_day', n=edit['of_day'])}  ·  {eyebrow}"
    card(0, day_end, [("Eyebrow", eyebrow), ("Day", T("day", day=edit["day"])), ("Rule", 30),
                      ("Line", T("day_line"))])

    # 2. Parlons card: right after, while the roulette's prompt is on the laptop below
    plug_start = day_end + 0.3
    plug_end = min(plug_start + D["time.plug_card"], max(timer + 1.5, plug_start + 3.0), dur)
    card(plug_start, plug_end, [("Eyebrow", T("plug_eyebrow")), ("Big", T("plug_big")), ("Rule", 26),
                                ("Eyebrow", T("plug_small"))])

    # 3. Like + follow: partway in, while people are still watching
    comment_start = dur - D["time.comment_card"]
    like_start = max(plug_end + 1.0, round(dur * D["time.like_at"], 2))
    if like_start + D["time.like_card"] <= comment_start - 0.5:
        card(like_start, like_start + D["time.like_card"],
             [("Eyebrow", T("like_eyebrow")), ("Big", T("like_big"), "\\i1"), ("Rule", 10)])

    # 4. Comment question: last seconds
    question = wrap(edit.get("comment") or D["text.comment_default"], D["caption.question_wrap"])
    card(comment_start, dur, [("Eyebrow", T("comment_eyebrow")), ("Big", "\\N".join(esc(l) for l in question)),
                              ("Rule", 10)])

    # 5. Captions (words light up as spoken), plus correction tags above them when switched on
    cues = edit["cues"]
    for i, cue in enumerate(cues):
        nxt = cues[i + 1]["s"] if i + 1 < len(cues) else dur
        s, e = cue["s"], min(cue["e"] + 0.15, nxt, dur)
        add(s, e, "Caption", f"{{\\pos({W // 2},{cap_y})\\fad(80,80)}}{karaoke(cue)}")
        fix = cue.get("fix") if D.get("caption.corrections", 1) else None
        if fix:
            note = f"\\N{{\\fs{round(D['size.tag'] * 0.75)}\\b0\\i1\\c{c['muted']}}}{esc(fix['note'])}" if fix.get("note") else ""
            add(s, min(e + D["time.fix_hold"], nxt + 0.6, dur), "Tag",
                f"{{{at(W // 2, cap_y - 82, rise=10, fade=(150, 250))}}}"
                f"{{\\s1\\c{c['muted']}\\b0}}{esc(fix['said'])}{{\\s0\\c{c['ink']}}}  →  {{\\b1\\c{c['red']}}}{esc(fix['better'])}{note}")

    return head + "\n".join(ev) + "\n"


def write_srt(edit, path):
    out = []
    for i, cue in enumerate(edit["cues"], 1):
        out.append(f"{i}\n{srt_ts(cue['s'])} --> {srt_ts(cue['e'] + 0.15)}\n{cue['text']}\n")
    path.write_text("\n".join(out))


def write_description(edit, path):
    D = design()
    question = edit.get("comment") or D["text.comment_default"]
    text = (f"Jour {edit['day']} de publications jusqu'à ce que je parle couramment français. 🇫🇷 "
            f"{edit['format'].capitalize()} : « {edit['prompt']} »\n\n"
            f"{question} Dis-le en commentaire 👇\n\n{D['post.plug']}\n\n{D['post.hashtags']}")
    path.write_text(text + "\n")


def render(edit, folder: Path, clip: Path, ffmpeg: Path, colour, work: Path, clean=False):
    D = design()
    fonts = work / "fonts"
    if fonts.exists():
        shutil.rmtree(fonts)
    fonts.mkdir(parents=True)
    for name in (D["font.serif"], D["font.sans"]):  # copy just the fonts the design names
        found = [f for d in FONT_DIRS if d.exists() for f in d.glob(f"{name}*") if f.suffix.lower() in (".ttf", ".otf", ".ttc")]
        if not found:
            raise SystemExit(f"Font '{name}' (VIDEO-DESIGN.md) isn't installed.")
        for f in found:
            shutil.copy(f, fonts / f.name)
    ass = folder / "overlay.ass"
    ass.write_text(build_ass(edit, colour))
    write_srt(edit, folder / "captions.srt")
    write_description(edit, folder / "caption.txt")

    def encode(out: Path, burn: bool):
        # gbrp10 keeps the HLG code values as they are while text is drawn on top
        chain = "scale=in_color_matrix=bt2020:in_range=tv,format=gbrp10le"
        if burn:
            chain += f",ass='{ass}':fontsdir='{fonts}'"
        chain += ",scale=out_color_matrix=bt2020:out_range=tv,format=yuv420p10le"
        cmd = [ffmpeg, "-loglevel", "error", "-y", "-ss", str(edit["source_start"]), "-to", str(edit["source_end"]),
               "-i", str(clip), "-vf", chain, "-c:v", "libx265", "-preset", "fast", "-crf", "18", "-tag:v", "hvc1",
               "-x265-params", "colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:log-level=error",
               "-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc",
               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
        subprocess.run([str(c) for c in cmd], check=True)

    encode(folder / "video.mp4", burn=True)
    if clean:  # for going back to the TikTok app: same cut, no text
        encode(folder / "clean.mp4", burn=False)
    print(f"  → {folder / 'video.mp4'}")
