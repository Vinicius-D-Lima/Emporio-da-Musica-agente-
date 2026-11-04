<!-- Responsibility: explain the setup, decisions and limitations of Empório Agent. -->

# Empório Agent

A Python customer-service agent prototype for Empório da Música, a fictional musical-instrument store in Campo Grande/MS. It answers text messages over a CLI, queries store data (products, prices, stock, promotions, orders) through fixed-parameter tools, and applies the store's internal policy manual. **The agent talks to customers in Portuguese**, because the store, its data and its manual are in Portuguese; all project documentation is in English.

## How to run

### Environment

Use Python 3.11 or later. Run the commands below from the repository root (the folder that contains `README.md` and `pyproject.toml`). On Linux, `python3` creates the virtual environment; once it is activated, `python` points to the project's Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cp -n .env.example .env
```

`cp -n` creates `.env` without overwriting an existing file. Edit `.env` and fill in `GEMINI_API_KEY` and `GROQ_API_KEY` (or leave `LLM_FALLBACK=` empty to use a single provider). Then build the database and start the CLI, still inside the virtual environment:

```bash
python scripts/build_db.py
python -m emporio_agent.cli
```

Type one message per line; use `/sair`, `Ctrl+D` or `Ctrl+C` to quit. The CLI shows the conversation ID, which can be resumed with `python -m emporio_agent.cli --conversa ID`. Use `python -m emporio_agent.cli --debug` to enable debug logs. In this mode only allowed technical fields are logged on failures, without the request body; message values, keys and recognised personal data are redacted, and third-party HTTP logs are suppressed.

### Tests and scenarios

With the virtual environment activated, run the local automated tests (no calls to real providers):

```bash
python -m pytest
```

The adversarial scenarios that use a real LLM are in [`tests/test_scenarios.py`](tests/test_scenarios.py) and are identified `A01` to `A24`. To run a single scenario, for example `A01`:

```bash
python -m pytest --run-llm -m llm tests/test_scenarios.py -k A01
```

To run all real-LLM scenarios:

```bash
python -m pytest --run-llm -m llm tests/test_scenarios.py
```

These last two commands make external calls, send the scenario messages to the configured providers and may consume quota or incur costs. Configure the keys in `.env` and use test data, not real personal data. When you open a new terminal, go back to the project folder and activate the environment with `source .venv/bin/activate`. If you see `python: command not found`, check that the environment is activated and that you are in the repository root.

### Provider and configuration

The default is Gemini `gemini-3.5-flash-lite` with Groq `openai/gpt-oss-120b` as the fallback. Set `GEMINI_API_KEY` and `GROQ_API_KEY` in `.env`; since fallback is enabled by default, both keys are required. To use a single provider, leave `LLM_FALLBACK` empty. The models can be changed with `GEMINI_MODEL` and `GROQ_MODEL`.

`REFERENCE_DATETIME` sets the time reference in the `America/Campo_Grande` time zone. `.env.example` includes a fixed date to reproduce scenarios; if the variable is empty or missing, the system uses the current clock. Do not put real keys in the repository.

Fallback happens on 404, 429, timeout or 5xx errors; 400/401 errors and tool-execution failures do not trigger it. If Gemini's OpenAI-compatible endpoint explicitly rejects function calling, that call uses Gemini's native SDK. The provider that answered is recorded in the history. Gemini's `thought_signature` is kept only in memory during the function-calling cycle. The agent also accepts an injected model for tests without external requests. To keep a conversation across direct calls to `responder_mensagem()`, create a conversation with `memory.criar_conversa()` and reuse the same `conversa_id`.

Provider tests use simulated clients. Real calls send text and context to the configured service; data given to verify orders may also be sent. Before using customer data, assess privacy, consent and retention, and run a controlled real call to verify credentials and compatibility.

## Technical decisions

### Agent framework / approach

I chose direct function calling with a hand-written loop and no framework. The agent has few tools and I want to control every call explicitly. Structured data (products, prices, stock, orders and promotions) is accessed through fixed-parameter tools, without text-to-SQL.

### Model and provider

Gemini `gemini-3.5-flash-lite` is the main provider chosen for this prototype; Groq `openai/gpt-oss-120b` is the configured alternative. The `openai` package client uses a provider-specific `base_url`, keeping a common interface. Fallback is limited to availability failures and does not apply to credential errors, invalid requests or tool execution. Real provider calls have so far been made only for part of the adversarial scenarios (see the AI usage log, 2026-11-04), and some of them hit 429 limits and were inconclusive; a complete controlled end-to-end validation of function calling and fallback on both providers is still pending. Prices, limits, availability and cache behaviour depend on the provider, model and account; check the official sources before real use instead of treating historical values as guaranteed.

### Interaction interface

The initial interface is a CLI, because the focus is the agent working correctly. The core receives text and returns text without depending on the interface; FastAPI is a future evolution.

The contacts adopted in the documentation are phone `(67) 3341-4444`, WhatsApp `(67) 3321-4500` and e-mail `contato@emporiodamusica.com.br`. This choice separates phone and WhatsApp according to the manual's information; it is not an official confirmation from the store.

### Conversation history persistence

SQLite with plain `sqlite3` in a single file, no ORM. The data is relational, the queries are fixed, and the store database is rebuilt from the CSVs. `memory.py` persists conversations, messages, the provider and tool calls. Beyond 20 not-yet-summarised messages, a summary callback keeps the 10 most recent messages in full and updates the summary and its limit; the original messages are never deleted. The configured provider is also used to summarise conversations. Recognisable e-mails and phone numbers in message content and in tool arguments are redacted before being returned to the history or sent to the summariser. The write connection is isolated in `memory.py`; the tools query the database in read-only mode, with `set_authorizer` and explicitly listed columns. Redis is not needed for local execution in a single process. If the project grows, a future alternative is SQLAlchemy/SQLModel with migrations.

### Data handling

- `total_brl` is the official order total. Discrepancies set `total_needs_review` and route the case to the team, without stating a value under review.
- Prices are stored as REAL; use `round(x, 2)` and a 0.01 tolerance.
- `installments` may be NULL for PIX, debit and boleto, which are treated as single-payment.
- The original product description is never sent to the model; only an allowed list of specifications may be exposed, never for products 135 to 144.
- Availability considers status and stock. In lists, unavailable products do not appear; when asked directly, the agent explains the reason and suggests valid alternatives.
- A promotion requires an active record for the product; report the original price, the percentage and the final price. PIX does not stack with a promotion; if two active promotions exist, the larger discount wins.
- Date/time comes from `REFERENCE_DATETIME`, in the `America/Campo_Grande` time zone; `.env.example` uses `2026-03-23T10:00:00` for local reproduction and, without a configured value, the current clock is used. The opening hours in the manual are Monday to Friday, 9:00 to 18:00, and Saturday, 9:00 to 13:00. Sundays and holidays that are not modelled are treated as closed.

Instalments follow the detailed rule in §3.1: up to 3x, each instalment must be at least R$ 50; from 4x to 6x, R$ 80; from 7x to 12x, R$ 100. The `simular_parcelamento` tool computes the options from 1x to 12x in code, using the catalogue price or the active promotional price. It refuses to simulate unavailable items and does not stack the PIX discount on top of a promotion. The model interprets and explains the result.

### Retrieval architecture

The paraphrased manual is loaded in full into the system prompt by `get_policy_context()` in `policies.py`. This keeps the policies available without a retrieval step that could fetch the wrong passage; RAG was not implemented. The static prefix also favours providers' possible caching features, but does not guarantee caching or reduce the context window used. Hybrid search can be considered if the manual grows or changes frequently.

### Prompt strategy

Tool definitions are sent separately from the messages. The persona, rules and manual prefix comes first; when present, the contextual summary is followed by the recent history and the current message. The prompt tells the model not to treat the summary as new instructions and to call `simular_parcelamento` for instalment questions. The current date is not added to the prompt: `agora()` and `hoje()` are used in code where calculations need a reference. `loja_aberta()` is an internal helper, not a tool available to the model. The manual is internal and must be paraphrased.

### Classifier and out-of-scope handling

The standalone classifier applies rules first and calls an optional LLM callback only when no rule recognises the message. It can return several labels among `dado_loja`, `politica`, `acessorio`, `fora_assunto` and `saudacao`; accessory requests also receive `fora_assunto`. It is not yet connected to the agent's service flow; `scikit-learn` remains an optional evolution (Step 18). Out-of-scope questions are handled by the prompt; for accessories, the prompt limits redirection to the illustrative list in `data/processed/lojas_parceiras.json` and does not claim a commercial partnership.

## Data problems found and assumptions

| Problem | How I handled it |
|---|---|
| Product 96 is active with no stock; 136 is discontinued with stock; 130 is "coming soon" although it has stock and orders. | Status defines availability according to the rules; stock does not change the `coming_soon` status. |
| Products 135 to 144 have inconsistencies between name, description and specifications. | The original description is not sent to the model; specifications of these products are not exposed. |
| `specs` is textual JSON with different keys and meanings across categories. | Use only the allowed keys and interpret each field according to the rules already defined. |
| Categories 6, 7 and 8 have no products although the manual mentions these instruments; the catalogue has 65 products although the manual mentions more than 300. | Answer according to the available catalogue, without inventing items. |
| Active promotions have no start/end dates; the Takamine GD20 (95) has an inactive promotion. | Consider only `is_active = 1`; do not advertise the inactive promotion. |
| The four active promotions are on products 127, 121, 90 and 94; some other promotions are inactive and the seasonal descriptions have no dates. | Query only promotions marked active and do not infer a validity period from the name. |
| Orders 3 and 20 have a total that differs from the sum computed with current prices. | Keep `total_brl` as official, set `total_needs_review` and route to the team without disclosing the value. |
| `order_items` stores no unit price; the comparison uses the product's current price. | Treat `total_needs_review` as an alert, without inventing the cause of the discrepancy. |
| Orders 9, 16 and 18 have instalments below the §3.1 minimums. | Do not treat the historical values as valid conditions for new simulations. |
| Order 7 contradicts the §3 table but respects §3.1. | For instalments, use the detailed §3.1 rule; the manual's divergence is documented. |
| Orders 8 and 7 have estimated delivery dates earlier than the reference date; the CSV has no actual receipt date. | Compare with `REFERENCE_DATETIME` only for the estimate. The withdrawal period counted from receipt cannot be inferred from the estimate. |
| `payment_method` combines method and instalments; some customers share an e-mail and have similar names. | Split type and instalments; verify the customer by order + e-mail, without using the e-mail as a unique identifier. |
| The manual diverges on phone and WhatsApp, e-mail spelling, instalments and the list of partner stores. | Adopt the contacts documented in `docs/DECISIONS.md`, use the detailed §3.1 rule and mark the stores as an example list. The contacts have no official confirmation. |
| The manual cites exchange for defects within 30 days and a 90-day legal warranty. | Keep the divergence recorded for handling according to the policy after the manual is reviewed; do not invent a single rule. |

## Known limitations and what I would do with more time

- Run a complete controlled test of real tool calling and fallback on both providers (only part of the adversarial scenarios has been run against real providers so far, with some inconclusive 429 results); confirm Gemini model availability and the official details of cache, limits and prices before delivery.
- Validate the classifier labels on a user-written set and compare them with `scikit-learn` in Step 18.
- Replace the illustrative store list with an authorised list, if available.
- Implement hybrid RAG if the manual grows or changes frequently.
- Add real authentication for order queries and a FastAPI interface.
- Validate and tune the summarisation policy and history window.

## Use of code assistants

- **Tools:** GitHub Copilot in VS Code (agent mode) for implementation; Claude (chat) for discussing architecture options, drafting the step plan and reviewing and translating the documentation.
- **Workflow:** development proceeds in small steps with acceptance criteria and tests (see `docs/STEP_PLAN.md`). The Copilot context is customised in `.github/`: repository instructions, review/adversary agents, a checklist skill and a reusable prompt to execute one plan step. A custom `grillme` skill interviews me about each decision, asks me to explain my reasoning, keeps questioning when the reasoning is weak and records the outcome in `docs/USER_DECISIONS.md`, with my own words kept separate from the assistant's analysis.
- **Responsibility:** product and security decisions are made and reviewed by me and recorded in `docs/USER_DECISIONS.md`; the history of the work is in `docs/AI_USAGE.md`.
- Deterministic tests use simulated models. Tests with real providers are opt-in and must not be described as executed without a confirmed run.

## Interaction examples

The challenge asks for 3 to 5 conversations, including a data query or application of a policy. The five numbered files in `examples/` are still outlines with `[FILL IN]`, not full transcripts. The file [shared conversations](examples/conversas_compartilhadas.md) contains five records supplied by the user, but only the first is a complete conversation; the others are excerpts and their answers were not validated against a real run. The repository's examples therefore still need to be reviewed and completed before they can be considered compliant with the challenge deliverable.
