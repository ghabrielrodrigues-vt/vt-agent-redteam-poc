# Rodando LiveKit Localmente — Resumo Não-Técnico

## Por que "local" importa?

Cada vez que testamos a IA, duas coisas custam para nós:

1. **Dinheiro**: LiveKit Cloud cobra por participant-minute, OpenAI cobra por
   token, e nosso Supabase de staging é compartilhado.
2. **Poluição**: Execuções de teste contra staging aparecem em métricas e
   dashboards, misturadas com os dados de teste reais dos entrevistadores.

A ferramenta de red-team vai rodar **muito** — em cada pull request, toda semana
como canary, mais qualquer hora que alguém estiver desenvolvendo. A gente precisa
fazer a maior parte dessas execuções custar zero e não poluir nada.

O truque é rodar a infra do LiveKit **no laptop do dev** para as execuções baratas e
frequentes, e só bater na cloud para as execuções que precisam ser realistas.

## As três opções, sem floreio

Há três formas de "rodar LiveKit localmente", e elas não são intercambiáveis:

1. **Agent no laptop, LiveKit na cloud.** Mais fácil se você tem acesso AWS. A IA
   roda na sua máquina mas os servidores de roteamento estão na cloud. Custa um
   pouco de dinheiro por execução.
2. **Tudo no laptop.** Setup um pouco maior (Docker), mas completamente grátis e
   capaz de funcionar offline. É o que a maioria das execuções de red-team vai
   usar, especialmente as por pull-request.
3. **Pular o LiveKit completamente.** Existe um modo "room falsa" para testes
   unitários. É muito rápido, mas só funciona se o código de teste estiver na mesma
   linguagem de programação que a IA. Como nossa IA é em TypeScript e o chefe quer
   a ferramenta em Python, essa opção está fechada para nós.

## O que a gente vai realmente fazer

- Para desenvolvimento diário da ferramenta de red-team, e para todo check por
  pull-request: **tudo no laptop** (opção 2).
- Para o canary semanal que pega problemas que a gente não vê de outra forma
  (configs de deploy, comportamento real do WebRTC, latência real do OpenAI):
  **agent local-ou-cloud contra LiveKit cloud** (opção 1).

## Como vai ser a experiência do dev

Um engenheiro novo no time deveria conseguir clonar a pasta do POC e rodar dois
comandos:

```
docker compose up        # sobe LiveKit no laptop
./scripts/dispatch-test-room.sh
```

…e ver um cenário de red-team rodando contra a IA, com o resultado impresso no
terminal. Os scripts e templates que tornam isso possível moram na pasta
`livekit-local/` do POC.
