<!-- Responsibility: record the execution plan, in steps, of the Empório da Música project. -->

# Step plan for the `emporio-agente` project

## Consolidated decisions guiding the steps

- Main provider Gemini Flash-Lite (`gemini-3.5-flash-lite`); backup Groq (`openai/gpt-oss-120b`); `openai` client with a `base_url` per provider. If Gemini's tool calling is incompatible, only it moves to the native SDK.
- Fallback on 404, 429, timeout and 5xx; 400/401 errors and tool-execution errors do not trigger fallback; record the provider that answered.
- Instalments follow §3.1 and will be computed by the planned `simular_parcelamento` tool, not by the model.
- Classifier based first on rules, with an LLM when in doubt and multiple labels: `dado_loja`, `politica`, `acessorio`, `fora_assunto`, `saudacao`. `scikit-learn` is left for Step 18.
- Accessories are redirected using the illustrative list in `data/processed/lojas_parceiras.json`, without claiming a real partnership.
- Documented contacts: phone `(67) 3341-4444`, WhatsApp `(67) 3321-4500` and e-mail `contato@emporiodamusica.com.br`; there is no official confirmation.
- Time reference: `REFERENCE_DATETIME=2026-03-23T10:00:00`, in the `America/Campo_Grande` time zone; use `agora()`/`hoje()`.
- Summarised history with recent messages in full; two active promotions on the same product are resolved by the larger discount.

## Step 0 — Skeleton, documentation and assistant context

Acceptance criteria:
- directory structure created;
- `README.md` and GitHub Copilot instructions in `.github/copilot-instructions.md`;
- review/adversary agents, a checklist skill and a reusable prompt in `.github/`;
- `docs/` with architecture, decisions, AI usage and the step plan;
- `pyproject.toml` with minimal dependencies and the `llm` marker;
- `src/emporio_agent` with stubbed modules and a complete `schema.sql`;
- `tests/` with stubs and `@pytest.mark.skip(reason="Step N")`;
- `.env.example` file with provider configuration and `REFERENCE_DATETIME`, and `.gitignore` created;
- `data/processed/politicas.md` with the manual's sections;
- `examples/` with outline files.

## Step 1 — Data preparation and database build

Acceptance criteria:
- `scripts/build_db.py` is idempotent;
- store tables are recreated from the CSVs and `data/emporio.db` is generated;
- counts: categories 9, customers 50, orders 20, order_items 22, products 65, promotions 25;
- running twice keeps the counts and does not delete the tables or the conversation records;
- `PRAGMA foreign_key_check` returns empty;
- `payment_method` is split: `credit_6x` becomes `payment_type=credit` and `installments=6`; PIX, debit and boleto keep NULL instalments;
- `total_needs_review = 1` on orders 3 and 20 and 0 on the others, compared with a 0.01 tolerance;
- `description_raw` is stored and `specs_json` holds valid JSON in every row;
- dates are stored as ISO text;
- `conversations` includes `summary` and `summarized_until_message_id`;
- the build prints anomalies for products 96, 136 and 130 and reports products with multiple active promotions;
- `tests/test_data.py` validates the items above.

## Step 2 — Connections and database security

- [x] `conn_leitura()` opens the database with `mode=ro` and blocks INSERT, UPDATE and DELETE;
- [x] `conn_escrita()` is imported only by `memory.py`;
- [x] the authorizer blocks reading `products.description_raw` and `customers.phone`;
- [x] `customers.email` remains readable for identity verification;
- [x] `PRAGMA foreign_keys = ON` is enabled on the read and write connections;
- [x] `tests/test_security.py` covers the criteria above.

Suggested commit: `feat(db): read/write connections and authorizer`

## Step 3 — Configuration and store hours

- [x] `carregar_configuracao()` loads provider, fallback and keys from the environment, and reports a clear error if a required key is missing;
- [x] `agora()` uses `REFERENCE_DATETIME` or the system clock, always in `America/Campo_Grande`; `hoje()` derives the date from `agora()`;
- [x] an invalid time reference fails with a clear message; `.env.example` defines `2026-03-23T10:00:00`;
- [x] `loja_aberta(agora)` applies Monday to Friday 09:00–18:00, Saturday 09:00–13:00 and Sunday closed; holidays are not modelled;
- [x] `date.today()` and `datetime.now()` are used only in `config.py`;
- [x] the configuration tests cover loading, time zones, validation and opening-hour limits.

