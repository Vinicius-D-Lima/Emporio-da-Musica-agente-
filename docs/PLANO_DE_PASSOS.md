<!-- Responsabilidade: registrar o plano de execução em passos do projeto Empório da Música. -->

# Plano de passos do projeto `emporio-agente`

## Decisões consolidadas para orientar os passos

- Provedor principal Gemini Flash (`gemini-2.5-flash`); reserva Groq (`openai/gpt-oss-120b`); cliente único `openai` com `base_url` por provedor. Se o tool calling do Gemini for incompatível, somente ele migra para o SDK nativo.
- Fallback somente para 429, timeout e 5xx, nunca para erro de tool; registrar o provedor que respondeu.
- Parcelamento segue o §3.1 e será calculado pela tool planejada `simular_parcelamento`, não pelo modelo.
- Classificador baseado primeiro em regras, com LLM em caso de dúvida e rótulos múltiplos: `dado_loja`, `politica`, `acessorio`, `fora_assunto`, `saudacao`. `scikit-learn` fica para o Passo 18.
- Acessórios serão redirecionados usando a lista exemplificativa em `data/processed/lojas_parceiras.json`, sem afirmar parceria real.
- Contatos documentados: telefone `(67) 3341-4444`, WhatsApp `(67) 3321-4500` e e-mail `contato@emporiodamusica.com.br`; não há confirmação oficial.
- Referência temporal: `REFERENCE_DATETIME=2026-03-23T10:00:00`, no fuso `America/Campo_Grande`; usar `agora()`/`hoje()`.
- Histórico resumido com as mensagens recentes completas; duas promoções ativas do mesmo produto resolvem-se pelo maior desconto.

## Passo 0 — Esqueleto, documentação e contexto do assistente

Critério de aceite:
- estrutura de diretórios criada;
- `README.md` e instruções do GitHub Copilot em `.github/copilot-instructions.md`;
- agentes de revisão/adversário, skill de checklist e prompt reutilizável em `.github/`;
- `docs/` com arquitetura, decisões, uso de IA e plano de passos;
- `pyproject.toml` com dependências mínimas e marker `llm`;
- `src/emporio_agent` com módulos stubados e `schema.sql` completo;
- `tests/` com stubs e `@pytest.mark.skip(reason="Passo N")`;
- arquivo `.env.example` com configuração de provedores e `REFERENCE_DATETIME`, e `.gitignore` criados;
- `data/processed/politicas.md` com seções do manual;
- `examples/` com arquivos esboço.

## Passo 1 — Preparação dos dados e build do banco

Critério de aceite:
- `scripts/build_db.py` é idempotente;
- tabelas da loja são recriadas a partir dos CSVs e `data/emporio.db` é gerado;
- contagens: categories 9, customers 50, orders 20, order_items 22, products 65, promotions 25;
- rodar duas vezes mantém as contagens e não apaga as tabelas nem os registros de conversa;
- `PRAGMA foreign_key_check` retorna vazio;
- `payment_method` é separado: `credit_6x` vira `payment_type=credit` e `installments=6`; PIX, débito e boleto ficam com parcelas NULL;
- `total_needs_review = 1` nos pedidos 3 e 20 e 0 nos demais, comparando com tolerância de 0.01;
- `description_raw` é guardada e `specs_json` contém JSON válido em todas as linhas;
- datas são armazenadas como texto ISO;
- `conversations` inclui `summary` e `summarized_until_message_id`;
- o build imprime anomalias para os produtos 96, 136 e 130 e informa produtos com múltiplas promoções ativas;
- `tests/test_data.py` valida os itens acima.

## Passo 2 — Conexões e segurança do banco

- [x] `conn_leitura()` abre o banco com `mode=ro` e bloqueia INSERT, UPDATE e DELETE;
- [x] `conn_escrita()` é importada somente por `memory.py`;
- [x] o authorizer bloqueia a leitura de `products.description_raw` e `customers.phone`;
- [x] `customers.email` continua legível para verificação de identidade;
- [x] `PRAGMA foreign_keys = ON` é habilitado nas conexões de leitura e escrita;
- [x] `tests/test_security.py` cobre os critérios acima.

Commit sugerido: `feat(db): conexões leitura/escrita e authorizer`

## Passo 3 — Schemas e validações Pydantic

Critério de aceite:
- todos os argumentos das tools usam modelos Pydantic;
- erros de validação retornam resposta estruturada; 
- argumentos inválidos não quebram o agente.

## Passo 4 — Tools de catálogo e detalhes

Critério de aceite:
- `buscar_produtos` e `detalhes_produto` consultam `products` com filtros válidos;
- campos sensíveis não são expostos;
- resultados obedecem a regras de disponibilidade e promoção.

