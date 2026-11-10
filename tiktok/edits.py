"""Builds each take as a project in Edits for Mac (Instagram's editor), instead of rendering it here.

    npm run tiktok -- edits [N] --day D [--per-day 2]     make N Edits projects, 2 a day from Jour D
    npm run tiktok -- english <folder>                    put the English lines from edit.json into Edits
    npm run tiktok -- caption <folder>                    (re)write caption.txt, the post text

What a project gets (the look of the Jour 79 reference video):
  0–3.5 s   "Jour N de publications jusqu'à ce que je parle couramment français." (Advercase)
            "Day N of posting till I speak French fluently" (small, condensed sans)
  3.5–6.5 s "exercices de spontanéité" (Advercase)
  all along French captions from Edits' own auto-captions, exactly as said, just above the laptop,
            with the English meaning under each line (written by Claude into edit.json, then `english`)

Edits must be open. It can only read files in ~/Movies, so clips are hard-linked into ~/Movies/nielparle
(no extra disk space). The look is set in LOOK below.
"""
import datetime as dt
import os
import sys
from pathlib import Path

import tiktok as t
from edits_client import Edits, EditsError

MOVIES = Path.home() / "Movies" / "nielparle"

# The post text (caption.txt), written the way he writes his own posts
POST = {
    "line": "Jour {day} de publications jusqu'à ce que je parle couramment français. 🇫🇷",
    "format": "Exercices de spontanéité",
    # always these, then the 2 topic hashtags Claude puts in edit.json "hashtags" (5 in all)
    "base_tags": ["#apprendrelefrançais", "#français", "#francophone"],
}

LOOK = {
    "title_font": "Advercase-Regular",
    "small_font": "IGSansCondensedGlobal-Regular",
    "title": ("Jour {day} de publications jusqu'à ce\nque je parle couramment français.", 17, 0.13),
    "title_en": ("Day {day} of posting till I speak French fluently", 11, 0.20),
    "format": ("exercices de spontanéité", 21, 0.20),
    "title_time": (0.0, 3.5),
    "format_time": (3.5, 3.0),
    "caption_style": "Default",       # Edits' style: whole line at once, heavy white
    "caption_font": "BrittiSans-Bold",   # French captions and the English under them
    "english_font": "BrittiSans-Bold",
    "caption_size": 42,         # French captions (Edits' default is 60: too loud)
    "english_size": 10,
    "english_colour": "#F6D98B",  # pale yellow: tells the two languages apart at a glance
    # captions sit just above the laptop (canvas fractions): the French block's bottom edge this far
    # above the laptop's top edge (long lines wrap upwards), the English line's centre this far
    "fr_bottom_above_laptop": 0.043,
    "en_above_laptop": 0.024,
    "caption_row": 0.027,       # height of one row of French
    "caption_row_chars": 42,    # about this many characters fit on one row
    "laptop_top_default": 0.565,
    "tail": 2.0,         # seconds kept after the last word
    "past_timer": 25.0,  # how far past the timer to look for the end of the answer
    "done_gap": 4.0,     # after the timer, a silence this long means the answer is over
}


def styled_text(e, text, at, dur, font, size, y, outline=False, colour="#FFFFFF"):
    el = e.call("addText", text=text, atSeconds=at, duration=dur)["id"]
    e.call("setTextFont", id=el, family=font)
    e.call("setTextStyle", id=el, size=size, color=colour)
    e.call("setTextPosition", id=el, x=0.5, y=y)
    if outline:
        e.call("setEmphasis", id=el, style="outline", color="#000000")
    return el


def open_project(e, pid, name):
    if e.call("appState").get("screen") == "editor":
        if e.call("state").get("title") == name:
            return
        e.call("closeProject")
    e.call("openProject", id=pid, name=name)


def laptop_top(clip: Path, timer_start: float) -> float:
    try:
        px = t.caption_y(clip, timer_start, 0)  # top of the laptop screen, px on 1920
    except Exception:
        px = 0
    return px / 1920 if px else LOOK["laptop_top_default"]


