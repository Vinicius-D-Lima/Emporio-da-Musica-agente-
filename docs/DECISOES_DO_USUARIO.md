<!-- Responsabilidade: separar as decisões e palavras do usuário da análise e dos riscos identificados pelo assistente. -->

# Decisões do usuário

Este registro guarda decisões tomadas pelo usuário durante o projeto, especialmente as esclarecidas por meio da skill `grillme`. Ele complementa [DECISOES.md](./DECISOES.md), que reúne as decisões técnicas consolidadas. O campo **Suas palavras** contém somente motivos expressos pelo usuário; a análise e os riscos são identificados como conteúdo do assistente. Nas entradas antigas em que não há uma fala literal disponível, o campo informa **"não informado"** em vez de reconstruir uma citação.

Cada entrada segue quatro campos:

- **Decisão**
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado")** (correções apenas de ortografia e coerência)
- **Análise do assistente (alternativas e trade-offs)**
- **Riscos e pendências (assistente)**

## Decisões registradas

### 2026-11-03 — Como conduzir questionamentos e registrar decisões

- **Decisão:** apresentar opções, deixar o usuário explicar sua escolha, continuar questionando quando houver pontos relevantes a esclarecer e oferecer explicação das opções quando solicitada.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** “Eu quero que você modifique uma coisa na skill Grillme sobre os questionamentos. Quero que você me dê a opção e me deixe explicar por que escolhi aquela opção. Se aquela opção não for a melhor ou o raciocínio não for legal, continue me questionando até eu ter certeza das decisões. Coloque uma opção para o caso de eu não ter entendido as opções, para você me explicar. Preciso que você crie um .md sobre as decisões que estou tomando, colocando a decisão e explicando a decisão que tomei.”
- **Análise do assistente (alternativas e trade-offs):** a entrevista deve testar escolhas sem pressionar o usuário a adotar a preferência do assistente; após uma confirmação informada, o questionamento daquela decisão termina.
- **Riscos e pendências (assistente):** nenhuma pendência para a atualização da skill; a confirmação final da decisão deve permanecer explícita.

### 2026-11-03 — Regra de parcelamento do manual

- **Decisão:** usar os mínimos detalhados na seção §3.1 do manual: 1x permitido; 2–3 parcelas com mínimo de R$ 50 por parcela; 4–6 com mínimo de R$ 80; 7–12 com mínimo de R$ 100.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** eu optei por essa decisão porque é que ta no manual e dei prioridade pro manual e nao pros dados.
- **Análise do assistente (alternativas e trade-offs):** a tabela geral apresenta R$ 100 como mínimo, enquanto a seção §3.1 discrimina faixas menores. A simulação segue a seção detalhada e não trata a divergência como resolvida pelo próprio manual.
- **Riscos e pendências (assistente):** confirmar a regra com a loja antes de uso comercial real.

### 2026-11-03 — Produtos indisponíveis na simulação

- **Decisão:** não simular parcelamento de produto sem estoque, fora do catálogo, em breve ou descontinuado; retornar indisponibilidade estruturada.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** essa decisão foi porque o agente poderia inventar dados pra poder complementar o que ele não sabe isso seria prejudicial.
- **Análise do assistente (alternativas e trade-offs):** em vez de cotar um item indisponível, informar a situação. Isso evita sugerir ao cliente que o produto está disponível.
- **Riscos e pendências (assistente):** a equipe pode decidir futuramente tratar encomendas ou pré-vendas com regras específicas.

### 2026-11-03 — Contatos da loja

- **Decisão:** adotar a opção B para separar o telefone da loja e o WhatsApp em números distintos, além de usar a grafia do e-mail sem acento.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** existia dois numeros distintos e um apontava pro whatsApp e outro pra loja então optei por separar e identificar eles no codigo, além de usar a grafia de email sem acento, porque com acento aparece como erro.
- **Análise do assistente (alternativas e trade-offs):** manter os números separados facilita indicar o canal adequado; a escolha documental pode não corresponder aos contatos atuais da loja.
- **Riscos e pendências (assistente):** confirmar os dados com o responsável antes de uso real.

### 2026-11-03 — Resumo de conversas e integração com LLM

- **Decisão:** permitir que um LLM produza o resumo, integrando-o por callback injetável enquanto o provedor e o loop do agente não estiverem implementados.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** foi uma decisão temporaria enquanto eu não configurava as chaves dos provedores.
- **Análise do assistente (alternativas e trade-offs):** acoplar imediatamente `memory.py` ao provedor seria prematuro, pois `llm.py` e `agent.py` ainda eram stubs. O callback permite testar e usar outro provedor sem misturar responsabilidades.
- **Riscos e pendências (assistente):** ligar o callback ao provedor real quando a camada LLM e o loop estiverem prontos.

### 2026-11-03 — Limites para resumir e preservar histórico

