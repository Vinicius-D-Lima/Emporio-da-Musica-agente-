<!-- Responsibility: record the consolidated project decisions and the items that still need validation. -->

# Project decisions

The decisions recorded by the user, and the reasons given during the conversations, are in [USER_DECISIONS.md](./USER_DECISIONS.md). This document consolidates the technical decisions and the validations still pending; the detailed diagnosis of the data and of the manual's divergences is in the [README.md](../README.md).

## Decided

| Decision | Reason |
|---|---|
| Direct function calling, manual loop, no framework. | The project has few tools and needs explicit control over the calls. |
| Structured data accessed through fixed-parameter tools, no text-to-SQL. | Avoids freely model-generated queries. |
| Paraphrased manual in the system prompt; RAG stays a future evolution. | Keeps the policies available in the context. The static prefix may favour provider cache features, without guaranteeing the cache is used. |
| Gemini `gemini-3.5-flash-lite` as main and Groq `openai/gpt-oss-120b` as backup. | The Gemini model was updated after the previous one returned 404, according to the documentation consulted at the time. |
| One `openai` package client, with a provider-specific `base_url`. | Keeps a uniform communication interface. |
| If Gemini's tool calling is incompatible with the OpenAI-compatible endpoint, only Gemini moves to the native SDK. | Isolates the adaptation to the provider that shows the incompatibility. |
| Gemini's `thought_signature` is preserved in memory through the function-calling round trip, on both the compatible and the native path; it is never stored in the database or logs. | The Gemini 400 error was traced to the signature being lost between the tool call and the next request; this was the most localised fix and keeps a shared client for both providers. |
| The provider that answered is recorded on each message. | Makes it possible to identify which provider served each call. |
| SQLite with plain `sqlite3`, one file, no ORM. | Keeps a small database with controlled queries simple. |
| Prices as REAL, rounding with `round(x, 2)` and a 0.01 tolerance. | Standardises price calculations and comparisons. |
| `installments` accepts NULL for PIX, debit and boleto. | Instalments do not apply to those methods; the answer will indicate single payment. |
| Instalments follow §3.1: up to 3x, minimum R$ 50 per instalment; 4x to 6x, R$ 80; 7x to 12x, R$ 100. | The detailed §3.1 rule was chosen over the general §3 table, which diverges from it. |
| The `simular_parcelamento` tool centralises the calculations in code. | Avoids arithmetic mistakes, invented conditions and token use on calculations. |
| The simulation accepts a product or an explicit amount, never both; unavailable items are not split into instalments. | Keeps the price source unambiguous and avoids quoting products that are not available for sale. |
| Summarise after more than 20 unsummarised messages, keeping the 10 most recent; the summary is produced by an injectable callback and updated only after success. | Keeps recent context, limits the history size and preserves all messages if the provider fails. |
| Redact e-mails and phone numbers in tool-call arguments and message texts before they go back to the history or the summariser. | Reduces exposure and unnecessary retention of personal data in the agent's context. |
| Keep the static persona/rules/manual prompt before the summary and history; insert the summary as delimited context, not as new instructions. | Preserves the defined order, makes the static prefix easier to reuse and reduces the risk of instructions quoted in the summary changing the agent's rules. |
| The main loop accepts an injectable model and by default uses `llm.py` to call Gemini/Groq; tool schemas are validated with Pydantic. | Allows tests without network and keeps provider coupling separate from the agent. |
| If Gemini's OpenAI-compatible endpoint explicitly rejects function calling, the Gemini call is adapted to the native SDK; fallback to Groq happens on 404, 429, timeout and 5xx, but not on 400/401. | Preserves the tool flow and limits fallback to unavailability or transient failures. |
| Limit tool calling to five rounds, allow one final call without tools and use a safe answer if the model keeps calling tools or produces no text. | Limits consumption and cycles, keeping a chance of a natural answer without exceeding the tool-execution ceiling. |
| Known tool errors are returned to the model as a safe structure and recorded as failures; internal details and sensitive values are not sent. | Allows a recovery attempt without exposing arguments or operational details. |
| `total_brl` is the official value; discrepancies set `total_needs_review` and route the case to the team. | The order total must not be replaced by an estimate using the current price. |
| The original product description is never sent to the model. | The data has inconsistencies between descriptions, names and specifications. |
| The customer is identified by order number and e-mail; the verified `customer_id` stays in the session. | Identity must not come as a model argument. |
| The classifier uses rules first and calls an optional LLM callback only when no rule recognises the message; without a callback it returns an empty list. It can return several labels from the taxonomy `dado_loja`, `politica`, `acessorio`, `fora_assunto` and `saudacao`; accessories also receive `fora_assunto`. | Keeps classification predictable, allows later integration without coupling the module, and combines intents without creating `misto`. |
| Interactive CLI with one message per line, resumption through `--conversa ID` and logs enabled by `--debug`; `/sair`, EOF or Ctrl+C ends the session. | Terminal interaction keeps the flow simple and compatible with ordinary terminals. |
| In `--debug`, only allowed technical fields from the provider's error (status, code, parameter, truncated message) are logged, with redaction; the request body, history, tool arguments and keys are never logged, and third-party HTTP transport logs are suppressed. | Shows the real error without exposing customer data and avoids guessing the cause. |
| `scikit-learn` stays as a Step 18 evolution. | The comparison will be made later, on the same test set. |
| Accessories are redirected using a fixed list of example stores, without claiming a real partnership. | The manual does not provide an authorised list of establishments. |
| Date and time use `REFERENCE_DATETIME`, in the `America/Campo_Grande` time zone; `.env.example` contains `2026-03-23T10:00:00` for local reproduction. | Without a configured value the code uses the current clock; the example date is not the code's automatic default. |
| If two active promotions exist for the same product, the one with the larger discount prevails. | Avoids stacking discounts and defines a deterministic result. (No product in the current data has two active promotions; the rule is defensive and covered by a synthetic test.) |
| `promocoes_ativas` accepts `product_id` or a name/model; ambiguous queries return candidates without prices and require clarification. | Allows a more natural query without the agent silently choosing between similar products. |
| Phone `(67) 3341-4444`, WhatsApp `(67) 3321-4500` and e-mail `contato@emporiodamusica.com.br`. | Option B separates the channels according to the manual's divergence; the e-mail domain is used without the accent. These are values adopted for the prototype, not confirmed by the store. |
| In the adversarial scenarios, a safe refusal without a tool call is accepted as long as the answer does not state an unconfirmed price, discount, instalment, stock or promotion; store recommendations are limited to the configured list; real-LLM scenarios are run in small batches because of 429 limits. | Tolerates model variation while the checks keep blocking any unconfirmed data. |
| GitHub Copilot is the development tool. | It is the tool chosen to work with instructions, agents, sub-agents and skills. |

## Open

- Validate function calling and fallback of the providers in a complete controlled real run; part of the adversarial scenarios has been run against real providers, with some inconclusive results because of 429 limits, and automated tests use simulated clients.
- Confirm, in official sources and on the account used, availability, prices, limits and cache before any real use; this data is variable and is not fixed here.
- Confirm the contacts and replace the illustrative list with an authorised list if the prototype comes to represent a real store.
- Adversarial tests that call an LLM are opt-in; real results still need to be evaluated and may be inconclusive because of provider limits.
- The classifier in `intent.py` is standalone and not connected to the agent flow; `scikit-learn` remains optional in Step 18.
- `orders.notes` is returned as the cancellation reason. The current data contains operational reasons; before sending real data in this column to the model, possible personal data must be filtered.
- The README documents example outlines that still contain `[FILL IN]`; completing 3 to 5 representative conversations is still pending.
