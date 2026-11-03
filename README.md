<!-- Responsabilidade: documentação geral do projeto, instruções de execução e contexto do agente Empório da Música. -->

# Empório Agente

## Como rodar

### Ambiente

1. Crie um ambiente virtual em Python 3.11+.
2. Instale as dependências do projeto com `pip install -e .`.
3. Copie `.env.example` para `.env` e ajuste as variáveis de provedor e data de referência.
4. Execute o build do banco com `python scripts/build_db.py`.
5. Use a CLI com `python -m src.emporio_agent.cli --help`.

### Provedor e configuração

- `LLM_PROVIDER` define o provedor principal (Gemini por padrão).
- `LLM_FALLBACK` define o provedor de reserva (Groq).
- `GEMINI_API_KEY` e `GROQ_API_KEY` devem ser preenchidas no `.env`.
- `REFERENCE_DATE` pode ficar vazio para usar a data do sistema, ou pode ser definido manualmente, por exemplo `2026-03-23`.

## Decisões técnicas

### Framework/abordagem do agente

Escolhi function calling direto com o SDK, sem framework. O agente tem poucas tools e um loop pequeno, então LangChain, LangGraph e similares seriam abstração demais. Eu queria manter o controle total do fluxo: mensagem, classificação, chamada de tool, resposta e logging. Dados estruturados como produtos, preços, estoque, pedidos e promoções ficam em ferramentas com parâmetros fixos, o que evita text-to-SQL e reduz risco de consulta inadequada. As políticas ficam no system prompt para manter um prompt cacheável e previsível.

### Modelo e provedor

O modelo padrão é Gemini Flash e a reserva é Groq. O fallback só entra em erro de limite ou indisponibilidade, nunca em erro de tool. O provedor que respondeu fica registrado em cada mensagem para rastreabilidade. O cliente de LLM permanece configurável via `.env` e o projeto não incorpora SDK específico em código até a etapa de implementação real.

### Interface de interação

A interface é CLI porque o foco é o agente funcionando de forma simples e testável. O núcleo do agente não depende da interface, então FastAPI ou outra entrada seria uma troca da camada externa e não da lógica de negócio.

### Persistência do histórico

O SQLite fica em um único arquivo (`data/emporio.db`) e guarda tanto os dados da loja quanto as tabelas de conversas e logs do agente. O histórico e as tool calls ficam persistidos em tabelas separadas; a camada de escrita fica isolada em `memory.py`, enquanto as tools usam conexões somente leitura. Isso mantém a segurança e a clareza da execução.

### Tratamento dos dados

- `total_brl` é o valor oficial e o build calcula `total_needs_review` quando há divergência entre total e soma dos itens.
- `description_raw` fica no banco, mas não é devolvida por nenhuma tool.
- Disponibilidade e promoções obedecem a regras explícitas: `active` com estoque > 0 é válido; `discontinued` saiu do catálogo; `coming_soon` está em breve; indisponíveis não aparecem em lista, mas são explicados quando perguntados diretamente.
- Preços em REAL usam `round(x, 2)` e tolerância de 0.01, e a data de referência vem de `REFERENCE_DATE` ou do sistema.
- O `customer_id` verificado fica na sessão e nunca vem do modelo.

### Arquitetura de retrieval

O projeto parte do princípio de que o manual cabe no prompt com folga e que a recuperação por seção não precisa estar implementada no Passo 0. Em uma evolução futura, RAG com busca híbrida BM25 + embeddings seria a melhor etapa para aumentar escala e flexibilidade, sem trocar a política atual de prompt direto para a entrega inicial.

### Estratégia de prompt

A ordem do prompt é: tools → persona + manual → histórico → mensagem nova. Isso deixa no início o que não muda e preserva a regra de que o manual é interno e deve ser parafraseado, sem colar o texto do PDF. O cache do prompt reduz custo e repete a base fixa entre chamadas, enquanto o histórico complementa o contexto dinâmico da conversa.

## Problemas encontrados nos dados e suposições