## Step 4 — Schemas and product tools

- [x] search and detail arguments are validated with Pydantic, including `preco_max > 0`;
- [x] queries list the columns explicitly and never read or return `description_raw`;
- [x] returned specs are limited to strings, electronics, scale and colour, and are omitted for products 135 to 144;
- [x] a search for acoustic guitars up to R$ 1,000 returns the 12 available ones and excludes products 96 and 113;
- [x] a search for `gd20`, `GD-20` and `takamine gd20` finds product 95;
- [x] details correctly report unavailability, removal from the catalogue, coming-soon products and discontinuation;
- [x] a search with no results returns a structured answer;
- [x] results are limited without losing the real total found;
- [x] `tests/test_tools.py` validates the product criteria above.

Suggested commit: `feat(tools): product search and details`

## Step 5 — Promotions and final price

- [x] only promotions with `is_active = 1` and an existing product are considered;
- [x] promotional prices are rounded to two decimals and use the larger discount without stacking;
- [x] without a promotion, product 95 keeps the price of R$ 2,199.00 and has a PIX price of R$ 2,089.05;
- [x] with a promotion, the PIX value gets no additional discount;
- [x] inactive promotions do not appear, including those of product 96;
- [x] the `build_db` report identifies products with multiple active promotions;
- [x] `tests/test_tools.py` validates real prices and the synthetic duplicated-promotion case.

Suggested commit: `feat(tools): promotions and final price calculation`

## Step 6 — Orders and identity

- [x] `verificar_cliente` compares e-mail ignoring case and spaces, and records the `customer_id` only in the conversation;
- [x] a nonexistent order and a wrong e-mail return the same answer;
- [x] invalid attempts are persisted per conversation and blocked after three attempts;
- [x] `status_pedido` receives the `conversa_id` as internal context, does not accept `customer_id` from the model, and restricts orders to the verified customer;
- [x] answers include status, date, items, payment, tracking and estimate, without phone or e-mail;
- [x] orders 3 and 20 hide the value when `total_needs_review` is active;
- [x] the delay of order 8 is computed with `hoje()` and `REFERENCE_DATETIME`;
- [x] cancellations report the reason; pending/confirmed orders without tracking report that they have not been dispatched yet;
- [x] `tests/test_security.py` covers verification, per-conversation limit, authorisation and privacy.

Suggested commit: `feat(tools): customer verification and order status`

## Step 7 — LLM provider and fallback

- [x] `llm.py` encapsulates the selected provider and produces the `ModelCallable` interface used by the agent;
- [x] Gemini Flash-Lite uses `gemini-3.5-flash-lite` and Groq uses `openai/gpt-oss-120b`, both with configurable models;
- [x] `openai` package clients use each provider's specific `base_url`;
- [x] an explicit tool-calling incompatibility error on the Gemini endpoint moves only that call to the native SDK;
- [x] fallback happens on 404, 429, timeout and 5xx; 400/401 errors do not try the backup;
- [x] logs record the provider and the error category without including credentials;
- [x] tests simulate answers, function calling, native migration and transient errors without external calls.

At the time of this step no real request had been made in the implementation; endpoint compatibility and credentials still needed a controlled real call (later partial real runs are in the AI usage log).

Suggested commit: `feat(llm): Gemini Groq integration and fallback`

## Step 8 — Memory system and history

- [x] `memory.py` creates conversations and persists messages, provider and tool calls in SQLite;
- [x] retrieval is isolated by conversation identifier and does not return tool arguments; recognisable e-mail/phone in messages and arguments are redacted;
- [x] beyond 20 unsummarised messages, it produces a summary through an injectable callback, keeps the 10 most recent messages in full and records `summary` and `summarized_until_message_id`;
- [x] a summariser failure preserves all original messages; successive summaries incorporate the previous summary.

The callback is connected to the provider through the model configured in the agent. The original messages are not deleted.

Suggested commit: `feat(memory): history persistence and summarisation`

