# Conexão com a Moderação do Nerdy Tutor — Resumo Não-Técnico

## O que parece igual e o que de fato é diferente

Quando o chefe disse "a gente tem alguma lógica que é largamente copiada", ele
estava certo — **mas só em alto nível**. No nível onde você de fato escreve código,
as duas coisas são jobs diferentes.

O trabalho de moderação do Nerdy Tutor que eu fiz nas últimas semanas é como um
**porteiro na porta** da IA. Quando um aluno digita algo arriscado, o porteiro
decide se deixa a mensagem entrar. Se sim, a IA vê; se não, a IA nunca fica sabendo
que o aluno tentou.

O POC de red-team é como um **cliente oculto**. Ele se aproxima da IA, diz algo
projetado pra fazer ela tropeçar, escuta o que a IA responde, e dá nota se a IA se
saiu bem. O ponto **não é proteger a IA de input ruim** — é **verificar que a IA
se comporta bem quando algo ruim passa**.

Ambos os jobs são necessários. Você quer um porteiro **e** quer clientes ocultos.
Eles checam modos de falha diferentes.

## O que do trabalho de moderação eu vou reaproveitar

O trabalho não foi duplicado. Três pedaços concretos se transferem direto para o
POC de red-team:

1. **A lista de prompts arriscados e categorias.** Eu passei semanas curando a
   lista específica de educação de palavras, frases e intenções ruins que aparecem
   no nosso contexto de tutoria. Essa lista vira o **menu inicial** de prompts de
   teste que a ferramenta de red-team manda pra IA. Um time começando do zero
   precisaria de meses de revisões de incidente pra montar algo equivalente.

2. **A integração da OpenAI Moderation API.** Eu pluguei o classificador de
   segurança da OpenAI no pipeline de moderação pra decidir se um texto que chega é
   arriscado. O POC de red-team usa **o mesmo classificador** pra decidir se a
   resposta que a IA está mandando é arriscada. Mesmos padrões de código, direção
   oposta.

3. **A forma como armazenamos os dados.** O schema, a categorização, o tratamento
   de language-code, o padrão de detalhes em JSON — eu construí tudo isso pro banco
   de moderação. O POC de red-team reusa as mesmas convenções pra tabela de
   resultados, pra que qualquer um lendo qualquer das duas tabelas se sinta em
   casa.

## O que não posso reaproveitar, e por que tudo bem

Duas coisas precisam ficar pra trás:

1. **A arquitetura do pipeline em si.** A stack L1/L2/L3 mora dentro do repo
   student-onboarding como uma rota de servidor Next.js. Ainda não é biblioteca, e
   extrair daí é projeto diferente. Pro POC de red-team, eu não preciso da stack —
   eu só preciso de pedaços dos inputs dela e de uma das chamadas de API.

2. **A ideia de "bloquear antes da IA ver".** Voz LiveKit não tem um passo onde eu
   consiga interceptar a fala do usuário antes que a IA escute; no momento em que o
   áudio chega, ele já está dentro do speech-to-text interno da IA. Tudo bem.
   Bloquear inputs é o job do pipeline de moderação de produção. Testar outputs é
   o job do POC de red-team.

## O que vou contar pro time

A história que eu vou defender no spike doc é:

> "O trabalho de moderação que eu fiz (PR #1667 e PR #1669) sai como **filtragem
> de input em produção** — o porteiro. O POC de red-team sai como um **pacote
> Python separado** que cada repo de agent LiveKit pode importar — o cliente
> oculto. Eles compartilham as categorias, a chamada de OpenAI Moderation, e os
> padrões de armazenamento, mas rodam em lugares diferentes, em momentos
> diferentes, pra objetivos diferentes."

Isso é honesto, defensável, e claro. Evita supervender — dizer "isso unifica toda
moderação" seria tecnicamente errado e convidaria crítica.
