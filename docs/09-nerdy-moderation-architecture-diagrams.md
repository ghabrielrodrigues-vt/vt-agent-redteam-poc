# Nerdy Tutor Text Moderation — Architecture Diagrams

Visual reference for the production moderation stack in
`student-onboarding-orchestration` (`lib/profanity`, Nerdy Tutor session hook).

**Companion (plain text for Google Docs):**
`../../vt-onboarding/nerdy-moderation-original-vs-cmp-google-docs.txt`

**Export PNG/SVG:** copy any Mermaid block into [mermaid.live](https://mermaid.live) → Actions → Export.

---

## 1. System overview

```mermaid
flowchart TB
  subgraph Learner["Learner surfaces"]
    TYPED["Typed chat / Quick replies / Intent picker"]
    SPOKEN["Microphone → LiveKit → Agent STT"]
  end

  subgraph Client["Browser — Nerdy Tutor session"]
    HOOK["use-nerd-tutor-session"]
    PREP["prepareNerdTutorChatMessage"]
    STTMOD["buildModeratedUserTranscriptEntry"]
    L1C["L1 client — censorTextL1"]
    API["POST /api/nerd-tutor/moderate-text"]
    UI["ConversationFeed / transcript state"]
    LK["LiveKit nerdy/user topic"]
  end

  subgraph Server["Next.js server"]
    ROUTE["moderate-text route — auth + rate limit"]
    PIPE["server-moderation.ts"]
    L1S["L1 static"]
    L2["L2 DB terms cache"]
    L3["L3 OpenAI moderation + censor"]
  end

  subgraph Data["Persistence and learning"]
    DB[("learner_text_moderation_terms")]
    REV["Human review → enabled terms"]
  end

  subgraph Agent["LiveKit agent"]
    BOT["Tutor LLM / TTS / avatar"]
  end

  TYPED --> HOOK --> PREP
  SPOKEN --> Agent
  Agent -->|"transcript role=user"| HOOK --> STTMOD

  PREP --> L1C
  STTMOD --> L1C
  L1C -->|"no L1 hit"| API
  API --> ROUTE --> PIPE
  PIPE --> L1S --> L2 --> L3
  L3 -->|"discovered terms"| DB
  DB --> REV --> L2
  L3 --> ROUTE --> API

  PREP -->|"safe text only"| LK
  PREP --> UI
  STTMOD --> UI
  LK --> BOT

  style L1C fill:#e8f5e9
  style L1S fill:#e8f5e9
  style L2 fill:#fff3e0
  style L3 fill:#e3f2fd
  style DB fill:#fce4ec
```

---

## 2. Primary rule — moderate-then-publish (original branch)

Branch: `vt4s-10659-nerdy-tutor-moderation`

```mermaid
sequenceDiagram
  participant U as Learner
  participant UI as Transcript UI
  participant M as moderateNerdTutorUserText
  participant L1 as L1 static
  participant API as /api/nerd-tutor/moderate-text
  participant S as L1→L2→L3 pipeline
  participant LK as LiveKit agent
  participant DB as Supabase terms

  Note over U,LK: Typed path
  U->>UI: Send message
  UI->>M: prepareNerdTutorChatMessage(text)
  M->>L1: censorTextL1
  alt L1 censored
    L1-->>M: censored text
  else L1 unchanged
    M->>API: POST { text, previousText? }
    API->>S: moderateTextForRoute
    S->>S: L1 → L2 → L3 if needed
    opt L3 flagged
      S->>DB: upsert terms (needs_review)
    end
    S-->>API: { text, layer }
    API-->>M: safe text
  end
  M->>LK: publishData kind=text (safe only)
  M->>UI: appendTranscript (safe only)

  Note over U,LK: Spoken path (STT echo)
  U->>LK: audio
  LK-->>UI: agent transcript user role
  UI->>M: buildModeratedUserTranscriptEntry
  M->>L1: same pipeline
  M->>UI: append safe caption only
```

---

## 3. Server pipeline — deterministic layers, OpenAI, feedback loop

```mermaid
flowchart LR
  IN["Learner text"] --> L1["L1 Static<br/>obscenity + seeds + patterns<br/>deterministic, $0"]
  L1 -->|match| OUT1["Censored text<br/>layer=static"]
  L1 -->|no match| L2["L2 Database<br/>direct + contextual terms<br/>deterministic, $0"]
  L2 -->|match| OUT2["Censored text<br/>layer=database"]
  L2 -->|no match| OM["OpenAI omni-moderation"]
  OM -->|not flagged| OUT3["Original text<br/>layer=none"]
  OM -->|flagged| RW["OpenAI censor rewrite<br/>JSON spans + terms"]
  RW --> OUT4["Censored text<br/>layer=openai"]
  RW --> DISC["Validate terms vs input"]
  DISC --> DB[("learner_text_moderation_terms<br/>needs_review / enabled")]
  DB -->|review + enable| L2
  DB -->|promote direct| L1

  style L1 fill:#c8e6c9
  style L2 fill:#ffe0b2
  style OM fill:#bbdefb
  style RW fill:#bbdefb
  style DB fill:#f8bbd0
```

**L1/L2:** every hit avoids OpenAI moderation + rewrite → lower cost and latency.

**Multilingual:** L3 flags any language; validated terms land in the DB (`normalized_term`, `language_code`); after review, L2 blocks locally without another OpenAI call.

---

## 4. Experiment branches (optional layers on top of the original)

```mermaid
flowchart TB
  CORE["Original: moderate-then-publish + L1/L2/L3<br/>(PRIMARY)"]

  CORE --> EXP1["exp publish-gate<br/>same gate, isolated MVP"]
  CORE --> EXP2["exp transcript-quarantine<br/>L1 before state append"]
  CORE --> EXP3["exp render-safety<br/>L1 at ConversationFeed"]
  CORE --> ALT1["alt channel-codec<br/>L1 on wire encode only"]
  CORE --> ALT2["alt live-redaction<br/>streaming obscenity"]
  CORE --> CMP1["cmp pending-reveal<br/>UI queue placeholder"]
  CORE --> CMP2["cmp stt-hold-line<br/>400ms STT buffer"]
  CORE --> CMP3["cmp display-projection<br/>displayTranscript read model"]

  EXP2 -.->|"defense in depth"| CORE
  EXP3 -.->|"last mile"| CORE
  CMP1 -.->|"UX only"| CORE
  CMP2 -.->|"STT tuning only"| CORE
  CMP3 -.->|"render contract only"| CORE

  style CORE fill:#4caf50,color:#fff
  style EXP2 fill:#fff9c4
  style EXP3 fill:#fff9c4
  style CMP1 fill:#e1bee7
  style CMP2 fill:#e1bee7
  style CMP3 fill:#e1bee7
```

---

## Legend

| Color / layer | Meaning |
|---------------|---------|
| Green (L1) | Static, local, deterministic |
| Orange (L2) | Database — learned, reviewed terms |
| Blue (L3) | OpenAI moderation + rewrite |
| Pink (DB) | Multilingual learning loop |

## Key files

| Path | Role |
|------|------|
| `lib/profanity/static-moderation.ts` | L1 lexicon + normalization |
| `lib/profanity/server-moderation.ts` | L2/L3 server pipeline |
| `lib/profanity/client-moderation.ts` | Client L1 then API |
| `lib/nerd-tutor/text-moderation.ts` | Nerdy Tutor client wrapper + metrics |
| `lib/nerd-tutor/session/chat-message-moderation.ts` | Typed pre-publish gate |
| `lib/nerd-tutor/session/user-transcript-moderation.ts` | STT echo ingress gate |
| `app/(app)/api/nerd-tutor/moderate-text/route.ts` | Authenticated API entry |