def rows(text):
    n, width = 1, 0
    for w in text.split():
        if width and width + 1 + len(w) > LOOK["caption_row_chars"]:
            n, width = n + 1, len(w)
        else:
            width += (1 if width else 0) + len(w)
    return n


def speech_end(caps, timer_end):
    """Where the video ends: a few seconds after the last word of the answer. The answer can run past
    the timer; past it, a long silence means he's done (what follows is chatter, not the answer)."""
    last = None
    for c in caps:
        if last is not None and last > timer_end - 1 and c["startTime"] - last >= LOOK["done_gap"]:
            break
        last = c["endTime"]
    return None if last is None else last + LOOK["tail"]


def caption_positions(e, captions, top):
    """Pin each French caption by its bottom edge, so a 3-row line grows up, away from the English."""
    for c in captions:
        y = top - LOOK["fr_bottom_above_laptop"] - rows(c["text"]) * LOOK["caption_row"] / 2
        e.call("setTextFont", id=c["id"], family=LOOK["caption_font"])
        e.call("setTextStyle", id=c["id"], size=LOOK["caption_size"], color="#FFFFFF")
        e.call("setTextPosition", id=c["id"], x=0.5, y=round(y, 4))


def build(e, take, day, number):
    clip = t.UNUSED / take["clip"]
    MOVIES.mkdir(parents=True, exist_ok=True)
    linked = MOVIES / clip.name
    if not linked.exists():
        try:
            os.link(clip, linked)
        except OSError:  # another disk: copy instead
            import shutil
            shutil.copy2(clip, linked)

    prompt = t.exact_prompt([f["text"] for f in t.read_screen(clip)
                             if take["landed"] <= f["t"] <= take["end"] and f["text"]])
    folder = t.READY / f"jour-{day}" / f"{number}-{t.slug(prompt)}"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"Jour {day} · N°{number} · {prompt[:40]}"
    print(f"  building {name} …")

    if e.call("appState").get("screen") == "editor":
        e.call("closeProject")
    pid = e.call("newProject")["id"]
    e.call("setTitle", name=name)
    vid = e.call("importMedia", path=str(linked))["id"]
    full = e.call("clips")["clips"][0]["duration"]
    # Trim before adding any text (trimming deletes text in the cut part). Keep some time after the
    # timer, because the answer often carries on past it; the end is set from the captions below.
    later = [x["start"] for x in t.load_json(t.WORK / "takes.json", {}).get(take["clip"], [])
             if x["start"] > take["start"]]
    hard_end = min([full, take["end"] + LOOK["past_timer"]] + later)
    e.call("trim", id=vid, side="right", deltaSeconds=round(full - hard_end, 3))
    e.call("trim", id=vid, side="left", deltaSeconds=round(take["start"], 3))
    length = hard_end - take["start"]

    e.call("generateCaptions", source="video", language="fr", curseWords=True)
    caps = e.call("captions")["captions"]
    end = speech_end(caps, take["end"] - take["start"])
    if end is not None and length - end > 0.1:
        e.call("trim", id=vid, side="right", deltaSeconds=round(length - end, 3))
        length = end
        caps = [c for c in e.call("captions")["captions"] if c["startTime"] < length]
    e.call("setCaptionStyle", style=LOOK["caption_style"])
    top = laptop_top(clip, take["timer_start"])
    caption_positions(e, caps, top)

    ids = {}
    for key in ("title", "title_en", "format"):
        text, size, y = LOOK[key]
        at, dur = LOOK["format_time"] if key == "format" else LOOK["title_time"]
        font = LOOK["small_font"] if key == "title_en" else LOOK["title_font"]
        ids[key] = styled_text(e, text.format(day=day), at, dur, font, size, y)
    e.call("saveProject")

    edit = {
        "status": "edits",  # edits (project made) → english (lines added) → posted
        "editor": "edits", "project_id": pid, "project_name": name,
        "date": dt.date.today().isoformat(), "day": day, "of_day": number,
        "clip": take["clip"], "source_start": take["start"], "source_end": round(take["start"] + length, 2),
        "prompt": prompt, "laptop_top": round(top, 3), "title_ids": ids,
        # Claude fills "en" (what was meant, in natural English) and, only for words Edits misheard,
        # "fr" (the corrected French; his own mistakes stay). Then `npm run tiktok -- english <folder>`.
        "captions": [{"id": c["id"], "start": round(c["startTime"], 2), "end": round(c["endTime"], 2),
                      "heard": c["text"], "fr": c["text"], "en": ""} for c in caps],
        "english_ids": [],
        # Claude: 2 hashtags about this prompt's topic, e.g. ["#films", "#séries"]
        "hashtags": [],
    }
    t.save_json(folder / "edit.json", edit)
    print(f"  → {folder}  ({len(caps)} caption lines, {length:.0f} s)")
    return folder


