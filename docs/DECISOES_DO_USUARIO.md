<!-- Responsabilidade: registrar decisões confirmadas pelo usuário, seus motivos e os trade-offs considerados. -->

# Decisões do usuário

Este registro guarda decisões tomadas pelo usuário durante o projeto, especialmente as esclarecidas por meio da skill `grillme`. Ele complementa [DECISOES.md](./DECISOES.md), que reúne as decisões técnicas consolidadas.

As justificativas são atribuídas ao usuário somente quando foram expressas por ele. Quando a decisão foi delegada ou o motivo não ficou claro na conversa, isso é indicado explicitamente; recomendações do assistente não são apresentadas como motivos pessoais do usuário.

## Decisões registradas

### 2026-11-03 — Como conduzir questionamentos e registrar decisões

- **Decisão confirmada:** ao questionar uma decisão, apresentar opções, permitir que o usuário explique por que escolheu uma delas e continuar examinando a escolha se houver lacunas ou riscos relevantes. Incluir uma opção para pedir explicação das alternativas antes de escolher.
- **Motivo informado pelo usuário:** quer entender as opções, explicar o próprio raciocínio e ter oportunidade de rever uma escolha até estar seguro; também quer poder pedir explicações quando não entender as alternativas.
- **Alternativas e trade-offs discutidos:** o processo deve ser crítico, mas não pressionar o usuário a adotar a preferência do assistente. Após uma confirmação informada, encerra-se o questionamento daquela decisão.
- **Riscos ou pendências:** nenhuma pendência para a atualização da skill; a confirmação da decisão final deve continuar explícita.

### 2026-11-03 — Regra de parcelamento do manual

- **Decisão confirmada:** usar os mínimos detalhados na seção §3.1 do manual: 1x permitido; 2–3 parcelas com mínimo de R$ 50 por parcela; 4–6 com mínimo de R$ 80; 7–12 com mínimo de R$ 100.
- **Motivo informado pelo usuário:** seguir a regra detalhada por faixa da seção §3.1, mantendo registrada a divergência com a tabela geral da seção §3.
- **Alternativas e trade-offs discutidos:** a tabela geral apresenta R$ 100 como mínimo, enquanto a seção §3.1 discrimina faixas menores. A simulação segue a seção detalhada e não trata a divergência como resolvida pelo próprio manual.
- **Riscos ou pendências:** confirmar a regra com a loja antes de uso comercial real.

### 2026-11-03 — Produtos indisponíveis na simulação

- **Decisão confirmada:** não simular parcelamento de produto sem estoque, fora do catálogo, em breve ou descontinuado; retornar indisponibilidade estruturada.
- **Motivo informado pelo usuário:** não foi registrado um motivo próprio além da escolha dessa conduta.
- **Alternativas e trade-offs discutidos:** em vez de cotar um item indisponível, informar a situação. Isso impede simulações que possam sugerir ao cliente que o produto está disponível.
- **Riscos ou pendências:** a equipe pode decidir futuramente tratar encomendas ou pré-vendas com regras específicas.

### 2026-11-03 — Contatos da loja

- **Decisão confirmada:** adotar a opção B para separar o telefone da loja e o WhatsApp em números distintos, além de usar a grafia do e-mail sem acento.
- **Motivo informado pelo usuário:** resolver documentalmente a divergência entre os contatos que aparecem no manual, sem afirmar que os dados foram confirmados oficialmente pela loja.
- **Alternativas e trade-offs discutidos:** manter os números separados facilita indicar o canal adequado; a escolha documental pode não corresponder aos contatos atuais da loja.
- **Riscos ou pendências:** confirmar os dados com o responsável antes de uso real.

### 2026-11-03 — Resumo de conversas e integração com LLM

- **Decisão confirmada:** a memória deve permitir que um LLM produza o resumo, mas a integração será feita por callback injetável enquanto o provedor e o loop do agente não estiverem implementados.
- **Motivo informado pelo usuário:** não foi explicado por que prefere que a memória também faça a chamada ao LLM; a decisão foi adaptada para respeitar a dependência técnica ainda pendente.
- **Alternativas e trade-offs discutidos:** acoplar imediatamente `memory.py` ao provedor seria prematuro, pois `llm.py` e `agent.py` ainda são stubs. O callback permite testar e usar outro provedor sem misturar responsabilidades.
- **Riscos ou pendências:** ligar o callback ao provedor real quando a camada LLM e o loop estiverem prontos.

### 2026-11-03 — Limites para resumir e preservar histórico

- **Decisão confirmada:** usar o limite recomendado de 20 mensagens não resumidas para iniciar o resumo e manter as 10 mensagens mais recentes completas.
- **Motivo informado pelo usuário:** o usuário declarou não saber quais limites seriam adequados e autorizou o assistente a escolher.
- **Alternativas e trade-offs discutidos:** um limite muito alto pode enviar contexto excessivo; um limite muito baixo pode descartar contexto recente com frequência. A política adotada resume mensagens antigas, preserva as recentes e não apaga as mensagens originais.
- **Riscos ou pendências:** os números são valores iniciais por quantidade de mensagens, não por tokens; podem precisar de ajuste após medir tamanho real do contexto.

