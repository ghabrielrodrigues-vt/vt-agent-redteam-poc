# Arquitetura do Agent — Resumo Não-Técnico

## Como o AI Interviewer realmente é por dentro?

O AI Interviewer não é uma IA só. São **duas IAs trabalhando juntas**, com jobs bem
diferentes.

- A **Mouth** é a voz que o candidato escuta. O único job dela é falar naturalmente,
  escutar, e seguir instruções. Ela não tem permissão de decidir que pergunta fazer
  em seguida ou se a resposta do candidato foi boa.
- A **Brain** é invisível para o candidato. Ela lê cada resposta que o candidato dá,
  **pontua** como uma professora corrigindo dever de casa, e aí **escreve a próxima
  instrução** para a Mouth — "faz um follow-up", "vai pro próximo tópico", "encerra,
  o tempo está acabando", e assim por diante.

A gente separou as duas dessa forma por três razões:

1. A Mouth nunca pode acidentalmente revelar o score para o candidato, porque ela
   não conhece.
2. A Brain corrige cada resposta **de forma independente**, sem ver o resto da
   conversa. Isso impede que uma resposta ruim arraste scores posteriores ou que uma
   resposta boa dê benefício da dúvida ao candidato.
3. O flow da entrevista é **código baseado em regras**, não LLM. Isso torna a
   experiência consistente em milhares de entrevistas.

## Por que isso é relevante para testes de red-team?

Por causa de três escolhas arquiteturais, nosso agent é **incomumente fácil de
fazer red-team**:

1. **Toda configuração mora na "metadata da room".** Quando uma nova entrevista
   começa, o servidor anexa um pequeno documento JSON à room LiveKit com o system
   prompt, matéria, tipo de entrevista, e credenciais de storage. O agent lê isso
   e roda a entrevista de acordo. O agent **não tem banco, nem conhecimento de API**
   próprio.

   Para nós, isso significa que um teste de red-team pode disparar uma room com a
   configuração que quisermos e exercitar o agent em qualquer estado — diferentes
   matérias, diferentes prompts, diferentes personas — sem tocar dados de produção.

2. **No fim de toda entrevista, o agent escreve tudo de volta na metadata da room**
   — o transcript completo, cada score, o caminho da gravação. É o lugar perfeito
   para uma ferramenta de red-team ler a conversa e julgar.

3. **O formato do sistema é o mesmo em todos os nossos agents LiveKit.** Todos rodam
   pelo mesmo padrão Mouth-Brain, mesmo canal de config via metadata da room, mesmo
   passo de finalização. Uma ferramenta de red-team que aprende esse padrão uma vez
   funciona contra cada agent que produzimos.

## O que isso significa para o POC

O POC não vai mudar o código do agent. Ele vai ficar do lado, como ferramenta
externa que:

1. **Finge ser um candidato**: abre uma room LiveKit com um cenário escolhido na
   metadata, entra, e "conversa" com o agent.
2. **Lê o transcript final e os scores da metadata da room** depois que a conversa
   termina.
3. **Julga as respostas do agent** contra os critérios de segurança que a empresa
   considera importantes.
4. **Escreve o resultado numa pequena tabela Supabase** para termos registro de
   cada execução.

Como todos os nossos agents LiveKit compartilham a mesma estrutura, a mesma
ferramenta funciona contra o AI Interviewer hoje, contra os tutores Lemon Slice em
seguida, e contra qualquer avatar futuro que a empresa vier a construir.
