
## Known environment issue (Aug 1, 2026)

VS Code debugger fails with "Timed out waiting for launcher to connect."
Cause: Python installed from Microsoft Store (C:\Program Files\WindowsApps\...),
which has sandboxed permissions the debugger can't work around.
Fix when there's time: install Python from python.org, delete .venv, recreate.
Not blocking — pytest and print() work fine.

# Profiling notes (Exercise 2)

Write findings here BEFORE you clean anything. Predictions included.
Being wrong in writing is how calibration develops.

## Row counts

| table | rows | cols |
|---|---|---|
|  |  |  |

## Suspicious columns

## My predictions

- Distinct department spellings I expect to find:6
- Fraction of lab values I expect to be unparseable:80%
- Anything I bet is broken that the profiler hasn't shown yet: missing data, misspelling, number errors etc etc 

## What actually turned out to be true
