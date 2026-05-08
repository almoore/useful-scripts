---
name: substack-live-brief
description: >
  Generate a structured content brief from a Substack Live (or similar live
  session / webinar / podcast / panel) transcript. Trigger this skill whenever
  the user mentions a Substack Live, a live session transcript, a recorded
  webinar, a panel discussion, or asks for a content brief / repurposing
  ideas / standalone quotes / "key themes" pulled from a recording — even if
  they don't say the word "Substack". Also trigger on phrasings like "I just
  finished a live and need to turn it into content", "pull quotes from this
  transcript", "summarize my session", or "what should I post from this".
---

# Substack Live → Content Brief

Turn a raw Substack Live transcript into a structured 6-section content brief
that the user can use to plan posts, threads, newsletters, and clips.

## Step 1 — Locate the transcript

The user will usually tell you a folder (Downloads, Desktop, or somewhere
specific) and possibly a session topic. If they don't:

- Ask which folder to search (default to `~/Downloads`).
- Ask for the session topic if not given. It's used to name the output file
  and to disambiguate when multiple transcript files exist.

Search that folder for recent files whose names contain any of: `transcript`,
`substack`, `live`, or words from the session topic. Accept these formats:
`.txt`, `.md`, `.pdf`, `.csv`, `.docx`.

Use `find` sorted by modification time, e.g.:

```bash
find ~/Downloads -maxdepth 3 -type f \
  \( -iname "*transcript*" -o -iname "*substack*" -o -iname "*live*" \) \
  \( -iname "*.txt" -o -iname "*.md" -o -iname "*.pdf" \
     -o -iname "*.csv" -o -iname "*.docx" \) \
  -mtime -30 -print0 \
  | xargs -0 ls -lt 2>/dev/null | head -20
```

**Disambiguation rules:**

- One match → use it, but tell the user which file you picked before
  reading it (so they can correct you cheaply).
- Multiple matches → show the top 3-5 by modification time with sizes, and
  ask the user to confirm. Default to the most recent unless the topic
  clearly points elsewhere.
- Zero matches → widen the search (drop the keyword filter, broaden the
  date range, try sibling folders like `~/Desktop` or `~/Documents`)
  before asking the user to point you at the file directly.

## Step 2 — Read the transcript

- `.txt`, `.md`, `.csv` → use the Read tool directly.
- `.pdf` → use the Read tool (it handles PDFs). For long transcripts, use
  the `pages` parameter to read in chunks.
- `.docx` → convert first. Try in this order:
  1. `pandoc input.docx -o /tmp/transcript.md` (preserves structure)
  2. `textutil -convert txt -output /tmp/transcript.txt input.docx` (macOS fallback)
  3. Python `python-docx` if neither is available.

  Then Read the converted file.

If the file is huge (more than ~2000 lines), read it in passes: scan the
whole thing once for shape and timestamps, then re-read targeted sections
when drafting specific brief sections. Don't try to hold every line in working
memory — work from notes.

## Step 3 — Analyze the content

Before writing the brief, identify:

- **Speakers**: who's hosting, who's joining, any notable guests. Substack
  Live transcripts often label speakers (`Speaker 1`, names, or `Host`).
- **Structure**: rough segments — intro, main discussion, audience Q&A,
  wrap-up. Note timestamps if present.
- **Audience interaction**: questions from viewers, reactions, threads
  that got long replies (signals high engagement).
- **Quotable moments**: lines that work standalone, surprising claims,
  punchy framings, vivid analogies.

## Step 4 — Write the brief

Use this exact 6-section structure. The headings and order matter — the
user has a downstream workflow built around them.

