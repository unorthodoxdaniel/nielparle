# The video project, in plain words

## What @nielparle is

A daily TikTok series: **"Jour N de publications jusqu'à ce que je parle couramment français."**
Daniel posts every day until he speaks French fluently. Most videos right now are
**exercices de spontanéité**: the parlons roulette (on the laptop) picks a question, a one-minute
timer starts, and he answers out loud without preparing.

## The problem this solves

Recording is quick. Editing wasn't: every clip had to be opened in the TikTok app, trimmed, titled,
captioned and checked, one at a time. The backlog of unedited clips was the stressful part, and
because it was done by hand the videos didn't look consistent (the "Jour N" title looked different
from one video to the next).

## What it does instead

You record and drop the clips in a folder. The tool:

1. **Finds the takes** by reading the laptop screen: where each roulette spin lands, where the timer
   runs, and where you stop. One clip can hold several takes; spins you skipped are left out.
2. **Skips prompts already posted**, using a log of every prompt that's gone out.
3. **Writes the captions** (offline), and Claude checks them: Whisper's mistakes are fixed, your own
   French stays as you said it, so native speakers can do the correcting in the comments.
4. **Burns in the design**: the day card, the parlons card, like + follow, a comment question, captions.
5. **Leaves a folder per video** with the video and the post caption, ready to upload anywhere.

You pick a folder, upload, paste the caption. That's it.

## What it should feel like

- **Less effort than editing in the app**, never more. If a step becomes a chore, it should be cut.
- **Consistent.** Every video looks like it belongs to the same series and to nielparle.com.
- **More conversation than an in-app edit.** Mistakes are left for viewers to correct, and every
  video ends on a question, so there's always a reason to comment.
- **Easy to undo.** Going back to the app is one flag away (`--clean`: same cut, no text).

## What we chose not to do

- No editing in Instagram's Edits app for now (its reach boost is small and was temporary).
- No music, filters or colour grading. The footage stays as recorded, in HDR.
- The prompt isn't written on screen: the laptop already shows it.
- Parlons is never changed from here; this project only reads its prompts.

## Where things are

- How it looks, and the rules behind it: [`VIDEO-DESIGN.md`](VIDEO-DESIGN.md) (edit this to change the design)
- How to use it day to day: [`VIDEO-WORKFLOW.md`](VIDEO-WORKFLOW.md)
- Prompts already posted: [`ledger.json`](ledger.json)
- Footage and finished videos: `video-content/` in the main checkout (not in git)