### 2026-11-03 — Redação de dados pessoais na memória

- **Decisão confirmada:** redigir e-mails e telefones reconhecíveis nos argumentos de tools e no conteúdo das mensagens antes de persistir, recuperar para o histórico ou enviar ao resumidor.
- **Motivo informado pelo usuário:** aceitou a recomendação para reduzir a exposição de dados pessoais no histórico do agente.
- **Alternativas e trade-offs discutidos:** guardar esses valores poderia facilitar sua reutilização em turnos posteriores; redigi-los reduz a exposição e exige que a pessoa informe novamente um dado quando ele for necessário.
- **Riscos ou pendências:** expressões de e-mail ou telefone que não forem reconhecidas pelos padrões de redação ainda podem passar sem alteração.

### 2026-11-03 — Rótulos para pedidos de acessórios

- **Decisão confirmada:** pedidos de acessórios recebem os rótulos `acessorio` e `fora_assunto`.
- **Motivo informado pelo usuário:** não foi registrado um motivo próprio; a escolha indica que o pedido deve ser identificado tanto pelo tipo específico quanto como fora do escopo de venda da loja.
- **Alternativas e trade-offs discutidos:** usar apenas `acessorio` seria mais específico; acrescentar `fora_assunto` pode simplificar fluxos que tratam todo assunto fora do escopo da loja de forma semelhante.
- **Riscos ou pendências:** um consumidor do classificador deve evitar responder duas vezes ao combinar ambos os rótulos.

### 2026-11-03 — Integração do loop principal com o provedor

- **Decisão confirmada:** implementar o loop do agente com uma função de modelo injetável e adiar a integração real com Gemini/Groq até que as chaves de API estejam disponíveis.
- **Motivo informado pelo usuário:** vai configurar os provedores Gemini e Groq mais tarde, depois de obter as chaves.
- **Alternativas e trade-offs discutidos:** implementar o provedor agora habilitaria chamadas reais, mas depende das credenciais; a injeção permite testar o fluxo de function calling sem chamadas externas, mas ainda não habilita uso real do LLM.
- **Riscos ou pendências:** concluir a camada de provedor no passo correspondente e configurar as chaves antes de testar com modelos reais.

### 2026-11-03 — Limite de rodadas de function calling

- **Decisão confirmada:** permitir até cinco rodadas de chamadas de tools por mensagem e, após isso, permitir uma chamada final ao modelo sem ferramentas disponíveis.
- **Motivo informado pelo usuário:** cinco rodadas limitam gasto, mas deixam tentativas suficientes para se recuperar de um erro; a chamada final ajuda a produzir uma resposta natural em vez de uma mensagem automatizada.
- **Alternativas e trade-offs discutidos:** encerrar localmente após cinco rodadas seria mais econômico, mas menos contextual. A chamada final não pode executar tools; se não produzir texto ou tentar chamar uma tool, o agente devolve uma resposta segura fixa.
- **Riscos ou pendências:** a chamada final ainda depende da qualidade do modelo; a resposta fixa serve como proteção quando ele não respeita o formato esperado.

### 2026-11-03 — Recuperação de erros de tools

- **Decisão confirmada:** devolver erros de execução em formato estruturado e seguro ao modelo, permitindo que tente corrigir ou continuar dentro do limite de rodadas.
- **Motivo informado pelo usuário:** considera o retorno estruturado uma boa prática de tratamento de erros.
- **Alternativas e trade-offs discutidos:** parar no primeiro erro seria mais simples, mas impediria recuperação de argumentos ou seleção de ferramenta; permitir recuperação consome chamadas adicionais, limitado pelo teto de cinco rodadas.
- **Riscos ou pendências:** detalhes técnicos, argumentos inválidos e dados sensíveis não devem ser incluídos na resposta de erro enviada ao modelo.

### 2026-11-03 — Proteção da chamada final

- **Decisão confirmada:** a chamada final do modelo recebe a lista de tools vazia; se ainda solicitar tool ou não produzir texto, o agente devolve uma resposta segura fixa.
- **Motivo informado pelo usuário:** quer impedir que o modelo envie respostas ruins ao usuário quando não consegue concluir o fluxo.
- **Alternativas e trade-offs discutidos:** permitir tools na chamada final poderia ultrapassar o limite definido; responder com uma mensagem segura é menos contextual, mas evita uma resposta gerada inválida ou um novo ciclo de execução.
- **Riscos ou pendências:** a resposta segura não explica a causa específica e orienta reformular o pedido ou procurar a equipe.
