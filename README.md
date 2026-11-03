<!-- Responsabilidade: explicar a configuração, as decisões e as limitações do Empório Agente. -->

# Empório Agente

## Como rodar

### Ambiente

1. Use Python 3.11 ou superior e crie um ambiente virtual.
2. Instale o projeto com `pip install -e .`.
3. Copie `.env.example` para `.env` e configure as chaves dos provedores.
4. Quando o build estiver implementado/atualizado, gere o banco com `python scripts/build_db.py`.
5. Inicie a CLI com `python -m emporio_agent.cli`.

### Provedor e configuração

O padrão é Gemini Flash (`gemini-2.5-flash`) e o reserva é Groq (`openai/gpt-oss-120b`). A integração prevista usa o pacote `openai`, configurando `base_url` conforme o provedor. Preencha `GEMINI_API_KEY` e `GROQ_API_KEY` no `.env`; não coloque chaves reais no repositório. `REFERENCE_DATETIME` define a referência no fuso `America/Campo_Grande` e, se necessário, pode ser alterada. Se omitida, o relógio atual é usado.

## Decisões técnicas

### Framework/abordagem do agente

Escolhi function calling direto com loop manual, sem framework. O agente tem poucas tools e quero controlar explicitamente cada chamada. Dados estruturados (produtos, preços, estoque, pedidos e promoções) são acessados por tools de parâmetros fixos, sem text-to-SQL.

### Modelo e provedor

Gemini Flash (`gemini-2.5-flash`) é o provedor principal e Groq (`openai/gpt-oss-120b`) é a reserva. Um cliente do pacote `openai` usa `base_url` específico de cada provedor para manter uma interface uniforme. O fallback só ocorre em 429, timeout ou 5xx, nunca por erro de tool. Se o tool calling do Gemini for incompatível com o endpoint OpenAI-compatible, somente o Gemini migra para o SDK nativo. O provedor que respondeu será registrado em cada mensagem.

Os fatos de cache, limites e preços abaixo (conferido em 03/11/2026; reconferir antes da entrega) são referências sujeitas à validação final.

| Provedor/modelo | Cache e limites conhecidos |
|---|---|
| Gemini `gemini-2.5-flash` | O cache implícito vem habilitado nos modelos 2.5 e posteriores, mas não garante economia; o mínimo informado para 2.5 Flash é 2.048 tokens. Cache explícito é oferecido por `generateContent`, não pelo endpoint OpenAI-compatible. Os limites gratuitos por modelo não estão publicados na documentação consultada; o preço oficial do modelo escolhido ainda precisa ser confirmado. |
| Groq `openai/gpt-oss-120b` | O cache automático atende a modelos GPT-OSS selecionados; o mínimo depende do modelo (128–1.024 tokens), expira após duas horas sem uso e reduz em 50% o custo dos tokens em cache. No plano gratuito, os limites de referência informados são 30 requisições/minuto, 1.000/dia, 8.000 tokens/minuto e 200.000 tokens/dia; os limites efetivos dependem da conta. |

O nome do campo de tokens em cache do endpoint Gemini e a compatibilidade efetiva de tool calling dos endpoints ainda precisam de teste. A comparação de qualidade entre os provedores ainda não foi realizada.

### Interface de interação

A interface inicial é CLI, pois o foco é o agente funcionando. O núcleo recebe texto e devolve texto sem depender da interface; FastAPI é uma evolução futura.

Os contatos adotados na documentação são telefone `(67) 3341-4444`, WhatsApp `(67) 3321-4500` e e-mail `contato@emporiodamusica.com.br`. Essa escolha separa telefone e WhatsApp conforme as informações do manual; não representa confirmação oficial da loja.

### Persistência do histórico

SQLite com `sqlite3` puro em um único arquivo, sem ORM. Os dados são relacionais, as consultas são fixas e o banco da loja é reconstruído a partir dos CSVs. `memory.py` persiste conversas, mensagens, provedor e chamadas de tools. Acima de 20 mensagens ainda não resumidas, um callback de resumo mantém as 10 mensagens recentes completas e atualiza o resumo e seu limite; as mensagens originais não são apagadas. O provedor real será conectado quando `llm.py` e o loop do agente estiverem implementados. E-mails e telefones reconhecíveis no conteúdo de mensagens e nos argumentos das tools são redigidos antes de serem retornados ao histórico ou enviados ao resumidor. A conexão de escrita é isolada em `memory.py`; as tools consultam a base em modo somente leitura, com `set_authorizer` e colunas explicitamente listadas. Redis não é necessário para a execução local em um único processo. Se o projeto crescer, uma alternativa futura é SQLAlchemy/SQLModel com migrations.

