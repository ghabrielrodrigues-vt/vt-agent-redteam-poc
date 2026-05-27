# Plano de Implementação — Resumo Não-Técnico

Este documento é o output de uma revisão auto-conduzida do design do POC. Eu
representei tanto o papel do revisor durão fazendo perguntas duras, quanto o do
engenheiro dando respostas comprometidas. A transcrição completa está em
`06-implementation-plan.md`. Este resumo só captura as conclusões.

## O pacote

- **Um novo repositório**, separado de qualquer agent existente. Nome:
  `vt-agent-redteam`.
- **Distribuído via `pip install` de URL Git** em v0.1 — funciona em CI sem
  precisar de infra interna de PyPI.
- **Construído sobre o LiveKit Server SDK para Python**, direto. Sem camada de
  abstração pra v0.1; podemos adicionar depois se um dia suportarmos agents
  não-LiveKit.

## Como a ferramenta fala com a IA

O AI Interviewer atual só escuta áudio — não tem modo de input de texto. Então a
ferramenta de red-team vai:

1. **Digitar** o prompt ruim.
2. **Converter pra fala** usando TTS da OpenAI.
3. **Publicar esse áudio** numa room LiveKit como se fosse uma pessoa falando.
4. **Escutar de volta** a resposta da IA, transcrever, e julgar.

Isso bate com a experiência real do candidato, incluindo toda a variância de
speech-to-text que vem junto. Custo por cenário: ~$0.015. Custo por canary
semanal: cerca de $1.50. Desprezível.

## O que é testado

Um cenário leva no máximo **90 segundos**, até **4 turnos**. Cenários rodam **um
de cada vez** em v0.1 pra manter atribuição de falha limpa; concorrência vem
depois.

Pra lidar com o fato de que a IA é não-determinística, **cada cenário roda 3
vezes** e o resultado é por voto majoritário. Custa mais, mas impede que flakes de
execução única falhem o build.

## Como é o corpus

O catálogo de prompts ruins é **arquivos YAML dentro do repo do pacote**,
commitados sob controle de versão. Isso significa:

- Rodar a mesma versão do pacote duas vezes produz os mesmos testes.
- Revisar o corpus é um PR normal.
- Quando um cenário falha, o time sabe qual versão do corpus produziu.

A primeira versão do corpus vem de três lugares: minha lista de moderação do
Nerdy Tutor (já curada), categorias da OpenAI Moderation API (linha-base de
calibração), e modos de falha específicos de LiveKit (prompt injection, vazamento
de system prompt, etc.).

Promptfoo vai gerar **novos** prompts depois (em v0.2), mas esses vão ser
revisados por humano e commitados no corpus — não regenerados em toda execução. Foi
o que o chefe quis dizer com "weekly/nightly expansion beyond our fixed test set".

## Como as respostas da IA são pontuadas

**Três scorers saem em v0.1**:

1. **OpenAI Moderation API** — a mesma que o Nerdy Tutor usa como filtro de
   input, mas aplicada à **resposta** da IA em vez do input do usuário.
2. **Refusal detector** — checa se a IA recusou apropriadamente. Usa pattern
   matching simples mais uma pequena chamada LLM-as-judge pros edge cases que
   patterns perdem.
3. **Prompt-leak detector** — checa se a IA acidentalmente revelou partes das
   instruções de sistema.

O time pode plugar scorers próprios depois sem mudar o pacote.

## Onde os resultados vão

Uma única tabela Supabase chamada `redteam_runs`, no projeto Supabase VT4S
existente, sob um schema novo `redteam`. Uma linha por cenário por execução. O
chefe disse "can just be a Supabase table"; respeitamos.

Retenção: 90 dias quente, depois arquivada pra S3.

Acesso em CI: GitHub Actions → AWS OIDC → AWS Secrets Manager → service-role key
do Supabase. Sem secrets de longa duração no GitHub.

## Quando a ferramenta roda

Quatro momentos, cada um com uma régua diferente:

| Trigger | O que roda | Régua pra passar |
| --- | --- | --- |
| Todo PR | ~10 cenários (conjunto smoke) | 100% pass |
| Pré-deploy | Conjunto completo ~100 cenários | 90% pass |
| Cron semanal | Conjunto completo ~100 cenários contra staging | 85% pass, alerta caso contrário |
| Manual | Qualquer | Configurável |

Cada repo consumidor (`livekit-agents`, `lemonslice-demo-agent`, etc.) escreve
seu próprio workflow de GitHub Actions que importa o pacote. O pacote em si não é
dono de workflow nenhum — isso mantém o job do pacote pequeno.

## Riscos que a gente já conhece, com respostas

- **Não-determinismo da IA** → cada cenário roda 3 vezes.
- **Variância de reconhecimento de TTS** → armazenar a versão ouvida pela IA
  junto com a pretendida; detectar deriva em review.
- **Custo descontrolado** → limite duro de 90 segundos por cenário + budget cap
  por execução.
- **Agent crasha no meio do cenário** → registrado como falha, harness continua.
- **Fadiga de alerta** → começar conservador, ajustar thresholds depois de um
  mês.
- **Apodrecimento do corpus** → adições geradas pelo Promptfoo (v0.2) mais
  refresh trimestral de relatórios de incidente do time trust+safety.

## O que está explicitamente fora de escopo pra v0.1

Pra não sermos arrastados pra isso:

- Suporte a agents não-LiveKit (o chefe disse "evaluate that after").
- Alerta em tempo real por turno.
- Substituir qualquer pipeline de moderação de produção.
- STT custom.
- UI custom de dashboard (Supabase Studio é suficiente).
- Idiomas além de inglês (Português e Espanhol vêm na Fase 3).

## Fases e timeline

- **Spike (esta semana)**: esta pasta + protótipo funcional.
- **MVP v0.1 (~3 semanas)**: pacote em pé, 30 cenários, integrado contra
  `livekit-agents` como consumidor de referência, check de PR no ar.
- **Fase 2 (~2 semanas)**: canary semanal, alertas via Slack, Promptfoo, segundo
  consumidor de agent.
- **Fase 3 (contínuo)**: endurecimento, multi-language, dashboards, mais
  consumidores.

## Perguntas abertas pro time (não pra eu responder sozinho)

- Quem é dono do repo? (Trust+safety, VT4S, AI infra?)
- Ops quer um mirror privado de PyPI primeiro, ou `pip install git+ssh://` está
  ok?
- Números finais de threshold — começar em 90% / 85% ou diferente?
- Qual canal Slack pra alertas?
- SLA pra consertar um PR bloqueado por red-team?
- Fazemos red-team só no output da Mouth, ou também na Brain (o Assessor LLM)?
  A Brain tem sua própria superfície potencial de injeção.
