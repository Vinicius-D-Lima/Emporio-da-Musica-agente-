<!-- Responsabilidade: registrar o uso de assistentes de código e a evolução do projeto Empório da Música por passos. -->

# Uso de assistentes de código

| Data | Passo | O que pedi | O que veio | O que corrigi / decidi |
| --- | --- | --- | --- | --- |
| Não informada | 7 — políticas e parcelamento | Analisar o manual fornecido, resumir as políticas e implementar simulação de parcelas. | Resumo parafraseado em dez seções, acesso isolado às políticas, validação de argumentos, cálculo de 1x a 12x e testes. | Confirmada a regra detalhada do §3.1; a simulação recusa produtos indisponíveis e não acumula desconto PIX com promoção. |
| 2026-11-03 | 8 — memória e histórico | Persistir conversas, recuperar histórico e resumir conversas longas. | Adicionadas funções de criação, registro, recuperação e resumo; 20 mensagens não resumidas acionam o callback, que preserva as 10 mais recentes. | O callback fica injetável até o provedor/loop serem implementados; em falha, mensagens originais permanecem. E-mail e telefone em mensagens e argumentos de tools são redigidos. |
