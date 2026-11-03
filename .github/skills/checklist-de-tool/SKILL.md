---
name: checklist-de-tool
description: Verifica requisitos de segurança e qualidade para tools do Empório Agente.
---

<!-- Responsabilidade: fornecer a lista de verificação para implementar ou revisar tools do Empório Agente. -->

Ao implementar ou revisar uma tool, confira:

1. Argumentos validados com Pydantic.
2. Sem `SELECT *`; colunas explicitamente listadas.
3. Usa `conn_leitura`.
4. Não devolve `description_raw`, telefone nem e-mail.
5. Não aceita `customer_id` como argumento do modelo.
6. Usa `agora()` ou `hoje()` em vez de `date.today()`/`datetime.now()` fora de `config.py`.
7. Tem teste em `tests/`.
8. Erros voltam como resultado estruturado.
