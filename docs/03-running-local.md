# Running LiveKit Locally

There are three ways to "run LiveKit locally". They serve different purposes and have
very different setup costs. Choose based on what you are trying to do.

## Option A — Local agent + LiveKit Cloud staging

**Use when**: you want to debug agent code in an environment as close to production
as possible.

The agent worker runs on your laptop in watch mode and connects to the LiveKit Cloud
staging instance. Rooms are real. OpenAI Realtime calls go to the real OpenAI API.
Recording uploads to staging Supabase Storage.

```bash
git clone git@github.com:varsitytutors/livekit-agents.git
cd livekit-agents
npm install
aws sso login  # or whichever auth method grants tutors-service/st/livekit access
npm run dev
```

The `dev` script pulls all secrets (LiveKit URL/key/secret, OpenAI key, Supabase
Storage creds) from AWS Secrets Manager. No `.env` file is required.

Pros:

- Behavior identical to production.
- No infra to manage.
- Multiple devs can run agents simultaneously against the same staging cluster.

Cons:

- Requires AWS access. If you are stuck on SSO or VPN, you cannot run.
- Consumes LiveKit Cloud staging minutes.
- "Local" only refers to the agent process — everything else is in the cloud.

## Option B — Local LiveKit Server via Docker

**Use when**: you want isolation from any cloud infra, or to test network behavior and
media routing offline. Also the right path for **PR-time red-team tests** that must be
cheap and fast.

```bash
docker run --rm -p 7880:7880 -p 7881:7881 -p 7882:7882/udp \
  -e LIVEKIT_KEYS="devkey: secret" \
  livekit/livekit-server --dev
```

That starts a single-node LiveKit Server listening on localhost. Default dev
credentials are `devkey` / `secret`.

Then point the agent at it:

```bash
LIVEKIT_URL=ws://localhost:7880 \
LIVEKIT_API_KEY=devkey \
LIVEKIT_API_SECRET=secret \
OPENAI_API_KEY=sk-...your-key... \
npm run dev
```

(You can put this in `.env.local` and source it before `npm run dev`.)

Pros:

- No cloud dependencies for routing.
- No AWS auth required.
- Free — no per-session cost.
- Reproducible: the same `docker run` works on any machine.

Cons:

- OpenAI Realtime still calls the real OpenAI API. Fully isolated network testing
  would require a local LLM substitute (out of POC scope).
- Supabase Storage upload still requires real credentials. The POC skips recording in
  local mode and only captures transcript.
- Some LiveKit features (TURN servers, S3 recording) need extra config to work locally;
  we do not need them for the POC.

The Docker image is small (~80MB). Disk and memory footprint are negligible.

## Option C — In-process test mode (not viable for us)

The LiveKit Agents SDK has a test-harness mode where you instantiate an `AgentSession`
in memory and inject turns without a real room. It is fast — milliseconds per turn — and
ideal for unit tests inside the agent repo.

**Why we cannot use it for the POC**: that mode only works when test code is in the
**same language and process** as the agent. The spike requires the red-team package in
Python. Our agents are TypeScript. The two do not share a process.

The right place for in-process tests is **inside `livekit-agents` itself**, as unit
checks for the assessor or state machine. That is a different scope of work.

## Decision matrix

| Goal | Recommended option |
| --- | --- |
| Debug agent bug | A (Cloud staging, real conditions) |
| Develop red-team package | B (Docker, no cloud cost, full isolation) |
| Run red-team tests on every PR in CI | B (Docker started by GitHub Actions) |
| Weekly canary catching deploy/config drift | A (Cloud staging, real environment) |
| Pure unit test of Mouth/Brain logic | C (in-process, but lives in TS repo, not Python package) |

## What `livekit-local/` in this folder contains

The `livekit-local/` subfolder of this POC has:

- `docker-compose.yml` — LiveKit Server stack + optional turn server
- `.env.template` — environment template for agent pointing at localhost
- `scripts/dispatch-test-room.sh` — uses `livekit-cli` (`lk`) to create a room with
  red-team metadata and dispatch the agent
- `scripts/install-livekit-cli.sh` — installs `lk` CLI via Homebrew

The intent is that, given a clean laptop, a dev can run `docker compose up` and
`./scripts/dispatch-test-room.sh` and see the prototype red-team scenario running
end-to-end against a locally running agent.
