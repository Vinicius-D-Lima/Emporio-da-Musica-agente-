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

## Passo 3 — Configuração e horário da loja

- [x] `carregar_configuracao()` carrega provedor, fallback e chaves do ambiente, e informa com erro claro se uma chave necessária estiver ausente;
- [x] `agora()` usa `REFERENCE_DATETIME` ou o relógio do sistema, sempre em `America/Campo_Grande`; `hoje()` deriva a data de `agora()`;
- [x] referência temporal inválida falha com mensagem clara; `.env.example` define `2026-03-23T10:00:00`;
- [x] `loja_aberta(agora)` aplica segunda a sexta 09:00–18:00, sábado 09:00–13:00 e domingo fechado; feriados não são modelados;
- [x] `date.today()` e `datetime.now()` só são usados em `config.py`;
- [x] os testes de configuração cobrem carregamento, fusos, validação e limites do expediente.

## Passo 4 — Schemas e tools de produto

- [x] argumentos de busca e detalhes são validados com Pydantic, incluindo `preco_max > 0`;
- [x] consultas listam explicitamente as colunas e nunca leem ou retornam `description_raw`;
- [x] specs retornadas limitam-se a cordas, eletrônica, escala e cor, e são omitidas para produtos 135 a 144;
- [x] busca de violões até R$ 1.000 retorna os 12 disponíveis e exclui os produtos 96 e 113;
- [x] busca por `gd20`, `GD-20` e `takamine gd20` encontra o produto 95;
- [x] detalhes informam corretamente indisponibilidade, saída do catálogo, produto em breve e descontinuação;
- [x] busca sem resultados retorna resposta estruturada;
- [x] resultados são limitados sem perder o total real encontrado;
- [x] `tests/test_tools.py` valida os critérios de produto acima.

Commit sugerido: `feat(tools): busca e detalhes de produtos`

## Passo 5 — Promoções e preço final

- [x] somente promoções com `is_active = 1` e produto existente são consideradas;
- [x] os preços promocionais são arredondados para duas casas e usam o maior desconto sem acumular;
- [x] sem promoção, o produto 95 mantém o preço de R$ 2.199,00 e tem PIX de R$ 2.089,05;
- [x] com promoção, o valor PIX não recebe desconto adicional;
- [x] promoções inativas não aparecem, incluindo as do produto 96;
- [x] o relatório do `build_db` identifica produtos com múltiplas promoções ativas;
- [x] `tests/test_tools.py` valida preços reais e o caso sintético de promoções duplicadas.

Commit sugerido: `feat(tools): promoções e cálculo de preço final`

## Passo 6 — Pedidos e identidade

- [x] `verificar_cliente` compara e-mail sem diferenciar caixa e espaços, e registra `customer_id` somente na conversa;
- [x] pedido inexistente e e-mail incorreto retornam a mesma resposta;
- [x] tentativas inválidas são persistidas por conversa e bloqueadas após três tentativas;
- [x] `status_pedido` recebe o `conversa_id` como contexto interno, não aceita `customer_id` do modelo e restringe pedidos ao cliente verificado;
- [x] respostas incluem status, data, itens, pagamento, rastreio e previsão, sem telefone ou e-mail;
- [x] pedidos 3 e 20 ocultam o valor quando `total_needs_review` está ativo;
- [x] atraso do pedido 8 é calculado com `hoje()` e `REFERENCE_DATETIME`;
- [x] cancelamentos informam o motivo; pedidos pendentes/confirmados sem rastreio informam que ainda não foram despachados;
- [x] `tests/test_security.py` cobre verificação, limite por conversa, autorização e privacidade.

Commit sugerido: `feat(tools): verificação de cliente e status de pedido`

## Passo 7 — LLM provider e fallback

Critério de aceite:
- `llm.py` encapsula o provedor selecionado;
- Gemini Flash usa `gemini-2.5-flash`; Groq usa `openai/gpt-oss-120b`;
- cliente único do pacote `openai` usa `base_url` por provedor;
- se o tool calling do Gemini for incompatível, somente Gemini migra ao SDK nativo;
- fallback ocorre apenas em 429, timeout ou 5xx;
- logs do provedor ficam registrados.

## Passo 8 — Sistema de memória e histórico

- [x] `memory.py` cria conversas e persiste mensagens, provedor e chamadas de tools no SQLite;
- [x] recuperação é isolada pelo identificador da conversa e não retorna argumentos de tools; e-mail/telefone reconhecíveis nas mensagens e nos argumentos são redigidos;
- [x] acima de 20 mensagens ainda não resumidas, produz resumo por callback injetável, mantém as 10 mensagens recentes completas e registra `summary` e `summarized_until_message_id`;
- [x] falha do resumidor preserva todas as mensagens originais; resumos sucessivos incorporam o resumo anterior.

A integração do callback com o provedor real depende da implementação de `llm.py` e do loop em `agent.py`, previstos em passos próprios. As mensagens originais não são apagadas.

Commit sugerido: `feat(memory): persistência e resumo do histórico`

## Passo 9 — Prompts e persona

- [x] `prompts.py` organiza persona, regras de negócio, fora de escopo e formato esperado;
- [x] ferramentas são mantidas separadas das mensagens; o prefixo estático de persona e manual vem antes do resumo, do histórico e da mensagem atual;
- [x] o resumo é apresentado como contexto, não como instruções; histórico recente e mensagem atual preservam sua ordem;
- [x] perguntas sobre parcelamento instruem o modelo a chamar `simular_parcelamento`, sem calcular parcelas de cabeça.

Commit sugerido: `feat(prompts): persona e contexto do agente`

## Passo 10 — Classificador de intenção

- [x] `classificar_intencao(msg)` retorna uma lista determinística com zero ou mais rótulos;
- [x] taxonomia limitada a `dado_loja`, `politica`, `acessorio`, `fora_assunto` e `saudacao`; não cria `misto`;
- [x] regras são avaliadas primeiro; callback LLM opcional só é chamado quando nenhuma regra classifica, e sem callback retorna `[]`;
- [x] saudação pode coexistir com a intenção principal; pedido de acessório retorna `acessorio` e `fora_assunto`;
- [x] lista exemplificativa de lojas e orientação de redirecionamento permanecem na configuração/documentação e no prompt, sem afirmar parceria real.

Commit sugerido: `feat(intent): classificador multirrótulo por regras`

## Passo 11 — Agente loop principal

Critério de aceite:
- `agent.py` executa loop de mensagem → tools → resposta;
- ferramentas e erros de execução são tratados sem derrubar o processo.

## Passo 12 — CLI e interface

Critério de aceite:
- `cli.py` lê opções de conversa e debug;
- CLI chama o núcleo do agente e imprime resposta textualmente.

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
