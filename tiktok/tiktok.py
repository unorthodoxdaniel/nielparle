"""TikTok prep for @nielparle: turns raw roulette takes into ready-to-post videos.

    npm run tiktok -- scan                 read every clip in "unused footage" (cached)
    npm run tiktok -- seed                 log the prompts already posted ("reference footage")
    npm run tiktok -- backlog              list takes that are ready to use, oldest first
    npm run tiktok -- next [N] [--date D]  make N new video folders for day D (default: today)
    npm run tiktok -- review [folder]      captions, unsure words and corrections, as text
    npm run tiktok -- render <folder>      burn titles, captions and CTAs into video.mp4
    npm run tiktok -- posted <folder>      log the prompt as covered, move finished clips to "used"
    npm run tiktok -- skip <folder>        don't use this take; it won't be offered again
    (next: --number N starts the day's numbering at N, e.g. after posting one from the app)

See tiktok/VIDEO-WORKFLOW.md for the whole workflow and tiktok/VIDEO-DESIGN.md for the design.
"""
import datetime as dt
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
LEDGER = HERE / "ledger.json"
FFMPEG = REPO / "node_modules" / "ffmpeg-static" / "ffmpeg"
DAY_ONE = dt.date(2026, 8, 20)  # Jour 1


def main_checkout() -> Path:
    """Footage lives in the main checkout, also when this runs from a worktree."""
    out = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                         capture_output=True, text=True)
    return Path(out.stdout.strip()).parent if out.returncode == 0 else REPO


CONTENT = Path(os.environ.get("VIDEO_CONTENT", main_checkout() / "video-content"))
UNUSED = CONTENT / "unused footage"
USED = CONTENT / "used footage"
REFERENCE = CONTENT / "reference footage"
READY = CONTENT / "ready"
WORK = CONTENT / ".work"
VIDEO_EXT = {".mov", ".mp4", ".m4v"}


# ---------- helpers ----------

def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def day_number(date: dt.date) -> int:
    return (date - DAY_ONE).days + 1


def load_json(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def clips(folder: Path):
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in VIDEO_EXT) if folder.exists() else []


def ledger():
    return load_json(LEDGER, {"covered": [], "skipped": []})


# ---------- prompt bank (parlons, read-only) ----------

def supabase_settings():
    url, key = os.environ.get("PARLONS_SUPABASE_URL"), os.environ.get("PARLONS_SUPABASE_KEY")
    if not (url and key):  # fall back to parlons' own public settings, read-only
        env = Path.home() / "parlons" / ".env"
        if env.exists():
            vals = dict(l.split("=", 1) for l in env.read_text().splitlines() if "=" in l and not l.startswith("#"))
            url = url or vals.get("PUBLIC_SUPABASE_URL")
            key = key or vals.get("PUBLIC_SUPABASE_PUBLISHABLE_KEY")
    if not (url and key):
        sys.exit("Set PARLONS_SUPABASE_URL and PARLONS_SUPABASE_KEY (the public publishable key).")
    return url.strip(), key.strip()


def prompt_bank(refresh=False):
    cache = WORK / "prompts.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text())
    url, key = supabase_settings()
    rows, offset = [], 0
    while True:
        req = urllib.request.Request(
            f"{url}/rest/v1/prompts?select=id,text,languages(code),themes(key,name)&order=id&offset={offset}&limit=500",
            headers={"apikey": key})
        page = json.load(urllib.request.urlopen(req, timeout=20))
        rows += [{"id": r["id"], "text": r["text"], "lang": (r.get("languages") or {}).get("code"),
                  "theme": (r.get("themes") or {}).get("name")} for r in page]
        if len(page) < 500:
            break
        offset += 500
    save_json(cache, rows)
    return rows


_SIM = {}


def overlap(a: str, b: str) -> float:
    """Share of the shorter text found in the longer one (in order). Ignores junk around a prompt."""
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    key = (a, b) if a < b else (b, a)
    if key not in _SIM:
        short, long_ = sorted((a, b), key=len)
        blocks = difflib.SequenceMatcher(None, short, long_, autojunk=False).get_matching_blocks()
        _SIM[key] = sum(m.size for m in blocks) / len(short)
    return _SIM[key]


