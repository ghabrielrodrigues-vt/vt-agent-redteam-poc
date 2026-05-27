# Primer de LiveKit — Resumo Não-Técnico

## O que é LiveKit?

LiveKit é a tecnologia que permite a duas pessoas (ou uma pessoa e uma IA) ter uma
conversa de áudio ou vídeo ao vivo pelo browser. É o mesmo tipo de encanamento que
Zoom ou Google Meet usam, mas projetado para ser embutido nos nossos próprios produtos
em vez de ser uma ferramenta de reunião isolada.

## Por que a VT usa?

Todos os nossos produtos com avatar falante — o AI Interviewer, os tutores Lemon
Slice, os futuros avatares Nerdy — precisam de três coisas:

1. Uma forma de o aluno ou candidato **falar** pelo browser.
2. Um lugar onde o áudio é **roteado** em tempo real, com latência baixa.
3. Uma forma de a **nossa IA escutar e responder**.

LiveKit fornece (2) diretamente, e nos dá o toolkit para construir (1) e (3) em cima.

## As três coisas chamadas de "LiveKit"

Quando alguém diz "LiveKit", geralmente está se referindo a uma de três coisas. As
pessoas confundem constantemente:

- **LiveKit Server**: o programa de computador propriamente dito que cuida do
  roteamento de áudio. Conseguimos rodar ele no laptop para desenvolvimento local.
- **LiveKit Cloud**: uma versão paga hospedada do mesmo programa, gerida pela empresa
  LiveKit. É o que está rodando em produção e staging hoje.
- **LiveKit Agents SDK**: uma biblioteca separada que ajuda a escrever "bots de IA"
  que entram numa conversa como se fossem uma pessoa. É a parte sobre a qual nossos
  engenheiros realmente escrevem código.

Quando o chefe diz "os agents estão hospedados no LiveKit", ele quer dizer que nossos
bots de IA rodam dentro do LiveKit Cloud, escutando a conversa através do roteamento
do LiveKit.

## Por que isso importa para o trabalho de red-team

A gente quer testar se a IA lida com prompts perigosos de forma segura. Para isso, a
ferramenta de red-team tem que **fingir ser uma pessoa na conversa**, enviar à IA um
prompt arriscado, escutar o que a IA responde, e julgar se foi uma resposta segura.

LiveKit é o meio onde essa conversa acontece. Então nossa ferramenta de red-team
precisa falar LiveKit também — abrir uma room, entrar, enviar algo adversarial,
capturar a resposta.

É por isso que o chefe citou LiveKit especificamente: cada um dos nossos produtos com
avatar compartilha esse mesmo encanamento, então uma única ferramenta que conhece
LiveKit consegue testar todos.

## O que a ferramenta de red-team NÃO vai fazer

Ela não vai substituir nenhum dos filtros de segurança que já bloqueiam inputs ruins
no Nerdy Tutor. Esses impedem alunos de mandar coisas prejudiciais para a IA logo de
cara. A ferramenta de red-team faz o trabalho inverso: força a IA a ouvir algo
prejudicial para a gente verificar se a IA **responde** de forma segura. As duas
camadas são complementares.