- **Decisão:** usar o limite de 20 mensagens não resumidas para iniciar o resumo e manter completas as 10 mensagens mais recentes; os valores foram escolhidos pelo assistente a pedido do usuário.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** valores iniciais por quantidade de mensagens, escolhidos pelo assistente, ajustar depois de medir os tokens reais
- **Análise do assistente (alternativas e trade-offs):** um limite muito alto pode enviar contexto excessivo; um limite muito baixo pode descartar contexto recente com frequência. A política adotada resume mensagens antigas, preserva as recentes e não apaga as mensagens originais.
- **Riscos e pendências (assistente):** os números são valores iniciais por quantidade de mensagens, não por tokens; podem   precisar de ajuste após medir o tamanho real do contexto.

### 2026-11-03 — Redação de dados pessoais na memória

- **Decisão:** redigir e-mails e telefones reconhecíveis nos argumentos de tools e no conteúdo das mensagens antes de persistir, recuperar para o histórico ou enviar ao resumidor.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** O email e o telefone do cliente já estão na tabela customers. Copiar pro histórico só duplica o dado e aumenta o risco de vazar.
- **Análise do assistente (alternativas e trade-offs):** guardar esses valores poderia facilitar sua reutilização em turnos posteriores; redigi-los reduz a exposição e exige que a pessoa informe novamente um dado quando ele for necessário.
- **Riscos e pendências (assistente):** expressões de e-mail ou telefone que não forem reconhecidas pelos padrões de redação ainda podem passar sem alteração.

### 2026-11-03 — Rótulos para pedidos de acessórios

- **Decisão:** pedidos de acessórios recebem os rótulos `acessorio` e `fora_assunto`.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** isso separa o que é acessorio de musica relacionado ao tema(mesmo que nao seja da loja) e algo totalmente fora do escopo(ex: comida).
- **Análise do assistente (alternativas e trade-offs):** usar apenas `acessorio` seria mais específico; acrescentar `fora_assunto` pode simplificar fluxos que tratam todo assunto fora do escopo da loja de forma semelhante.
- **Riscos e pendências (assistente):** um consumidor do classificador deve evitar responder duas vezes ao combinar ambos os rótulos.

### 2026-11-03 — Integração do loop principal com o provedor

- **Decisão:** inicialmente adiar a integração real e implementar o loop com modelo injetável; depois, substituir essa decisão pelo pedido para concluir os passos pendentes até o Passo 12.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** não informado.
- **Análise do assistente (alternativas e trade-offs):** a implementação com callback permitiu avançar sem credenciais; a integração atual conclui a conexão, mas testes reais podem consumir créditos e enviar conteúdo aos provedores.
- **Riscos e pendências (assistente):** a integração foi testada com clientes simulados; uma chamada real controlada deve confirmar acesso, compatibilidade e comportamento dos endpoints antes de uso com clientes.

### 2026-11-03 — Limite de rodadas de function calling

- **Decisão:** permitir até cinco rodadas de chamadas de tools por mensagem e, após isso, permitir uma chamada final ao modelo sem ferramentas disponíveis.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** não informado.
- **Análise do assistente (alternativas e trade-offs):** encerrar localmente após cinco rodadas seria mais econômico, mas menos contextual. A chamada final não pode executar tools; se não produzir texto ou tentar chamar uma tool, o agente devolve uma resposta segura fixa.
- **Riscos e pendências (assistente):** a chamada final ainda depende da qualidade do modelo; a resposta fixa serve como proteção quando ele não respeita o formato esperado.

### 2026-11-03 — Recuperação de erros de tools

- **Decisão:** devolver erros de execução em formato estruturado e seguro ao modelo, permitindo que tente corrigir ou continuar dentro do limite de rodadas.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** “A ideia seria não parar no primeiro erro, porque poderia ser menos natural e poderia perder a recuperação dos argumentos anteriores.”
- **Análise do assistente (alternativas e trade-offs):** parar no primeiro erro seria mais simples, mas impediria a recuperação de argumentos ou seleção de ferramenta; permitir recuperação consome chamadas adicionais, limitado pelo teto de cinco rodadas.
- **Riscos e pendências (assistente):** detalhes técnicos, argumentos inválidos e dados sensíveis não devem ser incluídos na resposta de erro enviada ao modelo.

### 2026-11-03 — Proteção da chamada final

- **Decisão:** a chamada final do modelo recebe a lista de tools vazia; se ainda solicitar uma tool ou não produzir texto, o agente devolve uma resposta segura fixa.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** “Não quero que o agente responda com uma mensagem de erro para o usuário, então preciso que responda com uma chamada mais confiante e precisa.”
- **Análise do assistente (alternativas e trade-offs):** permitir tools na chamada final poderia ultrapassar o limite definido; responder com uma mensagem segura é menos contextual, mas evita uma resposta gerada inválida ou um novo ciclo de execução.
- **Riscos e pendências (assistente):** a resposta segura não explica a causa específica e orienta reformular o pedido ou procurar a equipe.

