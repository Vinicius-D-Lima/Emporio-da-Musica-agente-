<!-- Responsabilidade: registrar o contexto operacional do assistente e as regras de trabalho para esta entrega do projeto Empório da Música. -->

# Contexto do assistente

## Decisões já tomadas

- Abordagem: function calling direto, loop de tools escrito à mão.
- Dados estruturados via tools com parâmetros fixos, sem text-to-SQL.
- Tools: `buscar_produtos`, `detalhes_produto`, `promocoes_ativas`, `verificar_cliente`, `status_pedido`.
- Loop do agente: limite de iterações; erro de tool volta pro modelo como resultado estruturado; argumentos inválidos voltam como erro de validação.
- Políticas: manual limpo no system prompt, com prompt caching. Ordem do prompt: tools → persona + manual → histórico → mensagem nova.
- Modelos: Gemini Flash como padrão, Groq como reserva. Configurável em `.env` (`LLM_PROVIDER`, `LLM_FALLBACK`, chaves, `REFERENCE_DATE`).
- Fallback só em erro de limite/indisponibilidade; nunca em erro de tool.
- Interface: CLI com `--conversa ID` e `--debug`; o núcleo `agent.py` recebe texto e devolve texto, sem depender da interface.
- Banco: SQLite com `sqlite3` puro, único arquivo `data/emporio.db`.
- Preços em REAL. `round(x, 2)` em desconto/PIX e tolerância de 0.01.
- Pedido: `total_brl` é o valor oficial; o build calcula `total_needs_review` e, se marcado, a tool não retorna o valor.
- Descrição de produto não é confiável: `description_raw` fica no banco, mas nenhuma tool devolve; `specs` apenas chaves permitidas.
- Disponibilidade: regras definidas para `active`, `discontinued`, `coming_soon` e indisponibilidade.
- Promoção: vale se `product_id` tiver `is_active = 1`; mostrar original, % e final; PIX 5% não acumula com promoção.
- Data: uma única função `hoje()` lê `REFERENCE_DATE` do `.env`.
- Identidade: cliente informa nº do pedido + e-mail; o `customer_id` verificado fica na sessão.
- Segurança em camadas: conexão `mode=ro` para ferramentas; escrita só em `memory.py`; `set_authorizer` bloqueando `products.description_raw`.
- Fora de escopo: regras no system prompt + classificador `classificar_intencao(msg)`.
- A loja vende só instrumentos; acessórios são redirecionados.
- Processo: um passo por vez, testes primeiro.

## Em aberto

- Janela de contexto: truncar vs resumir.
- Implementação do classificador (proposta: regras + LLM só na dúvida; scikit-learn e Jev como bônus).
- Acessórios: busca na web vs lista fixa de lojas parceiras.
- Contradições do manual.
- Valor padrão de `REFERENCE_DATE`.
- Duas promoções ativas no mesmo produto.
- Cliente de LLM: SDK compatível com OpenAI vs SDKs nativos de cada provedor.

## Regras de trabalho

- Um passo por vez e somente o que foi pedido.
- Testes primeiro.
- Não marcar passo como pronto sem `pytest` verde.
- Não rodar `git commit` nem `git push`.
- Não implementar nada de "Em aberto" sem decisão do usuário.
- Tudo em português.

## Checklist de tool

1. argumentos validados com Pydantic
2. sem `SELECT *`, colunas listadas
3. usa `conn_leitura`
4. não devolve `description_raw`, telefone nem e-mail
5. não aceita `customer_id` como argumento
6. usa `hoje()` em vez de `date.today()`
7. tem teste em `tests/`
8. erros voltam como resultado estruturado