## Passo 5 — Tools de promoção e pedido

Critério de aceite:
- `promocoes_ativas` lista promoções elegíveis;
- `verificar_cliente` valida pedido + e-mail;
- `status_pedido` consulta status e total_brl apenas para cliente correto.
- A regra de duas promoções ativas para o mesmo produto escolhe a de maior desconto.
- O parcelamento será centralizado na tool planejada `simular_parcelamento`, seguindo §3.1; não deixar o LLM calcular valores.

## Passo 6 — Segurança e remoção de vazamentos

Critério de aceite:
- telefone, e-mail e `description_raw` nunca são devolvidos;
- `SELECT *` não aparece no código;
- `date.today()` não existe fora do módulo de configuração.

## Passo 7 — LLM provider e fallback

Critério de aceite:
- `llm.py` encapsula o provedor selecionado;
- Gemini Flash usa `gemini-2.5-flash`; Groq usa `openai/gpt-oss-120b`;
- cliente único do pacote `openai` usa `base_url` por provedor;
- se o tool calling do Gemini for incompatível, somente Gemini migra ao SDK nativo;
- fallback ocorre apenas em 429, timeout ou 5xx;
- logs do provedor ficam registrados.

## Passo 8 — Sistema de memória e histórico

Critério de aceite:
- `memory.py` salva mensagens e tool calls;
- conversas e mensagens ficam persistidas em SQLite;
- histórico pode ser recuperado sem expor dados sensíveis;
- conversas longas são resumidas, mantendo as mensagens recentes completas, com `summary` e `summarized_until_message_id`.

## Passo 9 — Prompts e persona

Critério de aceite:
- `prompts.py` organiza persona, regras, fora de escopo e formato de resposta;
- manual e regras seguem a ordem tools → persona + manual → resumo e histórico → mensagem nova;
- a tool `simular_parcelamento` deve ser usada em perguntas sobre parcelamento; o modelo não calcula parcelas de cabeça.

## Passo 10 — Classificador de intenção

Critério de aceite:
- `classificar_intencao(msg)` retorna uma lista com zero ou mais rótulos;
- rótulos iniciais: `dado_loja`, `politica`, `acessorio`, `fora_assunto`, `saudacao`; não criar `misto`;
- regras são a primeira tentativa; LLM só é usado em caso de dúvida;
- acessórios e assuntos fora do escopo são detectados e redirecionados;
- acessórios citam somente nomes da lista de exemplo, sem alegar parceria real.

## Passo 11 — Agente loop principal

Critério de aceite:
- `agent.py` executa loop de mensagem → tools → resposta;
- ferramentas e erros de execução são tratados sem derrubar o processo.

## Passo 12 — CLI e interface

Critério de aceite:
- `cli.py` lê opções de conversa e debug;
- CLI chama o núcleo do agente e imprime resposta textualmente.

## Passo 13 — Configuração de ambiente e data

Critério de aceite:
- `.env` e `config.py` carregam `REFERENCE_DATETIME` no fuso `America/Campo_Grande`;
- `agora()` centraliza data e hora, e `hoje()` deriva a data de `agora()`;
- `horario_loja()` informa o horário de funcionamento usando a referência centralizada;
- horário previsto pelo manual §2: segunda a sexta 09:00–18:00, sábado 09:00–13:00, domingo fechado; feriados não são modelados.

## Passo 14 — Exemplos e documentação de uso

Critério de aceite:
- `examples/` traz cenários reais e objetivos de conversa;
- README explica como executar e consultar as respostas.

## Passo 15 — Testes de cenário com LLM

Critério de aceite:
- `tests/test_scenarios.py` cobre cenários de catálogo, pedido e fora de escopo;
- testes de LLM ficam marcados com `@pytest.mark.llm` e pulados por padrão.

## Passo 16 — Revisão final e conformidade

Critério de aceite:
- verificações de segurança, documentação e comportamento;
- projeto está pronto para a próxima etapa de implementação de regras reais.

## Passo 17 — Entrega e revisão

Critério de aceite:
- README, arquitetura e decisões finalizadas;
- repositório pronto para comitamentos incrementais do cliente.

## Passo 18 — Classificador com scikit-learn (posterior e opcional)

Critério de aceite:
- treinar e avaliar TF-IDF + regressão logística ou LinearSVC com frases escritas pelo usuário;
- comparar com regras + LLM no mesmo conjunto de teste, incluindo acerto, erros típicos e latência;
- registrar somente métricas realmente medidas;
- manter a interface multirrótulo de `classificar_intencao(msg)`.
