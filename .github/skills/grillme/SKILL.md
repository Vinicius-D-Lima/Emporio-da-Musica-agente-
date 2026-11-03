---
name: grillme
description: "Use quando o usuário pedir 'grill me', 'me questione' ou quiser testar uma ideia, plano, requisito ou decisão por meio de perguntas críticas antes de implementar."
---

<!-- Responsabilidade: conduzir uma entrevista crítica, iterativa e focada para esclarecer decisões antes de agir. -->

# Grill Me

Ajude o usuário a fortalecer uma ideia, plano, requisito ou decisão fazendo perguntas críticas e sequenciais. O objetivo é que ele entenda as alternativas, explique seu raciocínio e confirme a decisão com segurança, sem ser pressionado a escolher a opção preferida pelo assistente.

## Procedimento

1. Leia o contexto disponível e identifique o tema exato que será questionado. Não pergunte algo que já esteja respondido no contexto.
2. Faça **uma pergunta de decisão por vez**, começando pela escolha de maior impacto ou pela ambiguidade que mais pode alterar o resultado.
3. Apresente opções concretas e neutras, explique brevemente o que cada uma significa e quais consequências principais tem. Sempre inclua uma opção explícita equivalente a: **"Não entendi as opções; explique melhor antes de eu escolher."**
4. Se o usuário escolher a opção de explicação, não registre uma decisão nem avance para outra pergunta. Explique as alternativas com linguagem simples, exemplos práticos e trade-offs; depois, pergunte novamente sobre a mesma decisão.
5. Depois que o usuário indicar uma escolha, convide-o a explicar por que a escolheu. Não presuma os motivos a partir da opção selecionada.
6. Avalie o raciocínio com respeito e objetividade. Se notar uma premissa incorreta, risco relevante, contradição ou uma opção que pareça atender melhor ao objetivo, explique o ponto concreto e faça uma pergunta de acompanhamento para verificar se o usuário mantém ou quer rever a escolha.
7. Use cenários concretos, dependências, falhas e casos extremos para testar escolhas quando isso puder mudar a implementação. Faça uma pergunta de cada vez e não repita perguntas já respondidas.
8. Continue a conversa sobre a mesma decisão até o usuário demonstrar que entendeu os trade-offs e confirmar que deseja mantê-la, ou até pedir para parar. Não transforme isso em interrogatório, não tente vencer a discussão e não exija justificativas adicionais depois de uma confirmação informada.
9. Se o usuário disser "não sei", não invente uma decisão. Explique as alternativas e suas consequências; registre a escolha como aberta caso ele prefira não decidir.
10. Após a confirmação, registre a decisão em `docs/DECISOES_DO_USUARIO.md`, incluindo tema, decisão final, motivo informado pelo usuário, opções ou riscos considerados e pendências. Distinga claramente:
    - o que o usuário escolheu;
    - o motivo que ele próprio explicou;
    - recomendações, riscos ou consequências apontados pelo assistente;
    - dúvidas que permanecem abertas.
11. Não atribua ao usuário uma justificativa que ele não deu. Se ele não explicar o motivo ou delegar a decisão ao assistente, registre isso explicitamente como "motivo não informado" ou "decisão delegada ao assistente", e descreva a recomendação separadamente.
12. Não implemente, edite arquivos do produto nem encerre com uma solução prematura enquanto houver decisões importantes sem confirmação. A atualização deste registro de decisões só ocorre após confirmação do usuário.
13. Ao encerrar, apresente de forma concisa:
    - decisões confirmadas;
    - motivos informados pelo usuário;
    - recomendações e riscos considerados;
    - questões ainda abertas;
    - próximos passos sugeridos, sem executá-los a menos que o usuário peça.

## Estrutura do registro

Para cada decisão confirmada em `docs/DECISOES_DO_USUARIO.md`, use uma entrada com:

- **Tema**
- **Decisão confirmada**
- **Motivo informado pelo usuário**
- **Alternativas e trade-offs discutidos**
- **Riscos ou pendências**

Escreva em português, mantenha o registro conciso e atualize uma entrada existente quando o usuário revisar uma decisão, preservando a indicação de que ela foi substituída.

## Restrições

- Não transforme a conversa em um interrogatório: faça apenas perguntas necessárias e relacionadas ao objetivo.
- Não invente requisitos, respostas, dados, decisões ou justificativas.
- Separe fatos conhecidos, escolha do usuário e recomendação do assistente.
- A opção "não entendi" é um pedido de explicação, não uma decisão nem uma resposta negativa.
- Uma confirmação informada do usuário encerra o questionamento daquela decisão; não pressione para mudar a escolha.
- Se o usuário mudar de objetivo, confirme o novo foco e continue a partir dele.
