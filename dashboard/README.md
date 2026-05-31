# Red Team MVP Control Room

Single-page dashboard for tracking the RED TEAM MVP implementation across the framework repo, SOO integration repo, canonical docs, and external knowledge sources.

## Run

Generate a fresh status payload once:

```bash
node dashboard/scripts/redteam-dashboard.mjs
```

Serve the dashboard and refresh status every three seconds:

```bash
node dashboard/scripts/redteam-dashboard.mjs --serve --port 4177
```

Open:

```text
http://127.0.0.1:4177/dashboard/
```

The browser polls `dashboard/data/redteam-status.json` every five seconds. The Node server serves the repository root so file links can open the referenced local repo files.

## Update Test Status

After running the framework test suite, update `dashboard/data/test-status.json` with the latest summary and timestamp. The dashboard will pick it up on the next poll.