def similar(a: str, b: str, threshold=0.8) -> bool:
    """Same prompt? OCR is a little noisy and may carry menu text, so compare loosely."""
    return min(len(norm(a)), len(norm(b))) >= 15 and overlap(a, b) >= threshold


def partial_ratio(short: str, long_: str) -> float:
    """Best match of `short` against any same-length stretch of `long_` (junk around it is ignored)."""
    if len(short) > len(long_):
        short, long_ = long_, short
    sm = difflib.SequenceMatcher(None, short, long_, autojunk=False)
    best = 0.0
    for m in sm.get_matching_blocks():
        start = max(0, m.b - m.a)
        window = long_[start:start + len(short)]
        best = max(best, difflib.SequenceMatcher(None, short, window, autojunk=False).ratio())
    return best


def bank_match(text: str, bank):
    """The parlons prompt this OCR text shows, or None. The whole prompt has to appear as one close
    run in the text (menu junk around it doesn't matter); a partial read must still be most of it."""
    n = norm(text)
    if len(n) < 20:
        return None
    shortlist = sorted(bank, key=lambda p: -difflib.SequenceMatcher(None, n, p.setdefault("_n", norm(p["text"]))).quick_ratio())[:30]
    scored = [(partial_ratio(p["_n"], n) * min(1.0, len(n) / len(p["_n"]) / 0.8), p) for p in shortlist]
    score, best = max(scored, key=lambda x: x[0])
    return best["text"] if score >= 0.85 else None


def exact_prompt(texts):
    """Clean spelling of a prompt: the parlons prompt most readings agree on, else the OCR text."""
    from collections import Counter
    texts = [texts] if isinstance(texts, str) else texts
    try:
        bank = prompt_bank()
    except Exception:
        return max(texts, key=len, default="")
    votes = Counter(m for m in (bank_match(t, bank) for t in texts) if m)
    return votes.most_common(1)[0][0] if votes else max(texts, key=len, default="")


# ---------- reading the laptop screen ----------

# app chrome around the prompt: buttons and menus (prefix match), theme names (whole line only)
UI = re.compile(r"^(parlons|parions|macbook pro|fr|en|\d+ ?en|son activ|commencer|relancer|ne pl|espace|terminer|"
                r"confidentialit|proposer|nielparle|hielparle|se preparer|a propos|tu as pris le temps|"
                r"continue comme ca|un autre sujet|\W*$)|^(technologie|voyage|travail|culture|societe|souvenirs|"
                r"relations|vie quotidienne|apprentissage|imagination|aleatoire)$")
TIMER = re.compile(r"^\d{2}\s?[:.]\s?\d{2}$")


