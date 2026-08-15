# State

_Last updated: 2026-08-13 (evening)_

## Status

Fully operational. Discovery, gating, scoring, queueing, the daily digest, the
Windows toast, Gmail delivery and the scheduled task are all live and verified
end to end.

## What runs tonight

- Scheduled task **JobAutopilotDaily** at 21:00 IST, using `.venv`.
  Verified manually: `LastTaskResult = 0`.
- Last run: `fetched=661 new=1 queued=0 gated=1`.
- Delivery confirmed: `gmail: sent to kj6384647@gmail.com`.

## Environment

The project has its own virtualenv at `.venv` (Python 3.14). **Never call bare
`python`** — on this machine it resolves to the Claude agent's venv, which has
no pip and none of these dependencies. Use `jobs.ps1`, which handles it:

```powershell
& "C:\Users\kj638\Kevin codes\job-autopilot\jobs.ps1" queue
```

Gmail is authorised. `credentials.json` and `gmail.token.json` are both
gitignored and must never be committed.

## Open decision for Kevin

**The queue is empty and will likely stay empty.** Fresher-only plus
Chennai-only onsite is a very narrow filter: the same 661 postings queued 11
roles before the tightening and 0 after. The Greenhouse/Lever boards that
supply Indian roles (Meesho, Groww, PhonePe, HackerRank, Druva) hire almost
entirely in Bangalore and Hyderabad.

To re-open those metros, add them back to `ONSITE_LOCATIONS` in
`autopilot/scorer.py` and to `targets.locations` in `profile.yaml`.

## Next step

No major work outstanding — both redesigns are shipped and the pipeline runs
itself. Candidates, in order of value:

1. Resume tailoring per queued job (`tailor.py`), reading the base resume from
   `assets/resume/`.
2. Browser-assisted submission flow for LinkedIn/Internshala/Naukri, where
   Kevin is already signed in and confirms each submit.
3. Follow-up nudges at day 7 and 14 off the `applied` status.

## Done recently

- Clock redesigned as a split-flap departure board and deployed
  (https://kevin-clock.vercel.app). Fixed a render-loop `setInterval` leak, an
  external time-API dependency, a blocking `alert()`, and a missing SPA
  rewrite. See that repo's README.
- Resume rebuilt as an ATS-clean 2-page PDF at
  `assets/resume/Kevin_Jones_Resume.pdf`, verified by extracting its text back
  out. A 1-page variant means dropping a fourth project — Kevin's call.
- CodeAut0 redesigned as a drafting sheet and deployed
  (https://codeaut0.vercel.app). Removed fabricated node metrics (hardcoded
  11/27/41/72 rendered on every node), a hardcoded green "Operational" health
  badge, and dead navigation. Fixed MSW being gated behind DEV, which left the
  deployed demo with no API at all.
- Gmail delivery authorised and verified: digest emails send successfully.
- Bangalore added as a secondary onsite location.
- GitHub cleaned: 17 active repos, all described, 13 archived, forks removed.

## Known rough edges

- `Software Development Engineer in Test II` slips past `LEVELLED_SENIOR_RE`
  because the level suffix is not adjacent to the role word.
- Queue threshold is 45, set from an observed distribution that has since
  narrowed. Worth revisiting once a few hundred more jobs are scored.
- The `Clock` repo's git history is 11/15 commits by two other people. Not
  resolved; see the conversation on contributors vs collaborators.
