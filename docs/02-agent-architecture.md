# Arquitetura do Agent — `livekit-agents` (Tutor Interview)

Este documento descreve a arquitetura interna de `varsitytutors/livekit-agents`, o
repo que contém os agents LiveKit em produção na VT. Hoje tem um agent
(`tutor-interview`); a estrutura foi projetada para hospedar mais.

## Visão geral: Mouth + Brain

Dois papéis de LLM trabalhando juntos. **A Mouth nunca decide o que fazer a seguir
— a Brain decide.**

- **Mouth**: OpenAI Realtime (`gpt-realtime-mini`). Fala, escuta, segue instruções.
  Tem uma tool relevante ao job: `assess_answer`. Nunca avalia. Nunca decide o flow.
- **Brain**: Assessor LLM (LLM-as-judge, não-realtime) + State machine (código
  determinístico). Pontua cada resposta, decide o que acontece em seguida, gera as
  próximas instruções para a Mouth.

Essa separação é forçada arquiteturalmente: a Mouth não tem acesso a scores ou
state. O Assessor não tem acesso ao histórico de conversa (julga cada resposta em
isolamento, para evitar viés de ancoragem).

## Mapa de pastas

```
src/
  agents/tutor-interview/
    agent.ts            — Entry point. Liga Mouth + Brain, tool calling, egress, escrita de metadata
    state-machine.ts    — Fases, tracking de questões, gestão de tempo, scores
    assessor.ts         — Pontua respostas do candidato (LLM-as-judge)
    prompt-builder.ts   — Constrói prompts de intro e wrap-up a partir da config
    greeting-controller.ts — Saudação condicional ao tipo (HIRING vs SUBJECT)
    models.ts           — Multi-model factory (OpenAI / Google Gemini)
    types.ts            — Schemas Zod para metadata da room, types de state interno
    constants.ts        — Thresholds de timing
  lib/
    logger.ts           — Logging estruturado com Winston
    metadata.ts         — Parser de metadata da room (snake_case → camelCase)
    egress.ts           — Room Composite Egress gravando para Supabase Storage
    monitoring.ts       — Session tracking, alertas de erro, handlers globais
    langfuse.ts         — Observabilidade de chamadas LLM
    otel.ts             — Export OpenTelemetry
  index.ts              — Registro do agent, filtro por nome de room, entry CLI
```

Stack: TypeScript, Node.js 22, LiveKit Agents SDK 1.2.2, Zod, Winston.

## Modelo de configuração: zero database, tudo via room-metadata

Este é o fato arquitetural mais importante para o POC de red-team.

O agent tem **zero acesso a banco**, **zero conhecimento da API do tutors-service**,
e **zero credenciais hardcoded**. Tudo o que ele precisa chega na metadata da room
LiveKit, definida pelo tutors-service em Go quando a room é criada:

```json
{
  "interview_id": "uuid",
  "subject_name": "Portugues",
  "interview_type": "HIRING",
  "system_prompt": "Instruções completas da entrevista do dashboard admin...",
  "storage": {
    "endpoint": "...", "access_key": "...", "secret_key": "...",
    "bucket": "...", "region": "..."
  }
}
```

O `system_prompt` contém toda a estrutura da entrevista — persona, áreas de
habilidade, orientação de perguntas, guardrails — montada pelo tutors-service a
partir do dashboard admin. Adicionar uma nova matéria ou mudar comportamento da
entrevista significa atualizar dados no admin UI; nenhuma mudança de código de
agent, nenhum redeploy.

**Por que isso importa para red-teaming**: um teste de red-team pode subir uma room
com metadata arbitrária (diferente `system_prompt`, diferente `interview_type`, etc.)
e exercitar o agent em qualquer configuração sem precisar de acesso ao banco admin
de produção. A "superfície de configuração" é a metadata da room, e ela está sob
nosso controle.

## Fluxo por turno