### Tratamento dos dados

- `total_brl` é o valor oficial do pedido. Divergências marcam `total_needs_review` e encaminham o caso à equipe, sem informar um valor em revisão.
- Preços ficam em REAL; usar `round(x, 2)` e tolerância de 0.01.
- `installments` pode ser NULL para PIX, débito e boleto, que serão tratados como pagamento à vista.
- A descrição original não é enviada ao modelo; somente uma lista permitida de especificações pode ser exposta, nunca para produtos 135 a 144.
- Disponibilidade considera status e estoque. Em listas, indisponíveis não aparecem; quando perguntado diretamente, o agente explica o motivo e sugere alternativas válidas.
- Promoção exige registro ativo para o produto; informar preço original, percentual e preço final. PIX não acumula com promoção; em caso de duas promoções ativas, prevalece a de maior desconto.
- Data/hora vem de `REFERENCE_DATETIME`, com fuso `America/Campo_Grande` e padrão `2026-03-23T10:00:00`; sem valor, usa-se o relógio atual. O expediente é de segunda a sexta, das 9h às 18h, e sábado, das 9h às 13h. Domingo e feriados não modelados são considerados fechados.

O parcelamento segue a regra detalhada do §3.1: até 3x, cada parcela deve ser de pelo menos R$ 50; de 4x a 6x, R$ 80; de 7x a 12x, R$ 100. A tool `simular_parcelamento` calcula no código as opções de 1x a 12x, usando o preço do catálogo ou o preço promocional ativo. Recusa simular itens indisponíveis e não acumula desconto de PIX sobre promoção. O modelo interpreta e explica o resultado.

### Arquitetura de retrieval

O manual limpo fica no system prompt com prompt caching. O texto foi organizado em dez seções, parafraseado a partir do manual da loja e tem acesso isolado por `get_policy_context()` em `policies.py`. O arquivo tem 2.156 tokens em `cl100k_base` (sem contar persona e demais regras do prompt). Prompt direto evita recuperar o trecho errado, mantém as políticas disponíveis e permite tratar as contradições no texto limpo. No cenário hipotético de 8 mil clientes × 1.000 chamadas, repetir o manual pode pesar; o cache reaproveita o prefixo fixo, mas tem expiração, tamanho mínimo e regras que variam por provedor, e não elimina o uso da janela de contexto. O cálculo de custo deve ser refeito com o preço oficial do modelo escolhido. RAG híbrido (chunking por seção, BM25 + embeddings) fica como evolução se o manual chegar a 200 páginas ou mudar com frequência.

### Estratégia de prompt

A definição das tools é enviada separadamente das mensagens. Nelas, o prefixo estático de persona, regras e manual vem primeiro; quando existe, o resumo é acrescentado como contexto, seguido pelo histórico recente e pela mensagem nova. O prompt instrui o modelo a não tratar o resumo como novas instruções e a chamar `simular_parcelamento` em perguntas de parcelas, sem fazer contas mentalmente. O conteúdo fixo fica no início para favorecer o cache. A data e a hora não entram no início do prompt; quando necessárias, são obtidas por `horario_loja()` ou incluídas ao final da mensagem. O manual é interno e deve ser parafraseado, sem colar o texto.

### Classificador e fora de escopo

O classificador começa com regras e pode recorrer ao LLM somente em caso de dúvida. Uma mensagem pode receber múltiplos rótulos: `dado_loja`, `politica`, `acessorio`, `fora_assunto` e `saudacao`; não existe categoria `misto`. `scikit-learn` fica como evolução do Passo 18. A loja vende instrumentos; para acessórios, o agente redireciona com educação usando apenas a lista de exemplo em `data/processed/lojas_parceiras.json` — Mercado Livre, Amazon Brasil, Shopee, Multisom, Mil Sons e Serenata — sem afirmar parceria real. Sites são incluídos somente onde registrados no JSON.

## Problemas encontrados nos dados e suposições