def cmd_edits(args):
    """N projects from the backlog, per-day (default 2) a day starting at Jour --day D (required: the
    user confirms the number first; it follows posting, not the calendar). Each is named for its Jour."""
    count = int(args[0]) if args and args[0].isdigit() else 1
    day = t.require_day(args)
    per_day = int(args[args.index("--per-day") + 1]) if "--per-day" in args else 2
    picks = [x for x in t.available_takes() if not x["reason"]][:count]
    if not picks:
        sys.exit("No unused takes left. Record more, or check `npm run tiktok -- backlog`.")
    e = Edits()
    for take in picks:
        while True:
            number = len(list((t.READY / f"jour-{day}").glob("*/edit.json"))) + 1
            if number <= per_day:
                break
            day += 1
        build(e, take, day, number)


def write_caption(folder, edit):
    tags = POST["base_tags"] + [h for h in edit.get("hashtags", []) if h not in POST["base_tags"]]
    text = (f"{POST['line'].format(day=edit['day'])} {edit['prompt']}\n\n"
            f"{POST['format']}\n\n{' '.join(tags)}\n")
    (folder / "caption.txt").write_text(text)
    return text


def cmd_caption(args):
    folder = Path(args[0]).resolve()
    edit = t.load_json(folder / "edit.json", None)
    print(write_caption(folder, edit))


def cmd_english(args):
    folder = Path(args[0]).resolve()
    edit = t.load_json(folder / "edit.json", None)
    if not edit or edit.get("editor") != "edits":
        sys.exit("Not an Edits project folder (make one with `npm run tiktok -- edits`).")
    missing = [c["heard"] for c in edit["captions"] if not c["en"].strip()]
    if missing:
        sys.exit(f"{len(missing)} lines have no English yet, e.g. «{missing[0]}».")
    e = Edits()
    open_project(e, edit["project_id"], edit["project_name"])
    existing = {el["id"] for el in e.call("elements", fields=["id"], limit=1000)["elements"]}
    # rerunnable: drop the English lines added last time
    for old in edit["english_ids"]:
        if old in existing:
            e.call("selectById", id=old, addToSelection=False)
            e.call("delete")
    new_ids = []
    top = edit["laptop_top"]
    for c in edit["captions"]:
        if c["fr"] != c["heard"]:
            e.call("editCaption", id=c["id"], text=c["fr"])
        new_ids.append(styled_text(e, c["en"], c["start"], round(c["end"] - c["start"], 3),
                                   LOOK["english_font"], LOOK["english_size"],
                                   top - LOOK["en_above_laptop"], outline=True, colour=LOOK["english_colour"]))
    e.call("saveProject")
    edit.update(english_ids=new_ids, status="english")
    t.save_json(folder / "edit.json", edit)
    print(f"  {len(new_ids)} English lines added to «{edit['project_name']}» in Edits.")
    write_caption(folder, edit)
    print(f"  caption.txt written")


if __name__ == "__main__":
    {"edits": cmd_edits, "english": cmd_english, "caption": cmd_caption}[sys.argv[1]](sys.argv[2:])
