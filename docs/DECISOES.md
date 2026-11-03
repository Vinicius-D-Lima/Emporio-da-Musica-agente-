<!-- Responsabilidade: registrar as decisões consolidadas do projeto e os itens que ainda precisam de validação. -->

# Decisões do projeto

As decisões registradas pelo usuário e os motivos informados durante as conversas ficam em [DECISOES_DO_USUARIO.md](./DECISOES_DO_USUARIO.md). Este documento mantém as decisões técnicas consolidadas do projeto.

## Decididas

| Decisão | Motivo |
|---|---|
| Function calling direto, loop manual e sem framework. | O projeto tem poucas tools e exige controle explícito das chamadas. |
| Dados estruturados acessados por tools de parâmetros fixos, sem text-to-SQL. | Evita consultas geradas livremente pelo modelo. |
| Manual no system prompt com prompt caching; RAG fica como evolução futura. | O manual cabe no contexto e o prefixo fixo pode ser reutilizado. |
| Gemini Flash `gemini-2.5-flash` como principal e Groq `openai/gpt-oss-120b` como reserva. | Modelos escolhidos para a configuração inicial do projeto. |
| Um cliente do pacote `openai`, com `base_url` específico por provedor. | Mantém uma interface de comunicação uniforme. |
| Se o tool calling do Gemini for incompatível com o endpoint OpenAI-compatible, somente o Gemini migra para o SDK nativo. | Isola a adaptação ao provedor que apresentar incompatibilidade. |
| Fallback somente para 429, timeout e erros 5xx; erros de tools não acionam fallback. | Limita o fallback a indisponibilidade ou limite do provedor. |
| O provedor que respondeu é registrado em cada mensagem. | Permite identificar qual provedor atendeu cada chamada. |
| SQLite com `sqlite3` puro, um arquivo e sem ORM. | Mantém simples uma base pequena com consultas controladas. |
| Preços em REAL, arredondamento com `round(x, 2)` e tolerância de 0.01. | Padroniza os cálculos e comparações de valores. |
| `installments` aceita NULL para PIX, débito e boleto. | Parcelas não se aplicam a esses meios de pagamento; a resposta indicará pagamento à vista. |
| Parcelamento segue o §3.1: até 3x, parcela mínima de R$ 50; de 4x a 6x, R$ 80; de 7x a 12x, R$ 100. | A regra detalhada do manual foi escolhida para orientar os cálculos. |
| A tool `simular_parcelamento` centralizará os cálculos no código. | Evita erros matemáticos, condições inventadas e consumo de tokens com contas. |
| A simulação aceita um produto ou um valor explícito, nunca ambos; itens indisponíveis não são parcelados. | Mantém a origem do preço inequívoca e evita cotar produtos sem disponibilidade para venda. |
| Resumir após mais de 20 mensagens não resumidas, preservando as 10 mais recentes; o resumo é gerado por callback injetável e atualizado somente após sucesso. | Mantém contexto recente, limita o tamanho do histórico e preserva todas as mensagens se o provedor falhar. |
| Redigir e-mails e telefones nos argumentos de chamadas de tools e textos de mensagens antes de retorná-los ao histórico ou ao resumidor. | Reduz a exposição e a retenção desnecessária de dados pessoais no contexto do agente. |
| Manter o prompt estático de persona/regras/manual antes do resumo e do histórico; inserir o resumo como contexto delimitado e não como novas instruções. | Preserva a ordem definida, facilita o reaproveitamento do prefixo estático e reduz o risco de instruções citadas no resumo alterarem as regras do agente. |
| O loop principal usa uma função de modelo injetável, registra schemas de tools e valida chamadas com Pydantic; o provedor real permanece separado. | Permite testar function calling sem credenciais e manter o acoplamento com provedor no módulo LLM. |
| Limitar a cinco rodadas de tool calling, permitir uma chamada final sem tools e usar resposta segura se o modelo persistir em chamar ferramenta ou não produzir texto. | Limita consumo e ciclos, mantendo oportunidade de uma resposta natural sem ultrapassar o teto de execução de tools. |
| Erros conhecidos de ferramentas são devolvidos ao modelo como estrutura segura e registrados como falha; detalhes internos e valores sensíveis não são enviados. | Permite tentativa de recuperação sem expor argumentos ou detalhes operacionais. |
| `total_brl` é o valor oficial; divergências marcam `total_needs_review` e encaminham o caso à equipe. | O total do pedido não deve ser substituído por uma estimativa com preço atual. |
| A descrição original do produto nunca é enviada ao modelo. | Há inconsistências entre descrições, nomes e especificações dos dados. |
| Cliente é identificado por número do pedido e e-mail; `customer_id` verificado fica na sessão. | A identidade não deve vir como argumento do modelo. |
| O histórico será resumido, mantendo as mensagens recentes completas. | Preserva contexto relevante sem enviar toda a conversa indefinidamente. |
| O classificador começa com regras e chama callback LLM opcional apenas quando nenhuma regra reconhece a mensagem; sem callback retorna lista vazia. Pode retornar vários rótulos, e pedidos de acessórios recebem `acessorio` + `fora_assunto`. | Mantém classificação previsível, permite integração posterior do provedor sem acoplar o módulo e combina intenções sem criar `misto`. |
| As categorias iniciais são `dado_loja`, `politica`, `acessorio`, `fora_assunto` e `saudacao`. | São os rótulos iniciais definidos para o domínio. |
| `scikit-learn` fica como evolução do Passo 18. | A comparação será feita depois, no mesmo conjunto de teste. |
| Acessórios serão redirecionados usando uma lista fixa de lojas de exemplo, sem alegar parceria real. | O manual recomenda lojas, mas não fornece uma lista de parceiras. |
| Data e hora são configuráveis por `REFERENCE_DATETIME`, no fuso `America/Campo_Grande`; padrão `2026-03-23T10:00:00`. | Centraliza a referência temporal e permite reproduzir cenários. |
| Havendo duas promoções ativas no mesmo produto, prevalece a de maior desconto. | Evita acumular descontos e define um resultado determinístico. |
| Telefone `(67) 3341-4444`, WhatsApp `(67) 3321-4500` e e-mail `contato@emporiodamusica.com.br`. | A opção B separa os canais de telefone e WhatsApp conforme as informações encontradas no manual; o domínio do e-mail é usado sem acento. |
| GitHub Copilot é a ferramenta de desenvolvimento. | É a ferramenta escolhida para trabalhar com instruções, agentes, subagentes e skills. |

