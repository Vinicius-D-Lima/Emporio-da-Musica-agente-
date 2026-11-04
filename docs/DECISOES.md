<!-- Responsabilidade: registrar as decisões consolidadas do projeto e os itens que ainda precisam de validação. -->

# Decisões do projeto

As decisões registradas pelo usuário e os motivos informados durante as conversas ficam em [DECISOES_DO_USUARIO.md](./DECISOES_DO_USUARIO.md). Este documento consolida as decisões técnicas e as validações ainda pendentes; o diagnóstico detalhado dos dados e das divergências do manual fica no [README.md](../README.md).

## Decididas

| Decisão | Motivo |
|---|---|
| Function calling direto, loop manual e sem framework. | O projeto tem poucas tools e exige controle explícito das chamadas. |
| Dados estruturados acessados por tools de parâmetros fixos, sem text-to-SQL. | Evita consultas geradas livremente pelo modelo. |
| Manual parafraseado no system prompt; RAG fica como evolução futura. | Mantém as políticas disponíveis no contexto. O prefixo estático pode favorecer recursos de cache do provedor, sem garantir que o cache seja usado. |
| Gemini `gemini-3.5-flash-lite` como principal e Groq `openai/gpt-oss-120b` como reserva. | O modelo Gemini foi atualizado após o 404 do anterior, conforme a documentação consultada na ocasião. |
| Um cliente do pacote `openai`, com `base_url` específico por provedor. | Mantém uma interface de comunicação uniforme. |
| Se o tool calling do Gemini for incompatível com o endpoint OpenAI-compatible, somente o Gemini migra para o SDK nativo. | Isola a adaptação ao provedor que apresentar incompatibilidade. |
| O provedor que respondeu é registrado em cada mensagem. | Permite identificar qual provedor atendeu cada chamada. |
| SQLite com `sqlite3` puro, um arquivo e sem ORM. | Mantém simples uma base pequena com consultas controladas. |
| Preços em REAL, arredondamento com `round(x, 2)` e tolerância de 0.01. | Padroniza os cálculos e comparações de valores. |
| `installments` aceita NULL para PIX, débito e boleto. | Parcelas não se aplicam a esses meios de pagamento; a resposta indicará pagamento à vista. |
| Parcelamento segue o §3.1: até 3x, parcela mínima de R$ 50; de 4x a 6x, R$ 80; de 7x a 12x, R$ 100. | Foi escolhida a regra detalhada do §3.1 diante da divergência com a tabela geral do §3. |
| A tool `simular_parcelamento` centraliza os cálculos no código. | Evita erros matemáticos, condições inventadas e consumo de tokens com contas. |
| A simulação aceita um produto ou um valor explícito, nunca ambos; itens indisponíveis não são parcelados. | Mantém a origem do preço inequívoca e evita cotar produtos sem disponibilidade para venda. |
| Resumir após mais de 20 mensagens não resumidas, preservando as 10 mais recentes; o resumo é gerado por callback injetável e atualizado somente após sucesso. | Mantém contexto recente, limita o tamanho do histórico e preserva todas as mensagens se o provedor falhar. |
| Redigir e-mails e telefones nos argumentos de chamadas de tools e textos de mensagens antes de retorná-los ao histórico ou ao resumidor. | Reduz a exposição e a retenção desnecessária de dados pessoais no contexto do agente. |
| Manter o prompt estático de persona/regras/manual antes do resumo e do histórico; inserir o resumo como contexto delimitado e não como novas instruções. | Preserva a ordem definida, facilita o reaproveitamento do prefixo estático e reduz o risco de instruções citadas no resumo alterarem as regras do agente. |
| O loop principal aceita modelo injetável e, por padrão, usa `llm.py` para chamar Gemini/Groq; schemas de tools são validados com Pydantic. | Permite testes sem rede e mantém o acoplamento com provedores separado do agente. |
| Se o endpoint compatível com OpenAI do Gemini rejeitar explicitamente function calling, a chamada Gemini é adaptada ao SDK nativo; fallback para Groq ocorre em 404, 429, timeout e 5xx, mas não em 400/401. | Preserva o fluxo de tools e limita fallback a indisponibilidade ou falhas transitórias. |
| Limitar a cinco rodadas de tool calling, permitir uma chamada final sem tools e usar resposta segura se o modelo persistir em chamar ferramenta ou não produzir texto. | Limita consumo e ciclos, mantendo oportunidade de uma resposta natural sem ultrapassar o teto de execução de tools. |
| Erros conhecidos de ferramentas são devolvidos ao modelo como estrutura segura e registrados como falha; detalhes internos e valores sensíveis não são enviados. | Permite tentativa de recuperação sem expor argumentos ou detalhes operacionais. |
| `total_brl` é o valor oficial; divergências marcam `total_needs_review` e encaminham o caso à equipe. | O total do pedido não deve ser substituído por uma estimativa com preço atual. |
| A descrição original do produto nunca é enviada ao modelo. | Há inconsistências entre descrições, nomes e especificações dos dados. |
| Cliente é identificado por número do pedido e e-mail; `customer_id` verificado fica na sessão. | A identidade não deve vir como argumento do modelo. |
| O classificador usa regras primeiro e chama callback LLM opcional apenas quando nenhuma regra reconhece a mensagem; sem callback retorna lista vazia. Pode retornar múltiplos rótulos da taxonomia `dado_loja`, `politica`, `acessorio`, `fora_assunto` e `saudacao`; acessórios também recebem `fora_assunto`. | Mantém classificação previsível, permite integração posterior sem acoplar o módulo e combina intenções sem criar `misto`. |
| CLI interativa com uma mensagem por linha, retomada por `--conversa ID` e logs ativados por `--debug`; `/sair`, EOF ou Ctrl+C encerra a sessão. | A interação por terminal mantém o fluxo simples e a compatibilidade com terminais comuns. |
| `scikit-learn` fica como evolução do Passo 18. | A comparação será feita depois, no mesmo conjunto de teste. |
| Acessórios são redirecionados usando uma lista fixa de lojas de exemplo, sem alegar parceria real. | O manual não fornece uma lista autorizada de estabelecimentos. |
| Data e hora usam `REFERENCE_DATETIME`, no fuso `America/Campo_Grande`; `.env.example` contém `2026-03-23T10:00:00` para reprodução local. | Sem valor configurado, o código usa o relógio atual; a data de exemplo não é o padrão automático do código. |
| Havendo duas promoções ativas no mesmo produto, prevalece a de maior desconto. | Evita acumular descontos e define um resultado determinístico. |
| `promocoes_ativas` aceita `product_id` ou nome/modelo; consultas ambíguas retornam candidatos sem preços e exigem esclarecimento. | Permite uma consulta mais natural sem fazer o agente escolher silenciosamente entre produtos semelhantes. |
| Telefone `(67) 3341-4444`, WhatsApp `(67) 3321-4500` e e-mail `contato@emporiodamusica.com.br`. | A opção B separa os canais conforme a divergência do manual; o domínio do e-mail é usado sem acento. São dados adotados para o protótipo, não confirmados pela loja. |
| GitHub Copilot é a ferramenta de desenvolvimento. | É a ferramenta escolhida para trabalhar com instruções, agentes, subagentes e skills. |

## Em aberto

- Validar com chamadas reais o function calling e o fallback dos provedores; os testes automatizados usam clientes simulados.
- Confirmar, em fontes oficiais e na conta usada, disponibilidade, preços, limites e cache antes de qualquer uso real; esses dados são variáveis e não ficam fixados aqui.
- Confirmar os contatos e substituir a lista exemplificativa por uma lista autorizada se o protótipo passar a representar uma loja real.
- Os testes adversários que chamam LLM são opt-in; resultados reais ainda precisam ser avaliados e podem ser inconclusivos por limites dos provedores.
- O classificador em `intent.py` é independente e não está conectado ao fluxo do agente; `scikit-learn` permanece opcional no Passo 18.
- `orders.notes` é devolvido como motivo de cancelamento. O conjunto atual contém motivos operacionais; antes de enviar dados reais nessa coluna ao modelo, é necessário filtrar possíveis dados pessoais.
- O README documenta os roteiros de exemplo que ainda têm `[PREENCHER]`; completar 3–5 conversas representativas continua pendente.
