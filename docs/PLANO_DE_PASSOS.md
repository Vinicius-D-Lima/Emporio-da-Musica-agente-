<!-- Responsabilidade: registrar o plano de execução em passos do projeto Empório da Música. -->

# Plano de passos do projeto `emporio-agente`

## Passo 0 — Esqueleto, documentação e contexto do assistente

Critério de aceite:
- estrutura de diretórios criada;
- `README.md` e `CLAUDE.md` com contexto do projeto;
- `docs/` com arquitetura, decisões, uso de IA e plano de passos;
- `pyproject.toml` com dependências mínimas e marker `llm`;
- `src/emporio_agent` com módulos stubados e `schema.sql` completo;
- `tests/` com stubs e `@pytest.mark.skip(reason="Passo N")`;
- arquivo `.env.example` e `.gitignore` criados;
- `data/processed/politicas.md` com seções do manual;
- `examples/` com arquivos esboço.

## Passo 1 — Preparação dos dados e build do banco

Critério de aceite:
- `scripts/build_db.py` é idempotente;
- tabelas da loja são recriadas a partir dos CSVs;
- contagens e integridade referencial são validadas.

## Passo 2 — Segurança do banco e autorizações

Critério de aceite:
- `set_authorizer` bloqueia acessos indevidos;
- `customer_id` não entra como argumento de tools;
- leitura e escrita são separadas em conexões diferentes.

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

## Passo 6 — Segurança e remoção de vazamentos

Critério de aceite:
- telefone, e-mail e `description_raw` nunca são devolvidos;
- `SELECT *` não aparece no código;
- `date.today()` não existe fora do módulo de configuração.

## Passo 7 — LLM provider e fallback

Critério de aceite:
- `llm.py` encapsula o provedor selecionado;
- fallback ocorre apenas em falha de limite/indisponibilidade;
- logs do provedor ficam registrados.

## Passo 8 — Sistema de memória e histórico

Critério de aceite:
- `memory.py` salva mensagens e tool calls;
- conversas e mensagens ficam persistidas em SQLite;
- histórico pode ser recuperado sem expor dados sensíveis.

## Passo 9 — Prompts e persona

Critério de aceite:
- `prompts.py` organiza persona, regras, fora de escopo e formato de resposta;
- manual e regras seguem a ordem definida no prompt.

## Passo 10 — Classificador de intenção

Critério de aceite:
- `classificar_intencao(msg)` retorna categoria estável;
- acessórios e assuntos fora do escopo são detectados e redirecionados.

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
- `.env` e `config.py` carregam corretamente a data de referência;
- `hoje()` centraliza a leitura da data e evita uso direto em outros módulos.

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
