# site-video

A Claude Code plugin that makes films of real websites. A page is captured frame by frame in a real browser as it
plays; the camera, the cursor and the closing card are composed in code; every frame is measured before anyone sees
it. You get a checked MP4 ready for LinkedIn, X or email, and a capture that every later round of changes reuses, so a
change costs seconds, not a new recording.

The method behind it: the story and the choreography are agreed first, then a quick rough cut, and only then the
pixel-level refinement. The gates (hold lengths, text size on a phone, camera speed, framing, cut text, delivery
format) were each calibrated on renders with known faults.

## What you need

- A Mac (Apple silicon or Intel) with Claude Code: the desktop app's Code tab or the terminal.
- Python 3.9 to 3.13 (3.12 recommended; `brew install python@3.12`).
- ffmpeg with libx264 (`brew install ffmpeg`).
- About 5 GB of free disk for the browser, the captures and the renders.
- A network connection for the one-time setup, which downloads Playwright's Chromium (roughly 150 to 550 MB).

## Install

In Claude Code:

```
/plugin marketplace add revtech-hq/site-video
/plugin install site-video@site-video
```

Restart Claude Code after the install so the skill loads.

To install from a copy on disk instead (a clone of this repository, or its ZIP unzipped), keep the folder and add it
by its full path: `/plugin marketplace add /path/to/the/folder`, then the same install line.

## First run

Ask Claude: **"set up site-video"**. It runs two commands of the plugin's launcher, `sv`:

- `sv setup` makes a private Python environment in `~/.site-video` with exact versions of Pillow and Playwright, and
  downloads Playwright's Chromium. It asks before it runs, every time.
- `sv doctor` checks the machine: the Command Line Tools, Python, the environment, the browser, ffmpeg and ffprobe,
  and free disk. Every line should say PASS; each FAIL prints its fix.

Then ask: **"make the demo film"**. Claude starts a film folder from the overview template, which films a small demo
page that ships inside the plugin: no network, no third party's page. It takes a few minutes, most of it the capture.

## Your first real film

Ask: **"make a film of https://your-page.example"**. Claude asks three questions first (what the viewer must believe
at the end, who sees it and where, what the film must show), agrees the choreography with you, shows a rough cut, and
only then refines. Each version passes the gates, and the plugin's `film-reviewer` agent reviews the exact file before
it is called final.

A film folder holds its own numbers (`film.json`), the brand's values (`brand.json`), the beats the eye must get
(`beats.json`) and the film's script (`film.py`). The capture stays out of git. Any version replays from its folder.

## What the plugin pre-approves

The skill pre-approves three of the launcher's commands, so Claude can run them without asking each time:

- `sv doctor` (checks the machine),
- `sv check ...` (the gates, which read files and write a sidecar beside the film),
- `sv film ...` (the film's own commands: measure the page, capture, render).

`sv setup` is never pre-approved: it downloads software, so Claude asks you each time.

## Limits

- Pages behind a sign-in cannot be filmed: the capture's browser starts with no cookies. Consent banners are declined
  by their button text.
- The films are silent.
- Tested on macOS. Linux should work but is untested; Windows is not supported.

## Running `sv` yourself

The launcher lives in the installed plugin at `skills/site-video/scripts/sv`. To use it in a terminal, link it onto
your path, for example `ln -s "<plugin folder>/skills/site-video/scripts/sv" /usr/local/bin/sv`. Run `sv` with no
arguments for its commands.

## Uninstall

```
/plugin uninstall site-video@site-video
```

Then delete `~/.site-video` (the environment and the browser) if you want the disk back.

## What is in this repository

| Path | Holds |
|---|---|
| `plugins/site-video/skills/site-video/` | the skill: `SKILL.md`, the references, the launcher and its scripts, the overview template, the tests |
| `plugins/site-video/agents/film-reviewer.md` | the independent reviewer, run on every cut before it is called final |
| `evals/site-video-trigger/` | the cases that check when the skill loads and when it stays quiet |
| `tools/` | the repository's leak gate, run before every commit |

## Credit and licence

Made by RevTech. See `LICENSE`.
