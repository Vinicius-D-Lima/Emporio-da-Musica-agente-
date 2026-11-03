<!-- Responsabilidade: registrar as decisões do projeto e o estado de itens em aberto para a implementação do Empório da Música. -->

# Decisões do projeto

- A abordagem adotada é function calling direto, sem framework, porque o agente tem poucas tools e um loop pequeno.
- Dados estruturados ficam em ferramentas com parâmetros fixos para evitar text-to-SQL e reduzir riscos de consulta inadequada.
- O manual de políticas é mantido no system prompt para facilitar prompt caching e maior previsibilidade.
- O banco é SQLite em um único arquivo para simplificar a execução local e o projeto de 2 dias.
- O `total_brl` é o valor oficial, com `total_needs_review` calculado no build para itens fora do esperado.
- `description_raw` fica no banco e não é exposta por nenhuma tool.
- Disponibilidade e promoção seguem regras explícitas do prompt e nunca são inferidas sem consulta.
- O modelo padrão é Gemini Flash e o fallback é Groq, apenas em erro de limite ou indisponibilidade.
- O cliente informa número do pedido e e-mail e o `customer_id` verificado fica na sessão.
- O agente trata acessórios e assuntos fora de escopo com redirecionamento educado.

## Em aberto

- Janela de contexto: truncar vs resumir.
- Implementação do classificador (regras + LLM em dúvida).
- Acessórios: busca na web vs lista fixa de lojas parceiras.
- Contradições do manual: telefone, e-mail e regras de parcelamento.
- Valor padrão de `REFERENCE_DATE`.
- Duas promoções ativas no mesmo produto.
- Cliente de LLM: SDK compatível com OpenAI vs nativos do provedor.

## Problemas nos dados

| problema | como tratei |
| --- | --- |
| [PREENCHER: problema] | [PREENCHER: como tratei] |
| [PREENCHER: problema] | [PREENCHER: como tratei] |

## Contradições do manual

| problema | como tratei |
| --- | --- |
| [PREENCHER: problema] | [PREENCHER: como tratei] |
| [PREENCHER: problema] | [PREENCHER: como tratei] |
