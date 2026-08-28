# Verify

Proof commands. Run from the project root.

## Dependencies

```powershell
python -m pip install -r requirements.txt
```

## Full discovery pass

```powershell
python -m autopilot run
```

Expected: a line like `fetched=492 new=480 queued=11 gated=447`.
`fetched` in the low hundreds means the source filters are working; a number
near 100 with most jobs gated as `not-a-tech-role` means a source has fallen
back to its unfiltered feed.

## Inspect the queue

```powershell
python -m autopilot queue --limit 12
```

Expected: junior/trainee/intern software titles with a score, matched stack
terms, and a URL. Any non-technical title appearing here is a scorer bug.

## Generate today's summary

```powershell
python -m autopilot digest
```

Expected: prints the path to `docs/DAILY/<today>.md`.

## Check the scheduled task

```powershell
Get-ScheduledTask -TaskName "JobAutopilotDaily" | Select-Object TaskName, State
Get-ScheduledTaskInfo -TaskName "JobAutopilotDaily" | Select-Object LastRunTime, LastTaskResult, NextRunTime
```

Expected: `State = Ready`, `LastTaskResult = 0` after a run.

Run it on demand:

```powershell
Start-ScheduledTask -TaskName "JobAutopilotDaily"
```

## Score distribution sanity check

```powershell
python -c "from autopilot.store import connect; c=connect().__enter__(); print([tuple(r) for r in c.execute('SELECT status, count(*) FROM jobs GROUP BY status')])"
```

Expected: a `queued` count in the single or low double digits per day. Zero
queued across several runs means the threshold or the gates need recalibrating
— check `rejected_by` counts before changing the threshold.

## Fresher filter sanity check

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3;c=sqlite3.connect('data/autopilot.db');print([tuple(r) for r in c.execute(\"SELECT rejected_by,count(*) FROM jobs WHERE status='gated' GROUP BY rejected_by ORDER BY 2 DESC\")])"
```

Expected: `no-fresher-signal` present but well below `not-a-tech-role` and
`senior-title`. If it is the largest bucket, or if any posting whose title
contains junior/intern/graduate/trainee appears under it, the signal
detection in `scorer.has_fresher_signal` has regressed.
