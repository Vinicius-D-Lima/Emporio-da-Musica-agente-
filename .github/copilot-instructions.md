<!-- Responsabilidade: fornecer ao GitHub Copilot o contexto, as decisões e as regras de trabalho permanentes deste repositório. -->

# Contexto do Empório Agente

## Decisões já tomadas

- Function calling direto, com loop manual e sem framework; são poucas tools e é necessário controlar explicitamente as chamadas.
- Dados estruturados são acessados por tools de parâmetros fixos, sem text-to-SQL.
- Tools previstas: `buscar_produtos`, `detalhes_produto`, `promocoes_ativas`, `verificar_cliente` e `status_pedido`; `simular_parcelamento` está planejada, mas não deve ser implementada antes do passo correspondente.
- O loop do agente tem limite de iterações; erros de execução de tools voltam como resultados estruturados e argumentos inválidos voltam como erros de validação.
- O manual fica no system prompt com prompt caching; RAG é evolução futura.
- Ordem do prompt: tools → persona + manual → resumo e histórico recente → mensagem nova.
- Gemini Flash `gemini-2.5-flash` é o provedor principal; Groq `openai/gpt-oss-120b` é a reserva.
- Um cliente do pacote `openai` usa `base_url` específico por provedor. Se o tool calling do Gemini for incompatível, somente Gemini migra para SDK nativo.
- Fallback somente para 429, timeout e 5xx; nunca por erro de execução de tool. Registrar o provedor que respondeu em cada mensagem.
- SQLite com `sqlite3` puro em um único arquivo, sem ORM.
- Preços em REAL; usar `round(x, 2)` e tolerância de 0.01.
- `installments` pode ser NULL para PIX, débito e boleto.
- Parcelamento segue §3.1: até 3x, parcela mínima R$ 50; 4x a 6x, R$ 80; 7x a 12x, R$ 100. `simular_parcelamento` centralizará as contas no código; não implementar sem solicitação do passo correspondente.
- `total_brl` é o valor oficial. Divergência marca `total_needs_review` e encaminha à equipe.
- A descrição original dos produtos nunca é enviada ao modelo; `specs` só usa chaves permitidas e nunca para produtos 135 a 144.
- Identificação do cliente por número do pedido e e-mail; `customer_id` verificado permanece na sessão.
- Disponibilidade: `active` com estoque maior que zero está disponível; `discontinued` saiu do catálogo; `active` sem estoque está sem estoque; `coming_soon` prevalece sobre estoque. Itens indisponíveis não aparecem em listas; se perguntado diretamente, explicar o motivo e sugerir alternativas válidas.
- Promoção exige registro para o produto com `is_active = 1`; apresentar preço original, percentual e preço final. PIX de 5% não acumula com promoção; em caso de mais de uma promoção ativa, prevalece o maior desconto.
- Histórico será resumido, mantendo mensagens recentes completas.
- Classificador: regras primeiro, LLM somente em caso de dúvida; uma mensagem pode receber vários rótulos. Categorias iniciais: `dado_loja`, `politica`, `acessorio`, `fora_assunto`, `saudacao`. `scikit-learn` fica para o Passo 18.
- Acessórios são redirecionados usando lista fixa de exemplo, sem alegar parceria real.
- Data/hora de referência via `REFERENCE_DATETIME`, fuso `America/Campo_Grande`, padrão `2026-03-23T10:00:00`; centralizar em `agora()` e `hoje()`.
- Se houver duas promoções ativas para o mesmo produto, prevalece o maior desconto; PIX não acumula com promoção.
- Contatos documentados: telefone `(67) 3341-4444`, WhatsApp `(67) 3321-4500`, e-mail `contato@emporiodamusica.com.br`. Não afirmar confirmação oficial.
- Interface inicial CLI; FastAPI é evolução futura.
- A CLI prevê `--conversa ID` e `--debug`; o núcleo do agente recebe texto e devolve texto sem depender da interface.
- Provedor, compatibilidade, contatos e lojas de exemplo devem ser descritos conforme `docs/DECISOES.md`; não inventar resultados ou confirmações.

## Itens que ainda exigem validação

- Categorias finais e ajustes do classificador após testes.
- Tool calling real nos dois endpoints e eventual compatibilidade do Gemini.
- Reconferência de limites, preços e cache dos provedores antes da entrega.
- Confirmação dos contatos com responsável e eventual substituição da lista exemplificativa por uma autorizada.
- Campos `[PREENCHER]` dependentes de resultados ou experiência do usuário.

## Regras de trabalho

- Execute somente o passo solicitado de `docs/PLANO_DE_PASSOS.md`; não antecipe outros passos.
- Escreva os testes primeiro, mostre-os e aguarde aprovação antes de implementar.
- Não considere um passo concluído sem testes pytest verdes.
- Não faça `git commit` ou `git push` sem autorização explícita.
- Não decida nem implemente alternativas que ainda dependem de validação.
- Escreva documentação em português e não invente resultados, métricas, conversas ou registros de uso de assistentes.
- Todo arquivo novo deve começar com docstring ou comentário explicando sua responsabilidade.
- Não use frameworks de agente (LangChain, LangGraph, LlamaIndex, PydanticAI, CrewAI ou AutoGen).
- Não implemente a tool `simular_parcelamento` antes do passo que a prevê.

## Checklist de tool

1. Argumentos validados com Pydantic.
2. Sem `SELECT *`; listar as colunas.
3. Usar `conn_leitura`.
4. Não devolver `description_raw`, telefone ou e-mail.
5. Não aceitar `customer_id` como argumento do modelo.
6. Usar `agora()` ou `hoje()` em vez de `date.today()`/`datetime.now()` fora de `config.py`.
7. Ter teste em `tests/`.
8. Erros retornam como resultado estruturado.
