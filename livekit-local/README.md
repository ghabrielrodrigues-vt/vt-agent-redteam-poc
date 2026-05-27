# LiveKit Local — turn-key local stack

Everything in this folder exists to let you run a complete LiveKit + agent stack on
your laptop, without any AWS auth, without consuming staging minutes, and without
mocking anything that matters.

## What is here

```
livekit-local/
├── README.md
├── docker-compose.yml           — LiveKit Server (single node, dev mode)
├── .env.template                — env file template for the agent
├── scripts/
│   ├── install-livekit-cli.sh   — brew install lk
│   └── dispatch-test-room.sh    — create a red-team-shaped room + dispatch the agent
└── livekit-agents/              — cloned from varsitytutors/livekit-agents
```

The `livekit-agents/` folder is a clone of `https://github.com/varsitytutors/livekit-agents`
at whatever commit was current when this POC was set up. Update via:

```bash
cd livekit-agents
git fetch && git checkout main && git pull
```

## First-run setup (one time)

```bash
# 1. Install the LiveKit CLI
./scripts/install-livekit-cli.sh

# 2. Create your local env file from the template
cp .env.template .env.local
# Edit .env.local and paste a real OPENAI_API_KEY

# 3. Install the agent's npm dependencies
cd livekit-agents
npm install
cd ..
```

## Bringing the stack up

```bash
# Terminal 1 — LiveKit Server
docker compose up
# Wait for: "starting LiveKit server" + "running version X" + "listening 0.0.0.0:7880"

# Terminal 2 — agent
cd livekit-agents
set -a && source ../.env.local && set +a
npm run dev
# Wait for: "Agent registered" / "worker running"

# Terminal 3 — trigger a test scenario
./scripts/dispatch-test-room.sh
```

The agent in terminal 2 should log a dispatched job, parse the metadata, connect to
the room, and start its introduction. The Realtime API call goes to OpenAI; the audio
routes through localhost.

To actually **talk** to the agent, generate a participant token (the dispatch script
prints the exact command) and open https://meet.livekit.io/ with the token and
`ws://localhost:7880` as the server URL.

## Tearing down

```bash
docker compose down
```

This stops and removes the LiveKit Server container. Your agent process in terminal 2
will exit cleanly when its websocket to the server drops.

## When this folder is good enough

When `./scripts/dispatch-test-room.sh` reliably produces a dispatched agent in a
local room, the foundation is in place. The Python harness in `../prototype/` is what
turns this into red-team coverage.

## Troubleshooting

**`docker compose up` complains about port 7880 in use**: another LiveKit process is
already running (likely from a previous session). Run `docker ps | grep livekit` and
`docker stop <id>`.

**Agent fails with "Cannot connect to ws://localhost:7880"**: the LiveKit Server is
not running. Check `docker ps`.

**Agent fails with "Missing or invalid room metadata"**: the `lk room create` call did
not attach metadata. Re-run `dispatch-test-room.sh` and verify the JSON output above
the dispatch line.

**Agent connects but says nothing**: check that `OPENAI_API_KEY` is valid in
`.env.local` and that the key has Realtime API access enabled.

**`lk` command not found**: `./scripts/install-livekit-cli.sh`.
