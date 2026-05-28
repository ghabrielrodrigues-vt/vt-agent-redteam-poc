# vt-agent-redteam — POC (Promptfoo Edition)

Adversarial red-team harness for LiveKit-hosted K–12 AI agents. Spike + working
prototype with **Promptfoo** scenario generation, **PyRIT** multi-turn attacks,
and an **HTTP moderation runner** for Nerdy Tutor API testing.

**Repository:** https://github.com/ghabrielrodrigues-vt/vt-agent-redteam-poc

---

## Start here

**Read [`docs/GUIDE.md`](docs/GUIDE.md)** for the consolidated POC guide.
For the leadership-ready operational answer, read
[`docs/12-livekit-redteam-hardening-solution.md`](docs/12-livekit-redteam-hardening-solution.md).

| If you need… | Open |
|--------------|------|
| Everything in one place | [`docs/GUIDE.md`](docs/GUIDE.md) |
| Step-by-step local setup | [`SETUP.md`](SETUP.md) |
| Component status | [`STATUS.md`](STATUS.md) |
| LiveKit deploy/reuse solution | [`docs/12-livekit-redteam-hardening-solution.md`](docs/12-livekit-redteam-hardening-solution.md) |
| 12-tool safety comparison | [`docs/08-tooling-dossier.md`](docs/08-tooling-dossier.md) |
| Real agent lifecycle proof | [`docs/10-livekit-real-agent-proof.md`](docs/10-livekit-real-agent-proof.md) |
| 16 LiveKit agents + MVP priorities | [`docs/11-agent-coverage-matrix.md`](docs/11-agent-coverage-matrix.md) |
| Promptfoo generator | [`promptfoo/README.md`](promptfoo/README.md) |

Other files under `docs/` are optional deep dives.

---

## Validated at a glance

- **195 scenarios** (125 curated + 69 Promptfoo + 1 PyRIT) / 22 categories
- **45/45 pytest** green; Postgres writes validated
- **HTTP moderation runner** against `/api/nerd-tutor/moderate-text`
- **Real `livekit-agents` worker** lifecycle on local LiveKit
- **PyRIT Crescendo** — target refused 3-turn PII escalation

Details and commands: [`docs/GUIDE.md`](docs/GUIDE.md) §3–9.

---

## Layout

```
├── docs/GUIDE.md       ← start here
├── SETUP.md            ← run locally
├── STATUS.md           ← build status
├── prototype/          ← vt_agent_redteam Python package
├── promptfoo/          ← scenario generator
├── pyrit/              ← multi-turn attacks
└── livekit-local/      ← Docker + mock agent
```

---

## Lighter sibling repo

https://github.com/ghabrielrodrigues-vt/poc-moderation-red-team — docs-first spike
without Promptfoo/PyRIT folders.

---

## Security

Never commit `.env.local` or API keys. See [`docs/GUIDE.md`](docs/GUIDE.md) §14.

## License

Proprietary — Varsity Tutors internal use.
