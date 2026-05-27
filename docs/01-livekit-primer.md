# Primer de LiveKit

LiveKit é uma plataforma de mídia em tempo real — WebRTC por baixo. Pense nele como
"Zoom-as-a-service, mas programável". É a fundação sobre a qual todo agent de voz e
avatar da VT é construído.

A confusão que a maioria das pessoas enfrenta é que **o nome "LiveKit" se refere a
três coisas diferentes** que vêm juntas. Uma vez que você as separa, a arquitetura
fica simples.

## As três camadas

| Camada | O que é | Onde aparece no stack da VT |
| --- | --- | --- |
| **LiveKit Server** | Servidor WebRTC open source (binário Go). Hospeda "rooms", roteia áudio/vídeo/dados entre participantes. Pode rodar localmente via Docker. | Não está em nenhum repo da VT — não hospedamos. Consumimos a versão Cloud. |
| **LiveKit Cloud** | Versão hospedada do LiveKit Server, gerida pela LiveKit Inc. É o que usamos em produção e staging hoje. | Nossos agents autenticam contra o secret AWS `tutors-service/st/livekit`. |
| **LiveKit Agents SDK** | Framework Node e Python para escrever "bots" que entram em rooms como participantes com poderes extras (capturar áudio, rodar STT→LLM→TTS, publicar áudio de volta). | É exatamente sobre o que `varsitytutors/livekit-agents` foi construído (`@livekit/agents` v1.2.2). |

O "agent" sobre o qual o chefe fala é um **processo** (um worker Node, no nosso caso)
que se conecta a uma room LiveKit **como se fosse um participante**, mas com a
capacidade de ouvir o áudio do humano, rodar um modelo, e falar de volta.

## Por que isso importa para red-teaming

Fazer red-team de um agent significa: mandar input adversarial pra ele, observar o
output, pontuar se o output é seguro. Com LiveKit, "input" e "output" são ambos
**streams de áudio roteados através de uma room**.

Isso significa que um harness de red-team precisa ou:

1. **Ser um participante sintético** — entrar numa room como usuário falso, enviar
   texto adversarial (ou áudio sintetizado), capturar a resposta do agent, pontuar.
   Esse caminho é agnóstico de linguagem (funciona para agents TS ou Python) e
   espelha o runtime real do LiveKit.
2. **Ou rodar o agent in-process** sob um harness de teste — pula a room. Mais
   rápido, mas só funciona se o harness estiver na mesma linguagem do agent. Como
   nossos agents são TypeScript e o pacote que o chefe quer é Python, esse caminho
   está fechado.

Implicação: o POC vai ser "participante sintético" contra um servidor LiveKit real
(local ou staging).

## Anatomia de uma sessão (passo a passo concreto)

Isso é o que acontece quando um candidato a tutor inicia uma entrevista hoje:

```
1. Dashboard admin chama o tutors-service em Go
2. tutors-service chama o LiveKit Server SDK:
     - Cria room "interview-<uuid>"
     - Define metadata da room (interview_id, subject, system_prompt, storage creds)
     - Dispatcha o agent (agentName = "interview-agent")
3. LiveKit Cloud roteia o dispatch pra um worker no pool livekit-agents
4. Processo worker (Node) acorda:
     - Faz parse da metadata
     - Conecta no websocket do OpenAI Realtime (a "Mouth")
     - Inicia Room Composite Egress (gravação para Supabase Storage)
     - Entra na room como participante
5. Candidato abre o browser, recebe um token, entra na mesma room
6. Negociação WebRTC: áudio flui nas duas direções via LiveKit Cloud
7. Loop da entrevista roda (ver docs/02-agent-architecture.md)
8. Candidato desconecta:
     - Agent faz merge do transcript + state machine na metadata da room
     - Egress para, gravação termina de subir
     - LiveKit dispara webhook room_finished → tutors-service consome
```

O candidato e o agent **nunca conversam diretamente**. Cada byte passa pelo
LiveKit Cloud. Essa é a razão de rooms serem a única unidade sensata de isolamento
para red-team: uma room = um cenário de teste.

## Glossário de vocabulário

Esses termos aparecem o tempo todo no código LiveKit:

- **Room** — o container da sessão. Uma room = uma conversa. Tem metadata, participantes, tracks.
- **Participant** — qualquer um na room: candidato humano, agent worker, recorder.
- **Track** — um stream de áudio ou vídeo publicado por um participante.
- **Data channel** — mensagens de texto trocadas entre participantes (sem áudio).
- **Egress** — gravação server-side ou streaming dos tracks de uma room. Usado para os MP4s das entrevistas.
- **Dispatch** — LiveKit Cloud avisando um pool de workers "esta room precisa de um agent chamado X".
- **Metadata** — JSON arbitrário anexado a uma room ou participante. Usada extensivamente como canal de config do agent.
- **Token** — JWT que um cliente apresenta para entrar numa room. Codifica identidade, nome da room, permissões.

## Dimensão de custo (para contexto)

LiveKit Cloud cobra por participant-minutes. Uma execução de red-team que abre N
rooms × M turnos × ~30s por turno acumula. O design do pacote precisa ser barato por
teste, e é por isso que "servidor local via Docker para testes em PR-time, Cloud
staging para canary semanal" é a divisão proposta — ver `docs/03-running-local.md`
e `docs/04-poc-design.md`.
