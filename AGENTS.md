# Job Autopilot

Discovers junior/intern software roles, scores them against Kevin's profile,
and queues the good ones for approval. Writes a summary at 21:00 IST daily.

## What this does and does not do

It **does**: discover, deduplicate, gate, score, queue, track, and summarise.

It **does not** auto-submit applications. Submitting forms on job boards means
entering personal data and clicking irreversible controls on Kevin's behalf,
and mass auto-submission gets accounts restricted and trips ATS dedup filters.
The queue is reviewed, then submission is browser-assisted with Kevin
confirming each one.

## Stack

Python 3.11, standard library plus `requests` and `PyYAML`. SQLite for storage.
No framework — the whole thing is six modules.

## Layout

```
profile.example.yaml      committed template
profile.yaml              single source of truth for every form field (gitignored)
autopilot/
  config.py               loads profile.yaml, defines paths
  models.py               Job, Verdict, ScoredJob
  scorer.py               hard gates + weighted score
  store.py                SQLite schema and queries
  pipeline.py             fetch -> gate -> score -> store
  digest.py               daily markdown summary
  cli.py                  command line entry point
  sources/
    base.py               HTTP helpers, Source protocol
    remoteok.py           RemoteOK tag-filtered feeds
    remotive.py           Remotive software-dev category
scripts/daily.ps1         scheduled task entry point
data/autopilot.db         SQLite (gitignored)
docs/DAILY/<date>.md      generated summaries
```

## Commands

```bash
python -m autopilot run                    # discover and score
python -m autopilot queue                  # what is awaiting approval
python -m autopilot ingest --file inbox/x.txt --channel whatsapp
python -m autopilot digest                 # write today's summary
python -m autopilot daily                  # run + digest (scheduler uses this)
python -m autopilot approve <fingerprint>  # mark as applied
python -m autopilot skip <fingerprint>     # dismiss
```

## Rules

- **profile.yaml is the only place personal data lives, and it is gitignored.**
  Never hardcode a name, email, phone number or salary figure into a module,
  and never commit a real value into `profile.example.yaml` — the repo is
  public and its history was started clean on purpose. The resume assets are
  gitignored for the same reason: their header carries a phone number.
- **Channel posts come in by paste, never by scraping.** WhatsApp Channels
  have no public API and driving WhatsApp Web risks the account, so
  `autopilot ingest` takes pasted text and runs it through the identical
  gates and scoring. Nothing about a pasted job is trusted more than an API
  one.
- **Sources must have a public API.** LinkedIn, Naukri, Internshala and
  Wellfound forbid automated scraping and will restrict the account. They are
  handled browser-assisted, with Kevin already signed in.
- **A role must say it takes freshers.** `targets.experience_level: fresher`
  in profile.yaml turns on the `no-fresher-signal` gate: a post has to carry
  an explicit signal (a junior/intern/graduate/trainee title, "Experience:
  Freshers", "0-1 years", "entry level", "campus hire", and similar) or it is
  rejected. Rejecting "2+ years" is not the same thing — silence about
  experience overwhelmingly means "we expect some", and those were being
  queued as matches. Set `experience_level` to anything else to turn the gate
  off.
- **Rejections are stored, not discarded.** The `gated` status keeps every
  filtered job so thresholds can be recalibrated against real data. This is
  how the `not-a-tech-role` gate was found to be necessary.
- **A dead source must not kill the run.** `pipeline.run` catches per-source
  exceptions and records them in the `runs` table.
- **Deduplicate on company+title, not URL.** The same role is reposted under
  fresh URLs every few weeks.

## Scoring

Two stages. Hard gates disqualify outright: `not-a-tech-role`, `senior-title`,
`asks-for-money`, `requires-Ny-experience` (N > 2), `location-mismatch`,
`blacklisted-company`. Survivors get 0-100 from title match (35), stack
overlap (35), entry-level signals (15), location (15). Queue threshold is 55,
set in `pipeline.QUEUE_THRESHOLD`.

Skill matching is word-boundary anchored and skips `AMBIGUOUS_SKILLS`
(`move`, `rag`, `java`, `css`, ...). Substring matching previously scored a
Handyman listing 29/100 because "rag" appears inside "storage".

## System Operating Modes

Each mode is a persona defined in `.claude/modes/`. It sets what to focus on,
how to judge the work, and the output format.

| Mode | File | Switch (Claude Code) | Badge |
| --- | --- | --- | --- |
| Business Analyst | `ba.md` | `/mode ba` or `/ba` | `[Mode: Business Analyst]` |
| System Architect | `architect.md` | `/mode architect` or `/architect` | `[Mode: System Architect]` |
| Engineer (**default**) | `engineer.md` | `/mode engineer` or `/code` | `[Mode: Engineer]` |
| Auditor | `auditor.md` | `/mode auditor` or `/audit` | `[Mode: Auditor]` |

- `/mode reset` returns to Engineer.
- **Start every response with the current mode's badge on its own line.** If no mode has been chosen this session, use `[Mode: Engineer]`.
- A mode lasts until it is switched or reset. The Rules above apply in every mode.
- Codex and `agy` don't have these slash commands. Say "switch to ba mode" and they read `.claude/modes/ba.md` directly.
