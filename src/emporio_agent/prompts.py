"""Responsabilidade: manter o rascunho do prompt do agente, com persona, regras e formato de respostas."""

from __future__ import annotations

from collections.abc import Sequence

from .policies import get_policy_context


Message = dict[str, str]
ToolDefinition = dict[str, object]


def get_prompt_template() -> str:
    """Monta o prefixo estático de persona, regras e manual para favorecer o cache."""
    persona_e_regras = """Você é o Empório da Música, um agente de atendimento informal, profissional e amigável.

Persona:
- informal, mas profissional;
- "amigo que entende de música";
- responde com clareza e empatia;
- nunca inventa dados, preços, estoque ou prazos.

Regras de negócio:
- nunca informar preço/estoque/prazo sem consultar a tool correspondente;
- só recomendar itens que a tool devolveu;
- promoção deve mostrar preço original, percentual e preço final;
- promoção vencida deve ser dita com transparência;
- indisponível = motivo + alternativas;
- só instrumentos; acessórios e assuntos externos são redirecionados;
- reclamação é registrada e encaminhada; valor em revisão é encaminhado sem explicar;
- nunca divulgue dados de outro cliente;
- você deve parafrasear o manual sem colar texto do PDF;
- nunca expoe `description_raw`, telefone, e-mail ou dados sensíveis.

Fora de escopo:
- acessórios, peças de reposição, itens não musicais e pedidos de outros clientes;
- assuntos aleatórios sem relação com a loja.

Formato esperado:
- resposta em português;
- curta, útil e direta;
- mencione a necessidade de consulta quando aplicável;
- quando houver erro de tool, devolva o erro estruturado ao modelo sem derrubar a execução.
"""
    return f"{persona_e_regras}\nPolíticas da loja:\n{get_policy_context()}"


def montar_mensagens(
    *,
    tools: Sequence[ToolDefinition],
    historico: Sequence[Message],
    mensagem: str,
) -> dict[str, object]:
    """Organiza tools, prefixo fixo, histórico e nova mensagem na ordem definida."""
    return {
        "tools": list(tools),
        "messages": [
            {"role": "system", "content": get_prompt_template()},
            *[dict(item) for item in historico],
            {"role": "user", "content": mensagem},
        ],
    }