- Produto 96 `active` com estoque 0; 136 `discontinued` com estoque 13; 130 `coming_soon` com estoque 2 e dois pedidos.
- Produtos 135 a 144 têm inconsistências entre nome, descrição e specs.
- `specs` é um JSON textual com chaves diferentes por categoria e o significado de alguns campos varia entre produtos.
- Categorias 6, 7 e 8 não têm produtos, embora o manual diga que a loja vende itens das categorias correspondentes.
- Promoções ativas existirem em poucos produtos e, sem datas de início/fim, devem ser tratadas como dados do catálogo e não como cronograma completo.
- Pedidos com total fora do comportamento esperado exigem a flag `total_needs_review` no build.
- Há pedidos em status `pending`, `confirmed` e `shipped` em janeiro, fevereiro e março de 2026, o que torna a data de referência relevante.
- `payment_type` vem como texto com modelos diferentes e parcelamento ambíguo no manual.
- O manual tem inconsistências de dados e linguagem, como telefone, e-mail e regras de parcelamento divergentes.

## Limitações conhecidas e o que faria com mais tempo

- Implementar RAG com busca híbrida, chunking por seção e fallback para política contextualizada.
- Melhorar o classificador de intenção com regras explícitas e conjunto de testes dedicados.
- Validar o modelo e o fallback com comparação real de custo/qualidade entre Gemini e Groq.
- Adicionar autenticação real para fluxo de cliente, como OTP ou login com WhatsApp.
- Expandir a gestão de histórico para resumir janela de contexto em conversas longas.
- Incluir FastAPI como interface alternativa, sem abandonar o núcleo do agente.

## Uso de assistentes de código

Ferramentas: editor de código, busca por texto, execução local de testes e revisão de arquivos. Como usei, por etapa: comecei pela estrutura do projeto e documentação, depois validei a coleta dos testes e mantive o escopo do Passo 0 focado no esqueleto, sem avançar para passos futuros. O que a IA errou e eu corrigi: em um primeiro rascunho, havia placeholders e configurações que não estavam alinhadas com o contexto decidido no prompt; eu os substituí pelas decisões do projeto e pela documentação pedida. O que não deleguei: a definição do escopo, a revisão das regras de negócio e a decisão de não implementar itens em aberto sem autorização.

O processo foi conduzido em passos pequenos, com critérios de aceite e testes (ver `docs/PLANO_DE_PASSOS.md`) e o registro está em `docs/USO_DE_IA.md`.

## Exemplos de interação

- `examples/01_catalogo_violoes.md`
- `examples/02_preco_takamine_gd20.md`
- `examples/03_devolucao.md`
- `examples/04_fora_de_escopo_acessorio.md`
- `examples/05_status_pedido.md`

Links: `examples/01_catalogo_violoes.md`, `examples/02_preco_takamine_gd20.md`, `examples/03_devolucao.md`, `examples/04_fora_de_escopo_acessorio.md`, `examples/05_status_pedido.md`.

---

**Abordagem.** Escolhi function calling direto com o SDK, sem framework. O agente tem poucas tools e um loop pequeno, então LangChain, LangGraph e similares seriam abstração demais, e eu queria poder explicar exatamente o que acontece em cada chamada. Dados estruturados (produtos, preços, estoque, pedidos, promoções) ficam em tools com parâmetros fixos, o que evita text-to-SQL e seus riscos. Políticas ficam no system prompt com prompt caching.

**Políticas no prompt.** O manual tem 3.498 tokens (medido com `tiktoken`), então cabe com folga. Prompt direto elimina o risco de recuperar o trecho errado, permite limpar as contradições do manual uma vez e me deu mais tempo para tools, testes e exemplos. Em escala, o caching reduz o custo reaproveitando o prefixo fixo. Limitações: o cache expira depois de alguns minutos, e o manual continua ocupando janela de contexto. Se o manual chegasse a 200 páginas ou mudasse com frequência, migraria para RAG.

**Modelo e provedor.** Gemini Flash como padrão e Groq como reserva. O fallback só entra em erro de limite ou indisponibilidade, e o provedor que respondeu é registrado em cada mensagem.

**Interface.** CLI, porque o foco é o agente funcionando. O núcleo não depende da interface, então FastAPI é só trocar a camada de entrada.

**Persistência.** SQLite em um único arquivo, `sqlite3` puro; histórico e logs ficam no mesmo lugar. Não usei ORM: o banco é recriado do CSV, a segurança depende de recursos do driver e são seis tabelas com consultas fixas.

**Tratamento dos dados.** `total_brl` como valor oficial com `total_needs_review`; descrição fora do prompt; regras de disponibilidade e promoção; `payment_type` separado em tipo e parcelas; preços em REAL com `round(x, 2)` e tolerância; data de referência configurável.

**Fora de escopo.** Duas camadas: regras no system prompt e um classificador de intenção isolado. A loja vende só instrumentos, então acessórios são redirecionados com educação.
