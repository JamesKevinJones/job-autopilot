<div align="center">

# Job Autopilot

### Reads 1,300 job postings a day so you read six.

A personal job-discovery pipeline: seven public APIs in, one ranked approval
queue out, a summary in your inbox at 21:00. Python 3.11, six modules, SQLite,
no framework.

![Python](https://img.shields.io/badge/python-3.11-1B2632?labelColor=0B1016)
![SQLite](https://img.shields.io/badge/storage-sqlite-1B2632?labelColor=0B1016)
![Dependencies](https://img.shields.io/badge/dependencies-2-3FD0C9?labelColor=0B1016)
![License](https://img.shields.io/badge/license-MIT-1B2632?labelColor=0B1016)

</div>

---

## The problem

Job boards optimise for volume. A search for "junior software engineer" returns
hundreds of postings a day, most of which are senior roles with "junior" in the
body text, non-technical roles that matched on a stray keyword, or listings that
want two years of experience from a fresher.

Reading them is the work. This automates the reading, not the applying.

## What it does not do

**It does not submit applications.** That's a deliberate limit, not a missing
feature.

Auto-submitting means entering a real person's address and phone number into
third-party forms and clicking irreversible controls unattended. In practice it
also gets accounts restricted and trips ATS duplicate filters, which costs you
the roles you actually wanted. So the pipeline stops at a reviewed queue, and
submission stays browser-assisted with a human confirming each one.

Everything up to that point — discovery, deduplication, gating, scoring,
tracking, summarising — is automatic.

## How it scores

Two stages, because they answer different questions.

**Hard gates** disqualify outright. A posting that trips any of these is stored
with a reason and never scored:

| Gate | Catches |
| --- | --- |
| `not-a-tech-role` | Keyword collisions from non-technical listings |
| `senior-title` | "Senior", "Lead", "Staff", "Principal" |
| `asks-for-money` | Training fees and pay-to-apply schemes |
| `requires-Ny-experience` | Explicit demands beyond 2 years |
| `location-mismatch` | Outside your locations, and not remote |
| `blacklisted-company` | Your own opt-out list |

**Survivors get 0–100** from four weighted signals: title match (35), stack
overlap (35), entry-level signals (15), location (15). Anything at 55 or above
enters the approval queue. The threshold is one constant in `pipeline.py`.

Every score ships with its reasoning — the digest prints a **For** and an
**Against** line per job, so a bad ranking is debuggable rather than mysterious.

## Three things worth stealing

**Rejections are stored, not discarded.** Gated jobs stay in the database with
their reason. That's what makes thresholds tunable against real data instead of
guesses — the `not-a-tech-role` gate exists because the rejection log showed it
was needed.

**Skill matching is word-boundary anchored.** Substring matching once scored a
handyman listing 29/100 because `rag` appears inside `storage`. Short ambiguous
tags (`move`, `rag`, `java`, `css`) are held in an `AMBIGUOUS_SKILLS` set and
matched only on word boundaries.

**Deduplicate on company + title, not URL.** The same role is reposted under a
fresh URL every few weeks. Keying on the URL means seeing it as new every time.

A dead source also can't kill the run: `pipeline.run` catches per-source
exceptions and records them in the `runs` table, so one API outage costs you one
source, not the day.

## Sources

Seven public APIs, no scraping: **RemoteOK**, **Remotive**, **Arbeitnow**,
**Jobicy**, **Himalayas**, **Greenhouse** and **Lever** board endpoints.

LinkedIn, Naukri, Internshala and Wellfound are deliberately absent. Their terms
forbid automated access and enforcement means a restricted account, so those
stay browser-assisted.

## Running it

```bash
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
cp profile.example.yaml profile.yaml
```

Fill in `profile.yaml` — it's the single source of truth for every field, and
it's gitignored so your real details never reach the repo. Then:

```bash
python -m autopilot run
```

```bash
python -m autopilot queue
```

Other commands: `digest` writes today's summary, `daily` runs both and is what
the scheduler calls, `approve <fingerprint>` marks a job as applied, and
`skip <fingerprint>` dismisses one.

On Windows, `scripts/daily.ps1` is the Task Scheduler entry point.

## Structure

```
profile.example.yaml   template; copy to profile.yaml (gitignored)
autopilot/
  config.py            loads profile.yaml, defines paths
  models.py            Job, Verdict, ScoredJob
  scorer.py            hard gates + weighted score
  store.py             SQLite schema and queries
  pipeline.py          fetch -> gate -> score -> store
  digest.py            daily markdown summary
  cli.py               command line entry point
  sources/             one module per board API
scripts/daily.ps1      scheduled task entry point
docs/DAILY/<date>.md   generated summaries
```

## Privacy

`profile.yaml`, the resume assets and any OAuth token are gitignored. The
repository holds the pipeline, not the person — this history was started clean
so no personal data has ever been committed to it.

## Elsewhere

Part of [my portfolio](https://portfolio-website-eight-kappa-iwtiz3w2ef.vercel.app),
which introduces each project by the thing it refuses to do. This one refuses to
submit the application.

Related: [job-rag](https://github.com/JamesKevinJones/job-rag) takes the other end
of the same problem — conversational search over listings rather than scoring and
queueing them.

## License

MIT — see [LICENSE](LICENSE).
