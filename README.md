<!-- Responsabilidade: explicar a configuração, as decisões e as limitações do Empório Agente. -->

# Empório Agente

## Como rodar

### Ambiente

Use Python 3.11 ou superior. Execute os comandos abaixo na raiz do repositório
(a pasta que contém `README.md` e `pyproject.toml`). No Linux, `python3` cria o
ambiente virtual; depois de ativá-lo, `python` aponta para o Python do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cp -n .env.example .env
```

O `cp -n` cria `.env` sem substituir um arquivo que já exista. Edite `.env` e
preencha as chaves `GEMINI_API_KEY` e `GROQ_API_KEY` (ou deixe
`LLM_FALLBACK=` vazio para usar apenas um provedor). Em seguida, gere o banco e
inicie a CLI, ainda com o ambiente virtual ativado:

```bash
python scripts/build_db.py
python -m emporio_agent.cli
```

Digite uma mensagem por linha; use `/sair`, `Ctrl+D` ou `Ctrl+C` para encerrar.
A CLI mostra o ID da conversa, que pode ser retomada com
`python -m emporio_agent.cli --conversa ID`.
Use `python -m emporio_agent.cli --debug` para habilitar logs de depuração.
Esse modo registra apenas campos técnicos permitidos em falhas, sem registrar o
corpo da requisição; valores de mensagens, chaves e dados pessoais reconhecidos
são redigidos, e logs HTTP de terceiros são suprimidos.

### Testes e cenários

Com o ambiente virtual ativado, execute os testes automatizados locais (sem
chamadas a provedores reais):

```bash
python -m pytest
```

Os cenários adversários com LLM real estão em
[`tests/test_scenarios.py`](tests/test_scenarios.py) e são identificados de
`A01` a `A24`. Para executar somente um cenário, por exemplo o `A01`:

```bash
python -m pytest --run-llm -m llm tests/test_scenarios.py -k A01
```

Para executar todos os cenários com LLM real:

```bash
python -m pytest --run-llm -m llm tests/test_scenarios.py
```

Esses dois últimos comandos fazem chamadas externas, enviam as mensagens dos
cenários aos provedores configurados e podem consumir cota ou gerar custos.
Configure as chaves no `.env` e use dados de teste, não dados pessoais reais.
Ao abrir um terminal novo, entre novamente na pasta do projeto e ative o
ambiente com `source .venv/bin/activate`. Se aparecer `python: command not
found`, confira se o ambiente está ativado e se o comando foi executado na raiz
do repositório.

### Provedor e configuração

O padrão é Gemini `gemini-3.5-flash-lite` com Groq `openai/gpt-oss-120b`
como reserva. Configure `GEMINI_API_KEY` e `GROQ_API_KEY` em `.env`; como o
fallback está habilitado por padrão, as duas chaves são necessárias. Para usar
somente um provedor, deixe `LLM_FALLBACK` vazio. Os modelos podem ser alterados
por `GEMINI_MODEL` e `GROQ_MODEL`.

`REFERENCE_DATETIME` define a referência temporal no fuso
`America/Campo_Grande`. O `.env.example` inclui uma data fixa para reproduzir
cenários; se a variável estiver vazia ou ausente, o sistema usa o relógio atual.
Não coloque chaves reais no repositório.

O fallback ocorre em 404, 429, timeout ou erro 5xx; erros 400/401 e falhas de
execução de ferramentas não o acionam. Se o endpoint OpenAI-compatible do
Gemini rejeitar explicitamente function calling, essa chamada usa o SDK nativo
do Gemini. O provedor que respondeu é registrado no histórico. A assinatura
`thought_signature` do Gemini é mantida apenas em memória durante o ciclo de
function calling. O agente também aceita um modelo injetado para testes sem
requisições externas. Para manter uma conversa em chamadas diretas a
`responder_mensagem()`, crie uma conversa com `memory.criar_conversa()` e
reutilize o mesmo `conversa_id`.

Os testes de provedores usam clientes simulados. Chamadas reais enviam texto e
contexto ao serviço configurado; dados fornecidos para verificação de pedidos
também podem ser enviados. Antes de usar dados de clientes, avalie privacidade,
consentimento e retenção e faça uma chamada real controlada para verificar
credenciais e compatibilidade.

## Decisões técnicas

### Framework/abordagem do agente

Escolhi function calling direto com loop manual, sem framework. O agente tem poucas tools e quero controlar explicitamente cada chamada. Dados estruturados (produtos, preços, estoque, pedidos e promoções) são acessados por tools de parâmetros fixos, sem text-to-SQL.

### Modelo e provedor

Gemini `gemini-3.5-flash-lite` é o provedor principal escolhido para este
protótipo; Groq `openai/gpt-oss-120b` é a alternativa configurada. O cliente do
pacote `openai` usa um `base_url` específico para cada provedor, mantendo uma
interface comum. O fallback é limitado a falhas de disponibilidade e não se
aplica a erros de credenciais, requisições inválidas ou execução de tools.
Ainda não foi feita uma validação real de compatibilidade ponta a ponta. Preços,
limites, disponibilidade e comportamento de cache dependem do provedor, modelo
e conta; consulte as fontes oficiais antes de uso real, em vez de tratar valores
históricos como garantidos.

### Interface de interação

A interface inicial é CLI, pois o foco é o agente funcionando. O núcleo recebe texto e devolve texto sem depender da interface; FastAPI é uma evolução futura.

Os contatos adotados na documentação são telefone `(67) 3341-4444`, WhatsApp `(67) 3321-4500` e e-mail `contato@emporiodamusica.com.br`. Essa escolha separa telefone e WhatsApp conforme as informações do manual; não representa confirmação oficial da loja.

### Persistência do histórico

SQLite com `sqlite3` puro em um único arquivo, sem ORM. Os dados são relacionais, as consultas são fixas e o banco da loja é reconstruído a partir dos CSVs. `memory.py` persiste conversas, mensagens, provedor e chamadas de tools. Acima de 20 mensagens ainda não resumidas, um callback de resumo mantém as 10 mensagens recentes completas e atualiza o resumo e seu limite; as mensagens originais não são apagadas. O provedor configurado também é usado para resumir conversas. E-mails e telefones reconhecíveis no conteúdo de mensagens e nos argumentos das tools são redigidos antes de serem retornados ao histórico ou enviados ao resumidor. A conexão de escrita é isolada em `memory.py`; as tools consultam a base em modo somente leitura, com `set_authorizer` e colunas explicitamente listadas. Redis não é necessário para a execução local em um único processo. Se o projeto crescer, uma alternativa futura é SQLAlchemy/SQLModel com migrations.

### Tratamento dos dados

- `total_brl` é o valor oficial do pedido. Divergências marcam `total_needs_review` e encaminham o caso à equipe, sem informar um valor em revisão.
- Preços ficam em REAL; usar `round(x, 2)` e tolerância de 0.01.
- `installments` pode ser NULL para PIX, débito e boleto, que serão tratados como pagamento à vista.
- A descrição original não é enviada ao modelo; somente uma lista permitida de especificações pode ser exposta, nunca para produtos 135 a 144.
- Disponibilidade considera status e estoque. Em listas, indisponíveis não aparecem; quando perguntado diretamente, o agente explica o motivo e sugere alternativas válidas.
- Promoção exige registro ativo para o produto; informar preço original, percentual e preço final. PIX não acumula com promoção; em caso de duas promoções ativas, prevalece a de maior desconto.
- Data/hora vem de `REFERENCE_DATETIME`, no fuso `America/Campo_Grande`; o `.env.example` usa `2026-03-23T10:00:00` para reprodução local e, sem valor configurado, usa-se o relógio atual. O expediente descrito no manual é de segunda a sexta, das 9h às 18h, e sábado, das 9h às 13h. Domingo e feriados não modelados são considerados fechados.

O parcelamento segue a regra detalhada do §3.1: até 3x, cada parcela deve ser de pelo menos R$ 50; de 4x a 6x, R$ 80; de 7x a 12x, R$ 100. A tool `simular_parcelamento` calcula no código as opções de 1x a 12x, usando o preço do catálogo ou o preço promocional ativo. Recusa simular itens indisponíveis e não acumula desconto de PIX sobre promoção. O modelo interpreta e explica o resultado.

### Arquitetura de retrieval

O manual parafraseado é carregado integralmente no system prompt por
`get_policy_context()` em `policies.py`. Essa abordagem mantém as políticas
disponíveis sem uma etapa de retrieval que possa recuperar o trecho errado; não
foi implementado RAG. O prefixo estático também favorece eventuais recursos de
cache dos provedores, mas não garante cache nem reduz a janela de contexto
utilizada. Busca híbrida pode ser considerada se o manual crescer ou mudar com
frequência.

### Estratégia de prompt

A definição das tools é enviada separadamente das mensagens. O prefixo de
persona, regras e manual vem primeiro; quando existe, o resumo contextualizado é
seguido pelo histórico recente e pela mensagem atual. O prompt instrui o modelo
a não tratar o resumo como novas instruções e a chamar `simular_parcelamento`
em perguntas de parcelas. A data atual não é adicionada ao prompt: `agora()` e
`hoje()` são usadas no código onde os cálculos precisam de uma referência.
`loja_aberta()` é um helper interno, não uma tool disponível ao modelo. O manual
é interno e deve ser parafraseado.

### Classificador e fora de escopo

O classificador independente aplica regras primeiro e chama um callback LLM
opcional somente quando nenhuma regra reconhecer a mensagem. Pode retornar
múltiplos rótulos entre `dado_loja`, `politica`, `acessorio`, `fora_assunto` e
`saudacao`; pedidos de acessórios recebem também `fora_assunto`. Ele ainda não
está conectado ao fluxo de atendimento do agente; `scikit-learn` permanece uma
evolução opcional do Passo 18. Para acessórios, o prompt limita o
redirecionamento à lista exemplificativa de `data/processed/lojas_parceiras.json`
e não afirma parceria comercial.

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
- Uso: desenvolvimento iterativo por etapas, com implementação, análise de falhas e execução de testes locais. As decisões de produto e segurança são revisadas pelo usuário e registradas em `docs/DECISOES_DO_USUARIO.md`; o histórico do trabalho está em `docs/USO_DE_IA.md`.
- Os testes determinísticos usam modelos simulados. Testes com provedores reais são opt-in e não devem ser descritos como executados sem uma execução confirmada.

O processo foi planejado em passos pequenos, com critérios de aceite e testes (ver `docs/PLANO_DE_PASSOS.md`); o registro real está em `docs/USO_DE_IA.md`.

## Exemplos de interação

O desafio pede de 3 a 5 conversas, incluindo uma consulta de dados ou aplicação
de política. Os cinco arquivos numerados em `examples/` ainda são roteiros com
`[PREENCHER]`, não transcrições completas. O arquivo
[conversas compartilhadas](examples/conversas_compartilhadas.md) contém cinco
registros enviados pelo usuário, mas apenas o primeiro é uma conversa completa;
os demais são trechos e as respostas não foram validadas contra uma execução.
Assim, os exemplos do repositório ainda precisam ser revisados e completados
antes de serem considerados conformes ao entregável do desafio.
