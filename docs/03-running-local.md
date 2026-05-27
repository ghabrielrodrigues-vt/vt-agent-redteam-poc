# Rodando LiveKit Localmente

Há três formas de "rodar LiveKit localmente". Elas servem a propósitos diferentes e
têm custos de setup muito diferentes. Escolha pelo que você está tentando fazer.

## Opção A — Agent local + LiveKit Cloud staging

**Use quando**: você quer debugar o código do agent num ambiente o mais próximo
possível de produção.

O agent worker roda no seu laptop, em watch mode, e se conecta à instância de
staging do LiveKit Cloud. As rooms são reais. As chamadas para OpenAI Realtime vão
pra API real do OpenAI. A gravação faz upload para o Supabase Storage de staging.

```bash
git clone git@github.com:varsitytutors/livekit-agents.git
cd livekit-agents
npm install
aws sso login  # ou o método de auth que dá acesso a tutors-service/st/livekit
npm run dev
```

O script `dev` puxa todos os secrets (LiveKit URL/key/secret, OpenAI key, creds do
Supabase Storage) do AWS Secrets Manager. Nenhum arquivo `.env` é necessário.

Prós:

- Comportamento idêntico ao de produção.
- Sem infra para gerir.
- Múltiplos devs podem rodar agents simultaneamente contra o mesmo cluster de staging.

Contras:

- Requer acesso AWS. Se você estiver travado no SSO ou VPN, não consegue rodar.
- Consome minutos de staging do LiveKit Cloud.
- "Local" só se refere ao processo do agent — todo o resto fica na cloud.

## Opção B — LiveKit Server local via Docker

**Use quando**: você quer isolar de qualquer infra na cloud, ou testar comportamento
de rede e roteamento de mídia offline. Também é o caminho certo para **testes de
red-team em PR-time** que precisam ser baratos e rápidos.

```bash
docker run --rm -p 7880:7880 -p 7881:7881 -p 7882:7882/udp \
  -e LIVEKIT_KEYS="devkey: secret" \
  livekit/livekit-server --dev
```

Isso sobe um LiveKit Server single-node escutando em localhost. As credenciais
padrão de dev são `devkey` / `secret`.

Aí aponta o agent pra ele:

```bash
LIVEKIT_URL=ws://localhost:7880 \
LIVEKIT_API_KEY=devkey \
LIVEKIT_API_SECRET=secret \
OPENAI_API_KEY=sk-...sua-chave... \
npm run dev
```

(Pode colocar isso num `.env.local` e dar source antes do `npm run dev`.)

Prós:

- Sem dependências de cloud para roteamento.
- Sem auth AWS necessária.
- Grátis — não custa nada por sessão.
- Reproduzível: o mesmo `docker run` funciona em qualquer máquina.

Contras:

- OpenAI Realtime ainda chama a API real do OpenAI. Teste isolado de rede
  exigiria um substituto local de LLM (fora do escopo do POC).
- Upload do Supabase Storage ainda requer credenciais reais. O POC vai pular a
  gravação em modo local e só capturar transcript.
- Algumas features do LiveKit (servidores TURN, gravação para S3) precisam de
  configuração extra para funcionar localmente; não precisamos delas para o POC.

A imagem Docker é pequena (~80MB). Disco e footprint de memória são desprezíveis.

## Opção C — Modo in-process de teste (não viável para nós)

O LiveKit Agents SDK tem um modo test-harness onde você instancia um `AgentSession`
em memória e injeta turnos sem uma room real. Isso é rápido — milissegundos por
turno — e ideal para testes unitários dentro do repo do agent.

**Por que não conseguimos usar para o POC**: esse modo só funciona quando o código
de teste está na **mesma linguagem e processo** do agent. O chefe quer o pacote
red-team em Python. Nossos agents são em TypeScript. Os dois não compartilham
processo.

O lugar certo para testes in-process seria **dentro do próprio `livekit-agents`**,
como checks unitários do assessor ou da state machine. Esse é um escopo de
trabalho diferente.

## Matriz de decisão

| Objetivo | Opção recomendada |
| --- | --- |
| Debugar bug do agent | A (Cloud staging, condições reais) |
| Desenvolver o pacote de red-team | B (Docker, sem custo de cloud, isolamento total) |
| Rodar testes de red-team em cada PR no CI | B (Docker iniciado pelo GitHub Actions) |
| Canary semanal pegando deriva de deploy/config | A (Cloud staging, ambiente real) |
| Teste unitário puro da lógica Mouth/Brain | C (in-process, mas mora no repo TS, não no pacote Python) |

## O que `livekit-local/` nesta pasta contém

A subpasta `livekit-local/` deste POC tem:

- `docker-compose.yml` — stack LiveKit Server + turn server opcional
- `.env.template` — template de ambiente para o agent apontando pra localhost
- `scripts/dispatch-test-room.sh` — usa a CLI `livekit-cli` (`lk`) para criar uma
  room com metadata de red-team e dispatchar o agent
- `scripts/install-livekit-cli.sh` — instala a CLI `lk` via Homebrew

A intenção é que, dado um laptop limpo, um dev consiga rodar `docker compose up` e
`./scripts/dispatch-test-room.sh` e ver o cenário protótipo de red-team rodando
end-to-end contra um agent rodando localmente.