## Step 9 — Prompts and persona

- [x] `prompts.py` organises persona, business rules, out-of-scope handling and the expected format;
- [x] tools are kept separate from the messages; the static persona-and-manual prefix comes before the summary, the history and the current message;
- [x] the summary is presented as context, not as instructions; recent history and the current message keep their order;
- [x] instalment questions instruct the model to call `simular_parcelamento`, without computing instalments mentally.

Suggested commit: `feat(prompts): persona and agent context`

## Step 10 — Intent classifier

- [x] `classificar_intencao(msg)` returns a deterministic list with zero or more labels;
- [x] taxonomy limited to `dado_loja`, `politica`, `acessorio`, `fora_assunto` and `saudacao`; it does not create `misto`;
- [x] rules are evaluated first; the optional LLM callback is called only when no rule classifies, and without a callback it returns `[]`;
- [x] a greeting may coexist with the main intent; an accessory request returns `acessorio` and `fora_assunto`;
- [x] the illustrative store list and the redirection guidance stay in the configuration/documentation and in the prompt, without claiming a real partnership.

Suggested commit: `feat(intent): multi-label rule-based classifier`

## Step 11 — Main agent loop

- [x] `agent.py` runs the message → model → tools → final answer loop through an injectable model;
- [x] all six tools have a JSON Schema definition and a dispatcher with Pydantic validation; `conversa_id` is injected internally into the order tools and is not a model argument;
- [x] known tool errors return safe structures to the model and are recorded; persisted arguments go through the memory redaction;
- [x] limits calls to five tool rounds; allows one final call without tools and uses a safe answer if there is no valid text or the model tries another tool;
- [x] history is persisted and summarised before building the context, when applicable.

The loop can be tested with an injected model function, without keys or external requests; if none is injected, it uses the Gemini/Groq configuration from Step 7.

Suggested commit: `feat(agent): main loop and function calling`

## Step 12 — CLI and interface

- [x] `cli.py` reads the `--conversa ID` and `--debug` options;
- [x] the interactive CLI keeps the same conversation ID across messages and calls `agent.responder_mensagem()`;
- [x] answers are printed as text; `/sair`, EOF and Ctrl+C end the session;
- [x] nonexistent conversations and agent failures are reported clearly;
- [x] tests cover a new and a resumed conversation, multiple messages, debug and a missing/invalid provider configuration.

Input is one line per message; there is no `Shift+Enter` support in this simple CLI.

Suggested commit: `feat(cli): interactive customer-service interface`

## Step 14 — Examples and usage documentation

Acceptance criteria:
- `examples/` has real and objective conversation scenarios (3 to 5 complete conversations, at least one involving real-time data or applying a policy);
- the README explains how to run and how to check the answers.

## Step 15 — LLM scenario tests

Acceptance criteria:
- `tests/test_scenarios.py` covers catalogue, order and out-of-scope scenarios;
- LLM tests are marked `@pytest.mark.llm` and skipped by default.

## Step 16 — Final review and compliance

Acceptance criteria:
- [x] local security and behaviour checks approved by the deterministic suite;
- [x] documentation of the flow reviewed to match the implemented behaviour;
- [x] project ready to move on to the next implementation stage.

Review result: the local suite had 189 tests passed and 25 skipped. The redaction of e-mails and phone numbers in memory was checked and extended to continuous national phone numbers of 10 to 13 digits. At the time of this review the real-LLM scenarios, which are opt-in, had not been executed (later partial runs are in the AI usage log); provider compatibility, contacts and other external data still require validation before commercial use. The `orders.notes` field is sent as the cancellation reason; the current database contains only operational reasons, but real data in this column must be filtered before it is sent to the model.

## Step 17 — Delivery and review

Acceptance criteria:
- README, architecture and decisions finalised;
- repository ready, with a public history of incremental commits.

## Step 18 — Classifier with scikit-learn (later and optional)

Acceptance criteria:
- train and evaluate TF-IDF + logistic regression or LinearSVC with phrases written by the user;
- compare with rules + LLM on the same test set, including accuracy, typical errors and latency;
- record only metrics that were actually measured;
- keep the multi-label interface of `classificar_intencao(msg)`.
