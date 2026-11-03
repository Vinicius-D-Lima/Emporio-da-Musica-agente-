---
description: Executa um passo do plano do Empório Agente seguindo o ciclo de testes e aprovação.
---

<!-- Responsabilidade: orientar a execução isolada e revisável de um passo do plano do projeto. -->

Execute APENAS o Passo ${input:passo} de `docs/PLANO_DE_PASSOS.md`.

1. Transforme os critérios de aceite em testes pytest e mostre os testes antes de implementar.
2. Aguarde minha aprovação dos testes; depois implemente o mínimo para passar e rode pytest.
3. Se criou ou alterou uma tool, aplique a skill `checklist-de-tool` e consulte o agente revisor de segurança.
4. Resuma as alterações e liste o que ficou em `[DECIDIR]` ou `[PREENCHER]`.
5. Não faça commit antes da minha autorização. Depois do OK, faça um commit com a mensagem sugerida do passo.
6. Registre em `docs/USO_DE_IA.md` o que pedi, o que foi feito e o que corrigi.
7. Não adiante passos nem tome decisões que ainda dependem de validação.