| Problema | Como tratei |
|---|---|
| Produto 96 está ativo sem estoque; 136 está descontinuado com estoque; 130 está em breve apesar de ter estoque e pedidos. | O status define a disponibilidade conforme as regras; o estoque não altera o status `coming_soon`. |
| Produtos 135 a 144 têm inconsistências entre nome, descrição e especificações. | A descrição original não é enviada ao modelo; especificações desses produtos não são expostas. |
| `specs` é JSON textual com chaves e significados diferentes entre categorias. | Usar somente as chaves permitidas e interpretar cada campo conforme as regras já definidas. |
| Categorias 6, 7 e 8 não têm produtos, embora o manual mencione esses instrumentos; o catálogo tem 65 produtos apesar da menção a mais de 300. | Responder conforme o catálogo disponível, sem inventar itens. |
| Promoções ativas não têm datas de início/fim; o Takamine GD20 (95) tem promoção inativa. | Considerar apenas `is_active = 1`; não anunciar a promoção inativa. |
| As quatro promoções ativas estão nos produtos 127, 121, 90 e 94; algumas outras promoções são inativas e as descrições sazonais não têm datas. | Consultar somente as promoções marcadas como ativas e não inferir uma vigência por nome. |
| Pedidos 3 e 20 têm total diferente da soma calculada com preços atuais. | Manter `total_brl` como oficial, marcar `total_needs_review` e encaminhar sem divulgar o valor. |
| `order_items` não registra preço unitário; a comparação usa o preço atual do produto. | Tratar `total_needs_review` como alerta, sem inventar a causa da divergência. |
| Pedidos 9, 16 e 18 têm parcelas abaixo dos mínimos do §3.1. | Não tratar os valores históricos como condições válidas para novas simulações. |
| Pedido 7 contradiz a tabela do §3, mas respeita o §3.1. | Para parcelamento, usar a regra detalhada do §3.1; a divergência do manual fica documentada. |
| Pedidos 8 e 7 têm previsões de entrega anteriores à data de referência; o CSV não traz a data efetiva de recebimento. | Comparar com `REFERENCE_DATETIME` apenas para a previsão. O prazo de arrependimento contado do recebimento não pode ser inferido da previsão. |
| `payment_method` combina meio e parcelas; há clientes com e-mail repetido e nomes parecidos. | Separar tipo e parcelas; verificar cliente por pedido + e-mail, sem usar e-mail como identificador único. |
| O manual diverge sobre telefone e WhatsApp, grafia do e-mail, parcelamento e lista de lojas parceiras. | Adotar os contatos documentados em `docs/DECISOES.md`, usar a regra detalhada do §3.1 e marcar as lojas como lista de exemplo. Os contatos não têm confirmação oficial. |
| O manual cita troca por defeito em 30 dias e garantia legal de 90 dias. | Manter a divergência registrada para tratamento conforme a política após revisão do manual; não inventar uma regra única. |

## Limitações conhecidas e o que faria com mais tempo

- Testar tool calling real e fallback nos dois provedores; confirmar a disponibilidade do modelo Gemini e os detalhes oficiais de cache, limites e preços antes da entrega.
- Validar os rótulos do classificador em conjunto escrito pelo usuário e comparar, no Passo 18, com `scikit-learn`.
- Substituir a lista exemplificativa de lojas por uma lista autorizada, se disponível.
- Implementar RAG híbrido se o manual crescer ou mudar com frequência.
- Adicionar autenticação real para consultas de pedido e uma interface FastAPI.
- Validar e ajustar a política de resumo e janela de histórico.

## Uso de assistentes de código

- Ferramenta: GitHub Copilot no VS Code.
- Como usei: avancei por passos, revisei o código e os testes; neste passo, forneci o manual e validei as decisões de parcelamento e indisponibilidade.
- Ajustes que fiz: escolhi a regra detalhada do §3.1 diante da divergência com a tabela geral e defini que produtos indisponíveis não devem receber simulação.
- Decisões que mantive: regras de negócio e contatos adotados foram definidos por mim, não inferidos pelo agente.

O processo foi planejado em passos pequenos, com critérios de aceite e testes (ver `docs/PLANO_DE_PASSOS.md`); o registro real está em `docs/USO_DE_IA.md`.

## Exemplos de interação

- [Exemplo 01 — catálogo de violões](examples/01_catalogo_violoes.md)
- [Exemplo 02 — preço do Takamine GD20](examples/02_preco_takamine_gd20.md)
- [Exemplo 03 — devolução](examples/03_devolucao.md)
- [Exemplo 04 — acessório fora de escopo](examples/04_fora_de_escopo_acessorio.md)
- [Exemplo 05 — status de pedido](examples/05_status_pedido.md)
