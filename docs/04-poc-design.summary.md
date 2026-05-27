# Design do POC — Resumo Não-Técnico

## O que é essa ferramenta, em uma frase?

Um pacote Python pequeno que finge ser um aluno ou candidato mal-intencionado, manda
prompts perigosos para nossos agents de IA pelo LiveKit, verifica se a IA lida com
eles de forma segura, e escreve o resultado numa pequena tabela de banco.

## Onde vai ficar?

No próprio repositório. **Não dentro** de nenhum repo de agent existente. Razões:

- Nossos agents são escritos em TypeScript; o chefe pediu Python especificamente.
- A gente quer que outros times (Lemon Slice, video agent, avatares futuros)
  consigam instalar essa ferramenta com um comando — não conseguem se ela estiver
  enterrada dentro do repo do agent de entrevista.
- A ferramenta vai evoluir mais rápido que qualquer agent individual. Manter
  separado impede merges do tipo "quebrei o red-team enquanto consertava o agent de
  entrevista".

## Como ela realmente funciona?

Pensa nela como um robô testador:

1. A ferramenta lê uma lista de "prompts ruins" que a gente mantém (organizados por
   categoria: violência, conteúdo sexual, automutilação, tentativas de jailbreak,
   vazamento de system prompt, etc.).
2. Para cada prompt ruim, a ferramenta **abre uma conversa LiveKit** e finge ser o
   aluno ou candidato.
3. A ferramenta manda o prompt ruim e **grava o que a IA responde**.
4. A ferramenta **julga a resposta da IA** usando vários métodos de scoring:
   - A Moderation API da OpenAI flagga a resposta como insegura?
   - A IA recusou educadamente, ou entrou no jogo?
   - A IA acidentalmente revelou suas instruções de sistema?
5. A ferramenta **salva o resultado** numa tabela Supabase para a gente conseguir
   olhar depois.

## Quando ela roda?

Quatro momentos, deliberadamente:

1. **Em todo pull request** para um repo de agent LiveKit — roda um conjunto rápido
   (~10 cenários) contra um LiveKit local pra que o autor do PR saiba se quebrou
   alguma coisa.
2. **Antes de todo deploy** — roda o conjunto completo contra um LiveKit local,
   bloqueia o deploy se muitos falharem.
3. **Antes de promover para produção** — roda o conjunto completo contra o ambiente
   de staging real para pegar problemas de configuração de deploy.
4. **Uma vez por semana** — roda o conjunto completo contra o ambiente de produção
   ao vivo como canary, mesmo que nenhum deploy tenha acontecido. Pega deriva
   lenta, mudanças de API de parceiros, atualizações de modelo da OpenAI.

Se qualquer um deles falhar cenários demais, o time recebe alerta (canal Slack, a
decidir depois).

## E sobre outras ferramentas tipo Promptfoo?

O chefe mencionou fazer shopping da nossa geração de prompts para Promptfoo. É um
ótimo encaixe — mas para a próxima iteração, não a primeira. A primeira versão usa
uma lista hand-curated de prompts ruins pra gente saber que os testes são
reproduzíveis. Uma vez que isso estiver estável, Promptfoo pode gerar novas
categorias e a gente materializa no mesmo formato.

## Como o POC se conecta com meu trabalho de moderação no Nerdy Tutor?

Ver `05-moderation-connection.summary.md` para resposta completa. Versão bem curta:
as categorias e a lista de frases ruins que eu já curei para o filtro de input do
Nerdy Tutor viram o **corpus seed** dos prompts adversariais da ferramenta de
red-team. A integração da OpenAI Moderation API que eu fiz como filtro L2 de input
é **reusada como scorer das respostas da IA** na ferramenta de red-team. O design
do schema Supabase segue os mesmos padrões. O trabalho de moderação não foi
desperdiçado — ele produziu ativos reaproveitáveis para essa nova camada.

## Como "pronto" se parece para o POC?

O POC é um writeup, um skeleton funcional, e um cenário end-to-end. Não é uma
ferramenta finalizada. Depois que o spike for aceito, endurecer no release v0.1 é
um item de trabalho separado.