### 2026-11-03 — Atualização do modelo Gemini após erro 404

- **Decisão:** substituir `gemini-2.5-flash` por `gemini-3.5-flash-lite` como modelo principal.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** “O `gemini-2.5-flash` não funciona, então troquei pelo mais recente.”
- **Análise do assistente (alternativas e trade-offs):** manter o modelo anterior poderia continuar retornando 404 para contas sem acesso; o novo modelo evita depender de acesso a um modelo descontinuado, mas seu comportamento e disponibilidade ainda precisam ser testados na conta.
- **Riscos e pendências (assistente):** validar uma chamada real controlada e confirmar limites e preços antes de uso comercial.

### 2026-11-03 — Fallback do Gemini para o Groq

- **Decisão:** tentar o Groq como reserva quando o Gemini falhar por indisponibilidade (404), limite (429), timeout ou erro 5xx; não fazer fallback em erros 400/401.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** “Existe um problema também, porque, se a chamada no Gemini falhar, precisa chamar no Groq como segurança.”
- **Análise do assistente (alternativas e trade-offs):** encaminhar qualquer erro 4xx à reserva poderia mascarar problemas de credenciais ou requisições malformadas; restringir o fallback aos casos definidos torna esses outros erros visíveis.
- **Riscos e pendências (assistente):** o Groq também pode falhar ou atingir seus próprios limites; o erro final deve identificar o provedor sem expor chaves.

### 2026-11-03 — Interação pela CLI

- **Decisão:** oferecer uma CLI interativa, com uma mensagem por linha, sem entrada multilinha ou captura de `Shift+Enter`.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** “Porque era mais simples inicialmente e tenho pouco tempo para a entrega.”
- **Análise do assistente (alternativas e trade-offs):** capturar `Shift+Enter` poderia permitir quebras de linha, mas exige tratamento específico de terminal e pode reduzir a compatibilidade; entrada de uma linha é mais simples, mas não permite compor mensagens multilinha.
- **Riscos e pendências (assistente):** o usuário não poderá enviar quebras de linha em uma mensagem; a conversa segue por mensagens separadas.

### 2026-11-03 — Diagnóstico do erro 400 do Gemini

- **Decisão:** extrair campos técnicos permitidos da resposta do provedor somente em `--debug`, com limite e redação; não registrar o corpo da requisição, histórico, argumentos de tools ou chaves.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** “Escolhi essa opção porque ela mostra o erro de verdade (o provedor não mostra o erro detalhado), não expõe dados de nenhum cliente (ele só registra o resultado) e evita chutes para descobrir a causa.” Depois, ao escolher extrair mais detalhes da resposta: “Eu preciso encontrar o erro.”
- **Análise do assistente (alternativas e trade-offs):** campos permitidos como mensagem, código, status e detalhes estruturados podem indicar se o 400 veio do schema das ferramentas, do formato da requisição ou de outra validação. Registrar somente metadados reduziria a exposição, mas poderia não esclarecer a causa.
- **Riscos e pendências (assistente):** a causa foi identificada como perda da `thought_signature` entre a chamada da ferramenta e a requisição seguinte. Mensagens técnicas podem, em casos incomuns, ecoar trechos não reconhecidos como dados sensíveis. Durante a reprodução, o `--debug` padrão também mostrou cabeçalhos HTTP, incluindo `Set-Cookie`; os logs de transporte de terceiros foram suprimidos. O usuário deve revisar o diagnóstico antes de compartilhá-lo.

### 2026-11-03 — Preservação da thought signature do Gemini

- **Decisão:** manter o endpoint OpenAI-compatible e carregar a `thought_signature` da chamada de ferramenta durante a volta do function calling, inclusive quando houver migração para o SDK nativo do Gemini. A assinatura fica apenas em memória.
- **Suas palavras (literal, copiado da sua resposta; se não deu motivo: "não informado"):** “Eu escolhi esse motivo por não ter muito tempo para a entrega e por eu usar dois modelos diferentes no projeto.”
- **Análise do assistente (alternativas e trade-offs):** usar o SDK nativo para todas as chamadas do Gemini permitiria trabalhar diretamente com os tipos do Google, mas exigiria uma integração maior e deixaria duas interfaces de provedores no projeto. Preservar a assinatura no adaptador existente é a alteração mais localizada e mantém o cliente OpenAI-compatible compartilhado; o caminho nativo também precisa reconstruir a parte com a assinatura para evitar repetir a falha.
- **Riscos e pendências (assistente):** os testes automatizados verificam a preservação nos dois caminhos, mas falta o usuário repetir a conversa com uma chamada real do Gemini para confirmar a compatibilidade ponta a ponta. A assinatura é metadado opaco do provedor e não deve ser registrada em banco ou logs.