```
┌─────────────────────────────────────────────────────────┐
│                        MOUTH                             │
│                  (Realtime LLM)                          │
│                                                          │
│  1. Fala a pergunta (seguindo instruções da Brain)       │
│  2. Escuta a resposta do candidato                       │
│  3. Chama assess_answer(question, candidateResponse)     │
│                         │                                │
│                         ▼                                │
│  6. Recebe instruções ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ │
│  7. Fala naturalmente seguindo instruções                │ │
└─────────────────────────────────────────────────────────┘ │
                          │                                 │
                          ▼                                 │
┌─────────────────────────────────────────────────────────┐ │
│                        BRAIN                             │ │
│                                                          │ │
│  4a. Assessor LLM pontua a resposta                      │ │
│      → { score: 7, quality: "adequate", reasoning, ... } │ │
│                                                          │ │
│  4b. State machine processa o score                      │ │
│      → decide: follow-up / próximo tópico / wrap-up      │ │
│                                                          │ │
│  5. Prompt builder gera instruções                       │ │
│      → "Ask a follow-up about their teaching method"  ──┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Tools com escopo por fase

O conjunto de tools da Mouth muda conforme a fase da entrevista. A Brain troca tools
da lista da Mouth conforme o state avança:

| Fase | Tools disponíveis para a Mouth |
| --- | --- |
| `introduction` | `start_interview` |
| `interviewing` | `assess_answer`, `request_end_interview` |
| `wrap_up` | `end_interview` |

Transições de state são determinísticas:

| De | Para | Trigger |
| --- | --- | --- |
| `introduction` | `interviewing` | Mouth chama `start_interview` após candidato sinalizar prontidão |
| `interviewing` | `wrap_up` | Tempo restante abaixo do threshold, OU Mouth chama `request_end_interview` |
| `wrap_up` | `ended` | Mouth chama `end_interview`, OU candidato desconecta, OU watchdog de wrap-up dispara |

## Superfície condicional ao tipo

O agent roda dois tipos de entrevista (`HIRING` e `SUBJECT`). A superfície de
customização por tipo é deliberadamente pequena — **apenas três arquivos ramificam
por `interview_type`**:

1. `greeting-controller.ts` — frase de enquadramento da saudação falada
2. `prompt-builder.ts` `buildIntroductionPrompt` — `typeLabel` e bullet de
   explicação de formato
3. `assessor.ts` — system prompt do assessor inclui o tipo para que o LLM julgador
   ajuste a régua

Todo o resto (state machine, tools, fases, finalização) é agnóstico de tipo.
Adicionar um tipo futuro toca apenas esses três arquivos.

## Finalização (quando o candidato desconecta)

1. Agent extrai transcript do histórico de conversa do Realtime LLM
2. Dados da state machine (fases, scores, timing) são serializados
3. Ambos são feitos merge na metadata da room via
   `RoomServiceClient.updateRoomMetadata` (a room ainda está viva nesse momento)
4. Webhook local dispara se `WEBHOOK_LOCAL_URL` estiver setado (teste em dev)
5. Egress para → gravação termina de subir para Supabase Storage
6. Room fecha → LiveKit envia webhook `room_finished` para o tutors-service com a
   metadata atualizada

O backend recebe transcript, scores e caminho da gravação em um payload único.

## O que isso diz sobre pontos de integração para red-team

Há três costuras naturais nessa arquitetura onde um harness de red-team pode plugar:

| Costura | O que dá | Custo |
| --- | --- | --- |
| **Metadata da room** (canal de config) | Levar o agent para qualquer persona, matéria, configuração de prompt via injeção de metadata. Sem mudança de código. | Grátis. É como o POC vai configurar cenários. |
| **Resposta da tool `assess_answer`** | O score/reasoning do assessor por turno é JSON estruturado. Um scorer de red-team poderia observar. | Requer acesso ao log stream interno do agent ou traces do Langfuse. |
| **Transcript final na metadata da room** | Conversa completa, scores e caminho de gravação são escritos de volta na metadata no fim da sessão. Read-only. | Grátis. Fonte primária de dados para scoring post-hoc. |

O POC deve consumir o **transcript final** (costura 3) para scoring e usar **injeção
de metadata da room** (costura 1) para configuração de cenário. A costura 2 é para
integração futura mais profunda se quisermos alerta por turno.
