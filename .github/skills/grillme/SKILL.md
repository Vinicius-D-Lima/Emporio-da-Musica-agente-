---
name: grillme
description: "Use quando o usuário pedir 'grill me', 'me questione' ou quiser testar uma ideia, plano, requisito ou decisão por meio de perguntas críticas antes de implementar."
---

<!-- Responsabilidade: conduzir uma entrevista crítica, iterativa e focada para esclarecer decisões antes de agir. -->

# Grill Me

Ajude o usuário a fortalecer uma ideia, plano, requisito ou decisão fazendo perguntas críticas e sequenciais. O objetivo é revelar ambiguidades, premissas frágeis, riscos e casos extremos antes de propor ou implementar uma solução.

## Procedimento

1. Leia o contexto disponível e identifique o tema exato que será questionado. Não pergunte algo que já esteja respondido no contexto.
2. Faça **uma pergunta por vez**, começando pela decisão de maior impacto ou pela ambiguidade que mais pode alterar o resultado.
3. Prefira perguntas específicas e neutras. Quando útil, explique brevemente por que a resposta importa e ofereça opções concretas sem limitar respostas alternativas.
4. Após cada resposta, incorpore o que foi decidido, identifique a próxima lacuna relevante e faça a pergunta seguinte. Não repita perguntas já respondidas.
5. Teste premissas com cenários concretos, dependências, falhas, limites e casos extremos. Questione com respeito; não seja adversarial por estilo nem trate toda ideia como errada.
6. Não apresente uma longa lista de perguntas de uma vez. Não implemente, edite arquivos nem encerre com uma solução prematura enquanto ainda houver decisões importantes sem resposta.
7. Se o usuário pedir para parar ou responder "não sei", respeite isso. Registre a incerteza como ponto em aberto; não decida em nome dele.
8. Encerre quando as decisões de maior impacto estiverem claras, quando não restarem lacunas relevantes ou quando o usuário pedir uma síntese. Apresente então:
   - decisões confirmadas;
   - riscos ou premissas ainda não validadas;
   - perguntas em aberto;
   - próximos passos sugeridos, sem executá-los a menos que o usuário peça.

## Restrições

- Não transforme a conversa em um interrogatório: mantenha cada pergunta necessária e relacionada ao objetivo.
- Não invente requisitos, respostas, dados ou decisões do usuário.
- Separe fatos conhecidos, suposições e recomendações.
- Se o usuário mudar de objetivo, confirme o novo foco e continue a partir dele.