```markdown
# [Session Topic] — Content Brief

## 1. Session Overview
- **Main topic:** ...
- **Speakers:** ... (host, guests, notable participants)
- **Length:** ~XX minutes
- **Structure:** brief description of the arc — e.g., "10-min intro on X,
  25-min discussion of Y, 15-min audience Q&A, 5-min wrap"

## 2. Key Themes
[3-5 themes. For each:]
### Theme 1: [name]
- 2-3 bullets summarizing the idea
- > "Direct quote from a speaker." — Speaker name (timestamp if available)

## 3. Audience Questions & Answers
[List the strongest 3-6 questions. For each:]
- **Q:** "..." — asker name if known
- **A:** Summary of the answer/insight given.
- *Engagement signal:* note if this got a long response, a follow-up, or
  visible reaction (only when there's evidence in the transcript)

## 4. Standalone Quotes
[3-5 quotes that work pulled out of context — for social clips, pull
quotes, threads. Note timestamp if available.]
- > "Quote." — Speaker (HH:MM)

## 5. Content Repurposing Opportunities
- **Standalone post:** which idea is meaty enough for a full essay?
- **Thread / LinkedIn carousel:** what sequence works in 5-10 beats?
- **Newsletter:** which angle fits the user's regular cadence?
[Be specific — name the idea and why it fits the format, not just generic
"could be a post".]

## 6. Follow-Up Content Ideas
[3-5 topics the session touched on but didn't fully cover. These are
future content prompts — phrase them as questions or post titles, not
abstract topics.]
```

### What "good" looks like for each section

- **Themes are concepts, not topics.** "Why newsletter writers struggle
  with consistency" is a theme. "Newsletters" is a topic. Themes have a
  point of view; topics are just nouns.
- **Quotes must be verbatim.** If the transcript has speech-to-text errors
  ("its" for "it's", missing punctuation, run-ons), gently clean them
  for readability, but never paraphrase a quote and present it as one.
  When in doubt, mark a paraphrase clearly: `[paraphrased]`.
- **Repurposing ideas should be specific.** "Could be a thread on
  audience-building" is too vague. "Thread: the 4 mistakes newsletter
  writers make in their first month, with fixes from the live" is usable.
- **Follow-up ideas are gaps, not recaps.** Look for moments where a
  speaker said "we could go deep on that another time" or where a thread
  got cut off by time. Those are the highest-value follow-ups.

### Why this structure

The user runs a content workflow where each section feeds a different
output: themes → essay outlines, Q&A → reader engagement posts, quotes →
social clips, repurposing → editorial calendar, follow-ups → future
sessions. Keeping the structure consistent across briefs makes that
workflow possible. Don't reorder sections or merge them.

## Step 5 — Save the brief

Save to the same folder as the source transcript, named:

```
[session-topic-slug]-brief.md
```

Slug rules: lowercase, hyphens for spaces, no punctuation. If the session
topic is "Claude Skills for Newsletter Writers", the file is
`claude-skills-for-newsletter-writers-brief.md`.

If a brief with that name already exists, don't overwrite. Append a short
date suffix: `claude-skills-for-newsletter-writers-brief-2026-05-07.md`,
and tell the user.

After saving, tell the user:
- The full path to the brief
- A 2-3 line preview of what's in it (which themes, how many quotes, etc.)
  so they can decide whether to open it now or come back to it later.

## Edge cases

- **Transcript has no speaker labels.** Note this upfront and infer
  speakers from context only when you can do so confidently. Otherwise
  attribute quotes to "Speaker" and flag the limitation in the overview.
- **Transcript has no timestamps.** Skip timestamp annotations rather
  than inventing them. Don't fake `(00:00)` markers.
- **Session was very short (<15 min).** Still produce all 6 sections,
  but it's fine for the brief itself to be short. Don't pad.
- **Session was very long (>2 hours).** Themes and Q&A may need to be
  capped — pick the 5 strongest of each rather than exhaustively listing.
  Note in the overview that the brief is selective.
- **Multiple speakers, hard to tell apart.** Use "Host" / "Guest" /
  "Audience" rather than guessing names. Better honest than wrong.
