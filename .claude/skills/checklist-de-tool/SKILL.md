<!-- Responsabilidade: fornecer o checklist crítico para validação de tools do Empório da Música em Claude Code. -->

---
name: checklist-de-tool
description: Checklist de validação para tools do projeto Empório da Música.
---

## Checklist

1. argumentos validados com Pydantic
2. sem `SELECT *`, colunas listadas
3. usa `conn_leitura`
4. não devolve `description_raw`, telefone nem e-mail
5. não aceita `customer_id` como argumento
6. usa `hoje()` em vez de `date.today()`
7. tem teste em `tests/`
8. erros voltam como resultado estruturado