## Em aberto

- Validar as categorias finais e possíveis ajustes do classificador com o conjunto de teste.
- Testar o tool calling nos endpoints escolhidos; se o Gemini for incompatível, aplicar a migração decidida para o SDK nativo somente nesse provedor.
- Reconferir informações de cache, limites e preços dos provedores antes da entrega. Os limites gratuitos do Gemini não estão publicados na documentação consultada e o preço do modelo escolhido precisa de confirmação em fonte oficial.
- Confirmar os contatos com o responsável caso o projeto represente uma loja real; a decisão documental não é confirmação oficial.
- Substituir a lista de lojas de exemplo por uma lista autorizada, se vier a existir uma lista real de parceiras.
- `config.py` centraliza `REFERENCE_DATETIME`, `agora()`, `hoje()` e `loja_aberta()`; uma tool futura `horario_loja()` poderá apresentar esses dados ao cliente.
- Propagar os novos campos de resumo do `schema.sql` ao build do banco quando o passo correspondente for autorizado; esta atualização não alterou `scripts/build_db.py` nem recriou o banco.
- Preencher resultados de testes e registros pessoais de uso de assistentes nos locais `[PREENCHER]`.

## Problemas nos dados

| problema | como tratei |
|---|---|
| Produtos 135 a 144 têm inconsistências entre nomes, descrições e especificações. | A descrição original não será enviada ao modelo; os casos serão tratados conforme os campos permitidos. |
| Produto 96 está ativo sem estoque; 136 está descontinuado com estoque; 130 está em breve apesar de ter estoque e pedidos. | Aplicam-se as regras de disponibilidade por status e estoque definidas no projeto. |
| `specs` é JSON textual com chaves e significados diferentes entre categorias. | Serão expostas somente chaves permitidas e nunca para produtos 135 a 144. |
| Categorias 6, 7 e 8 não têm produtos, embora o manual mencione esses instrumentos. | A busca deve responder com base no catálogo, sem inventar disponibilidade. |
| Pedidos 3 e 20 têm totais diferentes da soma calculada com os preços atuais. | `total_brl` permanece oficial; o build marca `total_needs_review` conforme a comparação prevista. |
| Pedidos 9, 16 e 18 têm parcelas abaixo dos mínimos do §3.1. | A regra será registrada; os valores existentes não serão tratados como condições de parcelamento válidas. |
| Pedido 7 contraria o mínimo de R$ 100 da tabela do §3, mas respeita o §3.1. | Para simulação, foi escolhida a regra detalhada do §3.1; a divergência do manual fica registrada. |
| Há clientes distintos com o mesmo e-mail e nomes parecidos. | A verificação usa conjuntamente número do pedido e e-mail, sem expor dados de clientes. |
| `payment_method` combina meio e parcelas em valores como `credit_6x`. | O build separa `payment_type` e `installments`; meios à vista usam parcelas NULL. |

## Contradições do manual

| problema | como tratei |
|---|---|
| A tabela do §3 e o §3.1 divergem sobre parcela mínima; o pedido 7 exemplifica a diferença. | Para cálculo foi escolhida a regra detalhada do §3.1; a divergência não é apresentada como resolvida pelo próprio manual. |
| O manual associa `(67) 3341-4444` a telefone/WhatsApp e também informa `(67) 3321-4500`. | Foi adotada a opção B: `(67) 3341-4444` como telefone e `(67) 3321-4500` como WhatsApp, sem alegar confirmação oficial. |
| O domínio do e-mail aparece com e sem acento. | Foi adotado `contato@emporiodamusica.com.br`, sem acento, como decisão documental; confirmar com o responsável em uso real. |
| O manual menciona lojas parceiras, mas não fornece a lista. | O arquivo de lojas será explicitamente marcado como exemplo, sem afirmar parceria. |