def prompt_line(line: str) -> bool:
    """Lines that belong to the prompt, not the app around it (menus, buttons, misreads)."""
    l = line.strip()
    words = l.split()
    if len(words) < 2 or TIMER.match(l) or UI.match(norm(l)):
        return False
    if re.search(r"[^\x00-\u024F’«»…–—]", l):  # non-Latin letters: a misread
        return False
    letters = [c for c in l if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.5:  # MENU LABELS
        return False
    n = norm(l)
    return not any(difflib.SequenceMatcher(None, n, b).ratio() > 0.6
                   for b in ("commencer a parler", "terminer maintenant", "ne plus afficher ce sujet"))


def screen_binary() -> Path:
    exe = WORK / "bin" / "screen"
    src = HERE / "screen.swift"
    if not exe.exists() or exe.stat().st_mtime < src.stat().st_mtime:
        exe.parent.mkdir(parents=True, exist_ok=True)
        run(["swiftc", "-O", "-suppress-warnings", src, "-o", exe])
    return exe


def read_screen(clip: Path):
    """OCR timeline for a clip, cached by name and size."""
    cache = WORK / "screen" / f"{clip.name}.{clip.stat().st_size}.jsonl"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        print(f"  reading screen: {clip.name}")
        out = subprocess.run([str(screen_binary()), str(clip), "0.5"], capture_output=True, text=True, check=True)
        cache.write_text(out.stdout)
    frames = [json.loads(l) for l in cache.read_text().splitlines() if l.strip()]
    for f in frames:
        lines = f["lines"]
        f["timer"] = any(TIMER.match(l.strip()) for l in lines)
        f["landed"] = any(norm(l).startswith(("commencer", "umencer", "ommencer")) for l in lines)
        f["text"] = " ".join(l for l in lines if prompt_line(l))
    return frames


def caption_y(clip: Path, t0: float, design_gap: int) -> int:
    """Where captions go for this clip: just above the laptop screen. The framing changes from
    clip to clip, so find the app's header line ("Parlons", top of the screen) and sit above it."""
    out = subprocess.run([str(screen_binary()), str(clip), "1", str(t0), str(t0 + 4)],
                         capture_output=True, text=True, check=True)
    tops = []
    for line in out.stdout.splitlines():
        f = json.loads(line)
        header = [top for text, top in zip(f["lines"], f.get("tops", [])) if norm(text)[:3] in ("par", "pun", "pan")]
        if header:
            tops.append(min(header))
        elif f.get("tops"):
            tops.append(min(f["tops"]))
    if not tops:
        return 0  # use the design default
    top = sorted(tops)[len(tops) // 2] * 1920
    return int(max(800, min(1500, top - design_gap)))


def find_takes(clip: Path):
    """Each roulette that led to a timer is one take: from the spin that landed on the
    prompt to the end of the timer. Spins that were skipped (re-spun) are left out."""
    frames = read_screen(clip)
    takes, i = [], 0
    while i < len(frames):
        if not frames[i]["timer"]:
            i += 1
            continue
        j = i
        while j + 1 < len(frames) and (frames[j + 1]["timer"] or
                                        (j + 2 < len(frames) and frames[j + 2]["timer"])):  # allow 1-frame misses
            j += 1
        # the prompt: the clearest reading while it sat on screen (landed or timer running)
        texts = [f["text"] for f in frames[max(0, i - 6):j + 1] if len(norm(f["text"])) > 12]
        prompt = max(texts, key=lambda t: sum(similar(t, o) for o in texts) + len(t) / 1000, default="")
        same = lambda f: not norm(f["text"]) or similar(f["text"], prompt)
        # walk back: landed on this prompt (reading it out), then the spin before it
        k = i - 1
        while k >= 0 and not frames[k]["timer"] and frames[k]["landed"] and same(frames[k]):
            k -= 1
        landed_at = frames[k + 1]["t"]
        # the spin: text changes every frame. Stop at an earlier prompt that stayed put (a skipped landing).
        while k >= 0 and not frames[k]["timer"]:
            w = frames[max(0, k - 2):k + 1]
            if len(w) == 3 and all(norm(f["text"]) and similar(f["text"], w[0]["text"]) for f in w) \
                    and not similar(w[0]["text"], prompt):
                break
            k -= 1
        start = max(0.0, frames[k + 1]["t"] - 0.25) if k >= 0 else 0.0
        takes.append({"clip": clip.name, "start": start, "landed": landed_at, "timer_start": frames[i]["t"],
                      "end": frames[j]["t"] + 0.5, "prompt": prompt})
        i = j + 1
    return takes


# ---------- commands ----------

def cmd_scan(args):
    posted_sizes = {c.stat().st_size for c in clips(REFERENCE)}
    result = {}
    for c in clips(UNUSED):
        if c.stat().st_size in posted_sizes:
            print(f"  {c.name}: same file as in reference footage (already posted), skipping")
            continue
        result[c.name] = find_takes(c)
        for t in result[c.name]:
            secs = t["end"] - t["start"]
            print(f"  {c.name} {t['start']:6.1f}–{t['end']:6.1f}s ({secs:4.0f}s)  {t['prompt'][:70]}")
        if not result[c.name]:
            print(f"  {c.name}: no timer found (not a roulette take?)")
    save_json(WORK / "takes.json", result)


def cmd_seed(args):
    """Log the prompts of posted videos (reference footage) so they're never repeated.
    Posted videos have TikTok captions over the frame, so each prompt is read from several
    frames and only an exact parlons prompt that most frames agree on is logged."""
    from collections import Counter
    led = ledger()
    for c in clips(REFERENCE):
        frames = read_screen(c)
        bank = prompt_bank()
        votes = Counter(m for m in (bank_match(f["text"], bank) for f in frames if f["timer"]) if m)
        if not votes:
            print(f"  {c.name}: couldn't read the prompt; add it to tiktok/ledger.json by hand")
            continue
        prompt, n = votes.most_common(1)[0]
        if n < 3:
            print(f"  {c.name}: unsure ({prompt[:60]}…, {n} frame); add it to tiktok/ledger.json by hand")
            continue
        if any(similar(prompt, x["prompt"]) for x in led["covered"]):
            continue
        led["covered"].append({"prompt": prompt, "source": f"reference/{c.name}", "posted": None})
        print(f"  covered ({n} frames agree): {prompt[:90]}")
    save_json(LEDGER, led)


def available_takes():
    takes = load_json(WORK / "takes.json", None)
    if takes is None:
        sys.exit("Run `npm run tiktok -- scan` first.")
    led = ledger()
    done = [c["prompt"] for c in led["covered"]]
    skipped = {(s["clip"], round(s["start"])) for s in led["skipped"]}
    in_progress = set()
    for edit in READY.glob("[0-9]*/*/edit.json"):
        e = json.loads(edit.read_text())
        in_progress.add((e["clip"], round(e["source_start"])))
        done.append(e["prompt"])
    out, seen = [], []
    for name in sorted(takes):  # IMG_ numbers sort by recording order
        if not (UNUSED / name).exists():
            continue
        for t in takes[name]:
            key = (name, round(t["start"]))
            if key in in_progress or key in skipped:
                continue
            reason = None
            if t["end"] - t["timer_start"] < 20:
                reason = "timer stopped early (<20 s)"
            elif any(similar(t["prompt"], d) for d in done):
                reason = "prompt already posted"
            elif any(similar(t["prompt"], d) for d in seen):
                reason = "same prompt earlier in the backlog"
            out.append({**t, "reason": reason})
            if not reason:
                seen.append(t["prompt"])
    return out


def cmd_backlog(args):
    takes = available_takes()
    good = [t for t in takes if not t["reason"]]
    for t in takes:
        flag = f"  ✗ {t['reason']}" if t["reason"] else ""
        print(f"{t['clip']:>14} {t['start']:6.1f}s  {t['prompt'][:72]}{flag}")
    print(f"\n{len(good)} takes ready to use (~{len(good) // 2} days at 2 a day).")


def slug(s, n=40):
    return re.sub(r"-+", "-", norm(s).replace(" ", "-"))[:n].strip("-") or "video"


def transcribe(wav: Path, prompt: str):
    from faster_whisper import WhisperModel
    model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(str(wav), language="fr", word_timestamps=True, vad_filter=True,
                               initial_prompt=prompt, condition_on_previous_text=False)
    words = []
    for seg in segs:
        for w in seg.words:
            text = w.word.strip()
            if not text:
                continue
            # Whisper splits "c'est" into "c" + "'est" and "moi-même" into "moi" + "-même"
            if words and (text[0] in "'’-" or words[-1]["w"][-1] in "'’"):
                words[-1].update(w=words[-1]["w"] + text, e=round(w.end, 2),
                                 p=round(min(words[-1]["p"], w.probability), 2))
                continue
            words.append({"w": text, "s": round(w.start, 2), "e": round(w.end, 2), "p": round(w.probability, 2)})
    return words


def group_cues(words, max_chars=34, max_gap=0.7):
    """Short caption lines: break at sentence ends, pauses, or ~34 characters."""
    cues, cur = [], []
    for w in words:
        if cur:
            text = " ".join(x["w"] for x in cur + [w])
            gap = w["s"] - cur[-1]["e"]
            if len(text) > max_chars or gap > max_gap or re.search(r"[.?!…]$", cur[-1]["w"]):
                cues.append(cur)
                cur = []
        cur.append(w)
    if cur:
        cues.append(cur)
    # a lone word ("Alors,", a restart) flashes by: join it to the next line if that comes soon
    merged = []
    for c in cues:
        if merged and len(merged[-1]) == 1 and c[0]["s"] - merged[-1][-1]["e"] < 1.5 \
                and len(" ".join(x["w"] for x in merged[-1] + c)) <= max_chars + 8:
            merged[-1] = merged[-1] + c
        else:
            merged.append(c)
    cues = merged
    return [{"s": c[0]["s"], "e": c[-1]["e"], "text": " ".join(x["w"] for x in c),
             "unsure": [x["w"] for x in c if x["p"] < 0.6], "fix": None,
             "words": [[x["w"], x["s"], x["e"]] for x in c]} for c in cues]


def cmd_next(args):
    count = int(args[0]) if args and args[0].isdigit() else 1
    date = dt.date.fromisoformat(args[args.index("--date") + 1]) if "--date" in args else dt.date.today()
    day_dir = READY / date.isoformat()
    # numbering within the day: after the folders already made for it, or from --number (e.g. when
    # the day's first video was posted from the app)
    already = len(list(day_dir.glob("*/edit.json")))
    if "--number" in args:
        already = int(args[args.index("--number") + 1]) - 1
    picks = [t for t in available_takes() if not t["reason"]][:count]
    if not picks:
        sys.exit("No unused takes left. Record more, or check `npm run tiktok -- backlog`.")
    for t in picks:
        already += 1
        # read the prompt only once the roulette has landed (during the spin other prompts flash by)
        prompt = exact_prompt([f["text"] for f in read_screen(UNUSED / t["clip"])
                               if t["landed"] <= f["t"] <= t["end"] and f["text"]])
        folder = day_dir / f"{already}-{slug(prompt)}"
        folder.mkdir(parents=True, exist_ok=True)
        wav = WORK / "audio" / f"{folder.name}.wav"
        wav.parent.mkdir(parents=True, exist_ok=True)
        run([FFMPEG, "-loglevel", "error", "-y", "-ss", t["start"], "-to", t["end"], "-i", UNUSED / t["clip"],
             "-ac", "1", "-ar", "16000", wav])
        print(f"  transcribing {folder.name} …")
        words = transcribe(wav, prompt)
        # end on the last word (plus a breath), never after the timer
        speech_end = max((w["e"] for w in words), default=t["end"] - t["start"])
        out_t = min(t["end"] - t["start"], speech_end + 0.8)
        words = [w for w in words if w["s"] < out_t]
        edit = {
            "status": "draft",  # draft → checked (captions corrected) → rendered → posted
            "date": date.isoformat(), "day": day_number(date), "of_day": already,
            "clip": t["clip"], "source_start": t["start"], "source_end": round(t["start"] + out_t, 2),
            "landed": round(t["landed"] - t["start"], 2), "timer_start": round(t["timer_start"] - t["start"], 2),
            "prompt": prompt,
            "caption_y": caption_y(UNUSED / t["clip"], t["timer_start"], design_value("layout.caption_above_screen")),
            "format": "exercices de spontanéité",
            "comment": "",  # comment question shown near the end
            "cues": group_cues(words, design_value("caption.max_chars")),
            "words": words,
        }
        save_json(folder / "edit.json", edit)
        print(f"  → {folder}")


# ---------- render ----------

def design_value(key):
    sys.path.insert(0, str(HERE))
    from render import design
    return design()[key]



def hlg_colour(hex_rgb: str, level=0.75):
    """sRGB colour → BT.2020 HLG code values, with sRGB white at HLG reference white (75%)."""
    import math
    rgb = [int(hex_rgb[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    m = [[0.6274, 0.3293, 0.0433], [0.0691, 0.9195, 0.0114], [0.0164, 0.0880, 0.8956]]  # 709 → 2020
    l2020 = [sum(m[r][k] * lin[k] for k in range(3)) for r in range(3)]
    a, b, c = 0.17883277, 0.28466892, 0.55991073
    ref = (math.exp((level - c) / a) + b) / 12  # scene light that gives `level` signal
    out = []
    for e in l2020:
        e = max(0.0, e * ref)
        v = math.sqrt(3 * e) if e <= 1 / 12 else a * math.log(12 * e - b) + c
        out.append(round(min(1.0, v) * 255))
    return "&H{:02X}{:02X}{:02X}&".format(out[2], out[1], out[0])  # ASS is BGR


def cmd_render(args):
    folder = Path(args[0]).resolve()
    edit = load_json(folder / "edit.json", None)
    if not edit:
        sys.exit(f"No edit.json in {folder}")
    sys.path.insert(0, str(HERE))
    from render import render
    render(edit, folder, clip=UNUSED / edit["clip"] if (UNUSED / edit["clip"]).exists() else USED / edit["clip"],
           ffmpeg=FFMPEG, colour=hlg_colour, work=WORK, clean="--clean" in args)
    edit["status"] = "rendered"
    save_json(folder / "edit.json", edit)


def cmd_review(args):
    """Readable summary of a video's captions: what you said, Whisper's unsure words, corrections."""
    for arg in args or [str(d) for d in sorted(READY.glob("*/*")) if (d / "edit.json").exists()]:
        folder = Path(arg).resolve()
        e = load_json(folder / "edit.json", None)
        if not e:
            continue
        print(f"\n── {e['date']} · Jour {e['day']} · N° {e['of_day']} · {e['status']}  ({folder.name})")
        print(f"   Prompt: {e['prompt']}")
        print(f"   Comment question: {e.get('comment') or '(default)'}")
        for i, c in enumerate(e["cues"], 1):
            unsure = f"   ?{', '.join(c['unsure'])}" if c.get("unsure") and e["status"] == "draft" else ""
            print(f"   {i:>2}  {c['text']}{unsure}")
            if c.get("fix"):
                f = c["fix"]
                print(f"       ✎ {f['said']} → {f['better']}" + (f"  ({f['note']})" if f.get("note") else ""))


def cmd_skip(args):
    """Don't use this take (bad take, don't like it): never offered again; its folder moves aside."""
    folder = Path(args[0]).resolve()
    edit = load_json(folder / "edit.json", None)
    led = ledger()
    led["skipped"].append({"clip": edit["clip"], "start": edit["source_start"], "prompt": edit["prompt"]})
    save_json(LEDGER, led)
    dest = READY / "_skipped" / f"{edit['date']}-{folder.name}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(folder), dest)
    print(f"  skipped; folder moved to {dest}")


def cmd_posted(args):
    folder = Path(args[0]).resolve()
    edit = load_json(folder / "edit.json", None)
    if edit["status"] == "posted":
        sys.exit("Already logged as posted.")
    led = ledger()
    led["covered"].append({"prompt": edit["prompt"], "source": edit["clip"],
                           "posted": edit["date"], "day": edit["day"], "folder": f"{edit['date']}/{folder.name}"})
    save_json(LEDGER, led)
    edit["status"] = "posted"
    save_json(folder / "edit.json", edit)
    # move the raw clip once none of its takes are left to use
    left = [t for t in available_takes() if t["clip"] == edit["clip"] and not t["reason"]]
    if not left and (UNUSED / edit["clip"]).exists():
        USED.mkdir(exist_ok=True)
        shutil.move(str(UNUSED / edit["clip"]), USED / edit["clip"])
        print(f"  moved {edit['clip']} to used footage")
    print(f"  logged as posted on day {edit['day']}: {edit['prompt'][:80]}")


COMMANDS = {"scan": cmd_scan, "seed": cmd_seed, "backlog": cmd_backlog, "next": cmd_next, "review": cmd_review,
            "render": cmd_render, "posted": cmd_posted, "skip": cmd_skip}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](sys.argv[2:])
