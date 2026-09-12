# Personal AI Content System - Backend Technical Report

## 1. Executive Summary

This backend is a FastAPI service for turning a topic into platform-specific social-media content. It can ingest the user's documents, embed and retrieve relevant chunks as personal knowledge, optionally search the web, ask Gemini to generate ideas and a post, evaluate the post, persist drafts, pause for human review, persist approval, optionally generate media, and expose publishing/history endpoints.

The main architecture is:

- FastAPI HTTP routes in `app/api`.
- A LangGraph `StateGraph` in `app/graphs/content_graph.py`.
- A `TypedDict` workflow state in `app/graphs/content_state.py`.
- Gemini chat and embedding clients through LangChain in `app/core/llm.py` and `app/services/embedding_service.py`.
- SQLite application data in `content.db`.
- A separate SQLite LangGraph checkpoint database in `content_engine_checkpoints.db`.
- Tavily web search, Google/Gemini media calls, a Cloudflare Worker image endpoint, and X/LinkedIn publishing HTTP APIs.

A request enters through `/api/content/generate` or `/api/ideas`, both of which invoke the same compiled global graph. The graph retrieves personal knowledge, makes a deterministic research decision, optionally searches Tavily, generates five structured ideas with Gemini, saves them, selects the first idea, generates and evaluates content, refines it up to two times when the score is below 8, saves a draft, and pauses at a LangGraph interrupt for human review. A separate review request resumes the checkpoint. Approval updates the generated-content row. Image/audio routing then reads state flags; the current API does not set those flags, so normal requests skip both media branches and reach `END`.

**Backend in one paragraph:** The service is a FastAPI wrapper around a LangGraph content pipeline. SQLite stores documents, embeddings, ideas, generated posts, media references, social accounts, and graph checkpoints. Gemini supplies structured idea generation, post generation, evaluation, query generation, image-prompt generation, and embeddings. Tavily supplies optional web research. Human review is implemented with a LangGraph interrupt and checkpoint resume. Publishing is a separate HTTP endpoint that reads approved content and stored social-account credentials, then calls X or LinkedIn. The source contains the full intended path, but several parts are only partially wired: media flags are never populated by the main request, the review endpoint is misspelled, and some error/data contracts are weak.

## 2. Project Structure

| File/Folder | Purpose | Important Components | Used By |
|---|---|---|---|
| `main.py` | FastAPI application entrypoint | lifespan, `init_db`, CORS, router registration, `/health` | Uvicorn/deployment |
| `app/api/routes.py` | Main content and knowledge API | `/content/generate`, `/ideas`, upload/list/history/detail routes | `main.py` |
| `app/api/content_review.py` | Human-review resume API | `ReviewRequest`, `/reveiw`, `Command(resume=...)` | `main.py`, LangGraph checkpoint |
| `app/api/publish.py` | Publication API | `/publish`, approval/idempotency checks, publication status updates | `main.py` |
| `app/graphs/content_graph.py` | Workflow definition | nodes, edges, routers, checkpoint compilation | API routes, tests |
| `app/graphs/content_state.py` | Workflow state contract | `ContentState` TypedDict | every graph node |
| `app/graphs/content_nodes.py` | Core workflow node functions | retrieval, research, ideas, generation, evaluation, refinement, saves | `content_graph.py` |
| `app/graphs/human_reveiw.py` | Human-review nodes | interrupt, finalization, approval persistence | `content_graph.py` |
| `app/graphs/media_nodes.py` | Media nodes and routers | image/audio generation and skip nodes | `content_graph.py` |
| `app/graphs/publishing_nodes.py` | Separate publishing graph node | `publish_content_node` | no graph/API import found |
| `app/core/llm.py` | Gemini chat client | `ChatGoogleGenerativeAI`, `gemini-3.5-flash` | graph/services |
| `app/core/social_config.py` | Social configuration | X/LinkedIn OAuth variables and defaults | publishing/config checks |
| `app/db/database.py` | SQLite schema and CRUD | `content.db`, tables, idea/document/chunk operations | services/API |
| `app/db/migrations.py` | Standalone migration script | adds publishing columns | not imported by `main.py` |
| `app/db/checkpointer.py` | LangGraph persistence | `SqliteSaver` on checkpoint DB | `content_graph.py` |
| `app/models/content.py` | Pydantic LLM schemas | idea, idea-list, generated content, evaluation | LLM structured output |
| `app/services/document_service.py` | Document extraction/ingestion | PDF/text extraction, chunking, embedding persistence | upload route |
| `app/services/embedding_service.py` | Google embeddings | query/document embedding wrappers | ingestion/retrieval |
| `app/services/retrieval_service.py` | Personal knowledge retrieval | full-table scan, cosine similarity, top-k | retrieval node |
| `app/services/content_service.py` | Idea persistence wrapper | saves each idea | save-ideas node |
| `app/services/content_generation_service.py` | Post generation/evaluation | prompts and structured Gemini calls | generation/evaluation/refinement nodes |
| `app/services/generated_content_service.py` | Generated-post CRUD | insert draft, approve/update, fetch | graph/API |
| `app/services/media_prompt_service.py` | Image prompt generation | Gemini text call | image node |
| `app/services/image_service.py` | Image provider wrapper | Cloudflare path by default, optional Gemini path | image node |
| `app/services/audio_service.py` | Audio provider wrapper | Gemini media call wrapper | audio node |
| `app/services/media_service.py` | Media persistence | inserts `content_media` rows | media nodes |
| `app/services/publishing_service.py` | Platform dispatch | X vs LinkedIn selection | publish API/unused graph node |
| `app/services/publication_service.py` | Publication status CRUD | publishing/published/failed transitions | publish API |
| `app/services/social_account_service.py` | Social-account CRUD helpers | save/get account; OAuth state placeholders | publish API |
| `app/services/x_service.py` | X HTTP client | `POST https://api.x.com/2/tweets` | publishing service |
| `app/services/linkedin_service.py` | LinkedIn HTTP client | `POST https://api.linkedin.com/rest/posts` | publishing service |
| `app/tools/web_search.py` | Tavily LangChain tool | advanced search, five result mapping | research node |
| `app/tools/image_generate.py` | Image provider implementations | Cloudflare Worker and optional Gemini image interaction | image service |
| `app/tools/audio_generate.py` | Gemini audio implementation | `Kore` voice, WAV writing | audio service |
| `app/tests` / `tests` | Tests and learning examples | graph invocation, review resume, retrieval script | development only |

The dependency direction is API -> graph/services -> database or external provider. The graph is the orchestration layer; services perform persistence or provider calls. The publishing graph node is not wired into the main graph and the social OAuth configuration has no corresponding OAuth API routes.

## 3. Application Entry Point

The application starts in `main.py` with the module-level `app = FastAPI(...)`. A Uvicorn command is not included in the repository, so the exact deployment command is not defined here.

Initialization details:

1. `main.py` imports `init_db` and all three routers.
2. Importing the graph route modules imports the global `graph` from `app.graphs.content_graph`, which builds and compiles the graph at import time.
3. The FastAPI lifespan function prints startup text, calls `init_db()`, yields, then prints shutdown text. It has no explicit cleanup of clients or databases.
4. `init_db()` creates or migrates `content.db` using SQLite.
5. CORS allows four localhost origins on ports 5173 and 4173, credentials, all methods, and all headers.
6. Routers are included with prefix `/api`:
   - `routes.router` becomes the main `/api/...` routes.
   - `content_review.router` becomes `/api/reveiw`.
   - `publish.router` already has its own `/api` prefix, so inclusion adds another prefix and makes the publication path `/api/api/publish`.
7. No authentication middleware, request-ID middleware, custom exception handlers, or dependency injection providers are registered.
8. `load_dotenv()` is called in several modules. The LLM and Tavily clients are created as module globals during import.

The health endpoint is `GET /health` and returns a static JSON status. The main content request is handled synchronously by `generate_content()` or `generate_ideas()`, which construct a deterministic thread ID from topic/platform and call `graph.invoke(...)`.

## 4. API Layer

### Main content routes

| Method | Actual route | Input/validation | Handler and downstream behavior | Response/errors |
|---|---|---|---|---|
| POST | `/api/content/generate` | JSON `IdeaRequest`: `topic`, `platform`, `content_type`, all plain `str` fields | `generate_content()` creates `content-{topic}-{platform}` thread ID and invokes the graph with topic/platform/content type/empty ideas | Returns thread ID, content ID, selected idea, final/generated content, score, refinement count, `requires_review`, and interrupt payload. Unhandled graph/LLM/DB errors become framework errors. |
| POST | `/api/ideas` | Same `IdeaRequest` | `generate_ideas()` invokes the entire graph, not only the idea portion | Returns topic/platform/content type, research flag/results, and ideas. The graph still proceeds into generation, evaluation, persistence, and human interrupt. |
| POST | `/api/knowledge/upload` | Multipart `file`; extension must be `.pdf`, `.txt`, or `.md` | Reads upload to a temporary file, calls `ingest_document()`, deletes the temp file in `finally` | Unsupported extension returns an error object with normal 200 behavior. Extraction/embedding/DB errors propagate; cleanup is attempted. |
| GET | `/api/knowledge` | None | Intended to call DB `list_knowledge()` | Due to a same-name local handler shadowing the imported function, the handler calls itself recursively until `RecursionError`, then returns `{"error": ...}`. |
| GET | `/api/content/history` | None | Direct SQLite query of `generated_content`, newest first | Returns `{"items": [...]}`. DB exceptions are not caught. |
| GET | `/api/content/{content_id}` | Path integer | Direct SQLite query for one generated-content row | Returns row dict or `{"error":"Content not found"}`. DB exceptions are not caught. |
| POST | `/api/reveiw` | JSON `ReviewRequest`: thread ID, literal action `approve`/`edit`, optional content | Resumes graph with `Command(resume=...)` using the supplied thread ID | Returns graph result. Empty edit is returned as an error object with 200 status. Other exceptions are also converted to `{"message": ...}` with 200 status. The spelling is `reveiw`. |
| POST | `/api/api/publish` | JSON `PublishRequest`: integer `content_id`, literal `X`/`LinkedIn` | Fetches content, verifies approval, checks `can_publish`, gets account, marks publishing, calls platform API, persists success/failure | Uses `HTTPException` for not found, not approved, duplicate/unavailable publication, missing account, and provider failure. |
| GET | `/health` | None | `health_check()` | Static success response. |

The effective request path is:

```text
CLIENT
  -> FastAPI route
  -> graph.invoke (generation/ideas) or service calls (history/publish)
  -> LangGraph nodes
  -> Gemini/Tavily/Google embeddings/Cloudflare/X/LinkedIn and SQLite
  -> JSON response or LangGraph interrupt response
```

The `IdeaRequest` does not validate content type or platform against the `Literal` types defined in `app/models/content.py`; it accepts arbitrary strings at the API boundary.

## 5. Agent/Graph Architecture

### Graph definition

`build_content_graph()` in `app/graphs/content_graph.py` creates `StateGraph(ContentState)`, registers 19 nodes, adds the edges below, and compiles with the global `SqliteSaver` checkpointer.

```text
START
  -> retrieve_personal_knowledge
  -> decide_research
       -> generate_research_query -> research -> generate_content_ideas
       -> generate_content_ideas
  -> quality_check
  -> save_ideas_node
  -> generate_content
  -> evaluate_content
       -> refine_content -> evaluate_content
       -> save_generated_content
  -> human_review [interrupt]
  -> finalize_human_review
  -> save_approval
       -> generate_image -> audio_decision
       -> image_skipped -> audio_decision
  -> audio_decision
       -> generate_audio -> END
       -> audio_skipped -> END
```

The current source contains no broken `image_decison_after_skip` edge; that claim in the older `report.md` does not describe the current file. The graph has no explicit graph-level error handlers or retry policies.

### Node table

| Node | Function | Reads state | Modifies state | External calls | DB operations | Next node |
|---|---|---|---|---|---|---|
| `retrieve_personal_knowledge` | `retrieve_personal_knowledge` in `content_nodes.py` | `topic` | `retrieved_context` | Google embedding query | Reads all `document_chunks` | `decide_research` |
| `decide_research` | `decide_research` | `topic`, `content_type` | `research_required`, `research_query` | None | None | Router to research or ideas |
| `generate_research_query` | `generate_research_query` | `topic`, `content_type` | `research_query` | Gemini chat call | None | `research` |
| `research` | `research_topic` | `research_query` | `research_results` | Tavily advanced search | None | `generate_content_ideas` |
| `generate_content_ideas` | `generate_content_ideas` | topic/platform/type, retrieved context, research results | `ideas` | Gemini structured output `ContentIdeas` | None | `quality_check` |
| `quality_check` | `quality_check` | `ideas` | filtered `ideas` | None | None | `save_ideas_node` |
| `save_ideas_node` | `save_ideas_node` | topic, ideas | `saved_ids` | None | Inserts `content_ideas` rows | `generate_content` |
| `generate_content` | `generate_content_node` | ideas, platform/type, retrieval/research context | `selected_idea`, `generated_content`, `refinement_count=0` | Gemini structured output `GeneratedContent` through service | None | `evaluate_content` |
| `evaluate_content` | `evaluate_content_node` | generated content, platform/type | `quality_score`, `quality_feedback` | Gemini structured output `ContentEvaluation` | None | Router to refine or save |
| `refine_content` | `refine_content_node` | selected idea, contexts, feedback, refinement count | replacement `generated_content`, incremented `refinement_count` | Gemini structured content generation | None | `evaluate_content` |
| `save_generated_content` | `save_generated_content_node` | selected idea, generated content, score | `final_content`, `content_id` | None | Inserts draft `generated_content` row | `human_review` |
| `human_review` | `human_review_node` | content ID, platform/type, generated content, score | On resume: human action/edit/status | LangGraph `interrupt()` | None | Pauses; on resume `finalize_human_review` |
| `finalize_human_review` | `finalize_human_review_node` | human action, edited content, generated content | `final_content`, approval status | None | None | `save_approval` |
| `save_approval` | `save_approval_node` | content ID, final content | approval status | None | Updates content, status, approved timestamp | `image_router` |
| `generate_image` | `generate_image_node` | final content, platform, content ID | `image_url` | Gemini prompt call, Cloudflare Worker by default or optional Gemini image API | Inserts `content_media` image row | `audio_decision` |
| `image_skipped` | `image_skipped_node` | None | No state update (`{}`) | None | None | `audio_decision` |
| `audio_decision` | `_audio_decision_node` | No fields | Returns state unchanged | None | None | `audio_router` |
| `generate_audio` | `generate_audio_node` | final content, content ID | `audio_url` | Google Gemini interaction API if model configured | Inserts `content_media` audio row | `END` |
| `audio_skipped` | `audio_skipped_node` | None | No state update (`{}`) | None | None | `END` |

The separate `publish_content_node` in `publishing_nodes.py` is not registered in `content_graph.py`; it is extra implementation absent from the active graph.

### Routing and loops

- `research_router` reads `research_required`; `True` maps to `generate_research_query`, otherwise to `generate_content_ideas`.
- `content_quality_router` approves at score >= 8, or forcibly approves when `refinement_count >= 2`; otherwise it refines. It does not inspect `ContentEvaluation.should_refine`.
- `image_router` reads `image_requested`; false skips image.
- `audio_router` reads `audio_requested`; false skips audio.
- `media_router` exists in `media_nodes.py` but is not used by the graph.
- There is a bounded maximum of two refinement calls because count 2 routes to approval. There is no general retry policy for provider failures.
- Human review is the only explicit pause. The compiled graph uses SQLite checkpoint persistence, allowing a later `Command(resume=...)` call with the same thread ID.

## 6. State Management

The state type is `ContentState`, a `TypedDict` without `NotRequired` annotations. It describes fields but does not itself enforce runtime presence when the initial dictionary is passed to LangGraph.

| State field | Type | Created by | Modified by | Used by | Purpose |
|---|---|---|---|---|---|
| `topic` | `str` | API input | none in graph | retrieval, research, ideas | User subject |
| `platform` | `str` | API input | none | ideas, generation, review, media | Target platform |
| `content_type` | `str` | API input | none | research, ideas, generation, review | Content category |
| `saved_ids` | `list` | `save_ideas_node` | save ideas | response/state | Idea row IDs |
| `ideas` | `list[str]` annotation | API starts `[]`; idea node replaces | idea generation, quality check | generation/API | Structured `ContentIdea` objects in practice |
| `retrieved_context` | `list` | retrieval node | retrieval | idea/content generation | Relevant document chunks |
| `research_required` | `bool` | decision node | decision | research router/API | Research branch flag |
| `research_query` | `str` | decision/query node | both | research tool | Search query |
| `research_results` | `list` | research node | research | ideas/content generation/API | Tavily result dicts |
| `selected_idea` | `dict` annotation | generation node | generation | refinement/save/review | First idea only |
| `generated_content` | `str` | generation/refinement | both | evaluation/save/review | Current generated post |
| `quality_score` | `int` | evaluation | evaluation | router/save/response/review | 1-10 evaluator score |
| `quality_feedback` | `str` | evaluation | evaluation | refinement | Evaluator feedback |
| `refinement_count` | `int` | initial generation | refinement | router/response | Number of refinements |
| `final_content` | `str` | save draft/finalize | both | approval/media/API | Content after human review |
| `content_id` | `int` | save draft | save draft | review/approval/media/response | Generated row ID |
| `human_action` | `str` | resumed review | review node | finalization | `approve` or `edit` |
| `human_feedback` | `str` | none in current nodes | none | none | Declared but unused |
| `edited_content` | `str` | edit resume | review node | finalization | Human replacement text |
| `approval_status` | `str` | review/finalize/save | review nodes | response/media context | Current approval marker |
| `media_requested` | `bool` | none | none | no active node | Declared but unused |
| `image_requested` | `bool` | none in API/graph | none | image router | Controls image branch; absent defaults false |
| `audio_requested` | `bool` | none in API/graph | none | audio router | Controls audio branch; absent defaults false |
| `image_url` | `str` | image node | image node | final result if reached | Returned image path/string |
| `audio_url` | `str` | audio node | audio node | final result if reached | Returned audio path/string |

The initial API state supplies only `topic`, `platform`, `content_type`, and `ideas`. Nodes use `.get()` for many optional fields, while direct indexing is used for required inputs. State is carried forward by LangGraph merge semantics; node return dictionaries generally contain only changed fields, although several early nodes copy the whole state with `{**state, ...}`.

State is checkpointed by LangGraph in `content_engine_checkpoints.db` under the configured thread ID. It is not stored as a reusable application record in `content.db`. The generated content and related records do survive separately in `content.db`. The content API's deterministic thread IDs can cause repeated equivalent requests to share a checkpoint identity.

Lifecycle: request input -> personal retrieval -> research decision/results -> ideas -> filtered/saved ideas -> first idea generation -> evaluator loop -> draft row -> interrupt checkpoint -> resume with approve/edit -> final content update and approval -> optional media -> END.

## 7. Personal Knowledge System

Knowledge ingestion begins at `POST /api/knowledge/upload`:

1. The route accepts PDF, TXT, or Markdown extensions.
2. `document_service.extract_text()` uses `pypdf.PdfReader` for PDFs and UTF-8 `Path.read_text()` for TXT/MD.
3. `RecursiveCharacterTextSplitter` creates chunks of 800 characters with 100-character overlap.
4. `create_document()` inserts a `documents` row.
5. `embed_documents()` calls `GoogleGenerativeAIEmbeddings(model="gemini-embedding-2")`.
6. Each chunk and JSON-serialized embedding is inserted into `document_chunks`.

`retrieve_personal_knowledge()` calls `retrieve_relevant_chunks(topic, top_k=5)`. Retrieval embeds the topic, selects every row from `document_chunks`, deserializes each embedding, calculates cosine similarity in Python, removes results below `0.35`, sorts descending, and returns five results. There is no vector database or SQL vector index.

The retrieval result contains both `chunk_text` and duplicate `text` keys. Idea generation uses `text`; content generation accepts either `chunk_text` or `text`. Retrieved text is inserted into the idea and post prompts under `PERSONAL KNOWLEDGE`. No document/chunk source metadata is included in the generated-content row.

If there are no documents or no results above threshold, the graph continues with an empty personal context. Embedding/provider/database errors stop the graph because retrieval has no local fallback or catch block.

## 8. Research Pipeline

`decide_research()` is deterministic, not LLM-based:

- `ai_news` -> research required.
- `build_in_public` -> research skipped.
- `technical` and `opinion` -> research required.
- Any other value -> research skipped.

When required, the decision initially sets `research_query` to the topic. The graph then calls `generate_research_query()`, which asks the Gemini chat model for one concise current-information query and assumes `response.content[0]["text"]` is the text. That generated query replaces the topic query.

`research_topic()` invokes the LangChain `web_search` tool. The tool calls `TavilyClient.search(query, search_depth="advanced", max_results=5)` and maps each result to title, URL, and content. Results are kept only in `research_results`; they are not persisted in SQLite.

Idea generation joins research result `content` values and instructs Gemini to use web research for current/factual claims and preserve source URLs in relevant claims. Post generation includes title, URL, and content in its prompt. Search exceptions propagate and stop execution. When research is skipped, `research_results` remains absent/empty and prompts contain an empty research section.

## 9. Content Idea Generation and Quality Check

`generate_content_ideas()` creates a structured Gemini client with `llm.with_structured_output(ContentIdeas)`. Its prompt includes personal context, research context, topic, platform, content type, and the fixed focus areas of AI engineering, agents, machine learning, public project building, technical explanations, opinions, and industry developments. It requests five ideas, each with title, angle, and reason, and receives a Pydantic `ContentIdeas` object containing `ContentIdea` objects.

`ContentIdea` also requires `content_type` and `platform` literals, so structured output validation checks those fields as well. The API input itself is not validated against those literals. The node returns `result.ideas` without a count check beyond whatever the LLM/parser returns.

`quality_check()` is deterministic field presence/content validation only. It removes ideas whose title, angle, or reason is blank after stripping whitespace. It does not call an LLM, check duplicates, calculate relevance, score quality, or verify sources. It does not explicitly check the idea's platform/content type.

If all ideas are filtered out, `save_ideas_node` saves no ideas and `generate_content_node` raises `ValueError("No content ideas available.")`, stopping the graph.

## 10. Database

The application database is SQLite at the relative path `content.db`. The checkpoint database is a separate SQLite file at `content_engine_checkpoints.db`. There are no explicit non-primary-key indexes; `social_accounts.platform` is unique.

| Table | Purpose | Important fields | Created by | Read by | Updated by |
|---|---|---|---|---|---|
| `content_ideas` | Saved generated ideas | id, topic, title, angle, platform, created_at | `save_ideas_node` -> `save_content_ideas` | No active detail route; linked by generated content | None |
| `documents` | Uploaded knowledge inventory | id, filename, file_type, created_at | document ingestion | `list_knowledge` DB function | None |
| `document_chunks` | Chunk text and JSON embeddings | id, document_id, chunk_text, embedding, created_at | document ingestion | retrieval full scan | None |
| `generated_content` | Draft/approved/publishable posts | id, idea_id, platform, content_type, content, quality_score, status, approval/publish fields | save-generated node | history, detail, publishing | review approval and publication status services |
| `content_media` | Media references | id, content_id, media_type, media_url, created_at | image/audio nodes | No active read route | None |
| `social_accounts` | Stored platform credentials/account metadata | platform, account_id, account_name, access_token, refresh_token, expiry | `save_social_account` helper | `get_social_account` | upsert helper |

`init_db()` calls `_initialize_schema()` at startup. That function creates all six tables with `IF NOT EXISTS`, enables foreign keys on that connection, and includes publishing columns in the initial `generated_content` definition. Its migration checks add missing publishing columns for an older table. `get_connection()` repeats schema/migration checks when opening a connection.

The standalone `app/db/migrations.py` uses the same `content.db` path but assumes `generated_content` already exists. It is not called by `main.py`; `_initialize_schema()` is the effective bootstrap/migration path.

Application data is committed immediately in each CRUD helper. There are no multi-table transactions spanning workflow steps, so a later graph failure can leave saved ideas or a draft row behind. Foreign keys are enabled on connections, but the schema does not define cascade actions.

## 11. Content Generation

`generate_content_node()` rejects an empty idea list, selects `ideas[0]`, converts the Pydantic idea with `model_dump()`, and calls the `generate_content()` service. The service builds a prompt containing platform, content type, title, angle, reason, personal knowledge, and research source/title/URL/content. It instructs the Gemini model to write a final X or LinkedIn post, follow platform-specific style, avoid invented experiences, use research for factual claims, and return only post content.

The service uses `llm.with_structured_output(GeneratedContent)` and returns `result.content`. The configured chat model is `gemini-3.5-flash` with temperature `0.7`. No explicit token limit, timeout, retry, or model fallback is configured in the code.

The node returns the selected structured idea, generated content, and `refinement_count=0`. Unlike the idea list, the generated post is a complete platform-formatted draft. Provider/parser exceptions propagate.

## 12. Content Evaluation and Refinement Loop

`evaluate_content_node()` calls the evaluation service with the current generated text, platform, and content type. The service asks Gemini to assess clarity, usefulness, originality, hook, platform suitability, human-sounding writing, and factual reliability. It requests a score from 1 to 10, feedback, and `should_refine`, validated by `ContentEvaluation`.

The actual router ignores `should_refine`. It uses only the numeric score and count:

```text
score >= 8             -> approved
score < 8 and count < 2 -> refine
count >= 2             -> approved
```

`refine_content_node()` appends the previous evaluator feedback to the idea angle, calls the same generation service again, replaces `generated_content`, and increments the count. The loop therefore permits at most two refinement passes, after which the content is approved regardless of score. There is no infinite loop under the current router. Evaluation/provider/parser failures stop the graph; there is no retry or fallback. Approved content proceeds to `save_generated_content_node()`.

## 13. Human-in-the-Loop

`save_generated_content_node()` inserts the generated post as a `generated_content` row with default status `draft`, then stores the row ID and final content in state.

`human_review_node()` constructs an interrupt payload containing review type, content ID, platform, content type, generated content, quality score, and an instruction. `interrupt(review_request)` pauses the graph and persists the checkpoint using the graph's thread ID. The initial content-generation route exposes the interrupt via `requires_review` and `interrupt` in its response.

The resume route is `POST /api/reveiw` (misspelled). Its `ReviewRequest` requires the original `thread_id` and action `approve` or `edit`. It correctly uses the supplied thread ID in `config` and invokes `Command(resume=...)`. For edit, the route and node require nonempty content. The node accepts only approve/edit; any other resumed payload raises `ValueError`.

On approve, the node sets `human_action=approve` and approval status. On edit, it sets `human_action=edit`, stores `edited_content`, and approval status. There is no rejection state, reject route, or human feedback field handling. `finalize_human_review_node()` chooses edited content for edit, otherwise the original generated content. `save_approval_node()` requires content ID and final content, updates the row content, status `approved`, and `approved_at` using `datetime.utcnow().isoformat()`.

No-response behavior is simply a paused checkpoint; no timeout or expiry handling exists. Review route exceptions are converted to JSON messages without HTTP error status. A successful resume returns the graph result, which should continue through media routing and `END`.

## 14. Image Generation

The image branch is selected only when `state.get("image_requested", False)` is true. The normal generation request does not accept or set an image flag, and no graph node sets it, so the normal path reaches `image_skipped`.

If reached, `generate_image_node()` requires `final_content`, calls `generate_image_prompt()` to ask Gemini for a visual prompt, then calls `image_service.generate_image()` and inserts the returned value into `content_media` with `media_type="image"`.

`image_service.py` has `USE_GEMINI=False`, so it uses `generate_with_cloud()` by default. That function posts the prompt to `https://zubaimage.ibrahimalaaya7.workers.dev/` with a bearer value from `CLOUDFLARE_SCERET`, writes successful response bytes to a UUID `.jpg` file, and returns the local path. If the request fails, the tool returns an error string; the service also returns an error string on exceptions rather than raising. The image node consequently may persist an error string as `media_url`. The optional Gemini path uses `IMAGE_MODEL` and `GOOGLE_API_KEY` but is disabled by the constant.

There is no API for downloading/serving generated media and no media read endpoint. The database stores a path/string, not the binary image.

## 15. Audio Generation

The audio branch is selected only when `audio_requested` is true. No current request or node populates that flag, so normal executions skip audio.

If reached, `generate_audio_node()` requires final content, calls `audio_service.generate_audio(content)`, saves the result in `content_media` as audio, and returns `audio_url`.

`audio_service.py` reads `AUDIO_MODEL`, defaulting to an empty string. With no model configured it returns the literal placeholder `audio_not_configured`. With a model, `tools/audio_generate.py` calls the Google GenAI interactions API with `response_format={"type":"audio"}` and voice `Kore`, decodes the returned audio, writes a UUID `.wav` file, and returns the result of `wave_file()`. `wave_file()` does not return the filename, so that path currently evaluates to `None`; the media row can therefore have a null URL. Provider exceptions are converted to an error string by the service. There is no media serving endpoint.

## 16. External Services and APIs

| Service | Purpose | Called from | Authentication | Data sent | Data received |
|---|---|---|---|---|---|
| Google Gemini chat | Ideas, query, posts, evaluation, image prompts | `llm.py`, content/media prompt services | `GOOGLE_API_KEY` | Topic, context, research, prompts, content | Text or structured Pydantic results |
| Google Gemini embeddings | Knowledge indexing/retrieval | `embedding_service.py` | Environment-backed Google credentials/client configuration | Document chunks or query | Vectors |
| Tavily | Current web research | `tools/web_search.py` | `TAVILY_API_KEY` | Search query | Up to five mapped results |
| Cloudflare Worker | Default image generation proxy | `tools/image_generate.py` | Bearer `CLOUDFLARE_SCERET` | Image prompt | Image bytes |
| Google GenAI image interaction | Optional image generation | `tools/image_generate.py` | `GOOGLE_API_KEY` | Prompt/model | Base64 image data |
| Google GenAI audio interaction | TTS/audio | `tools/audio_generate.py` | `GOOGLE_API_KEY` | Final post text/model/voice config | Base64 audio data |
| X API | Publish X post | `services/x_service.py` | Stored bearer access token | `{"text": content}` | JSON post response |
| LinkedIn REST API | Publish LinkedIn post | `services/linkedin_service.py` | Stored bearer access token | Author and post payload | JSON/header post ID |
| SQLite | App data/checkpoints | DB modules/LangGraph | Local filesystem | SQL/content/checkpoints | Rows/checkpoint state |

No LangSmith client, authentication provider, cloud object storage, or OAuth token-exchange HTTP implementation is present.

## 17. Environment Variables

| Variable | Purpose | Required? | Used in |
|---|---|---|---|
| `GOOGLE_API_KEY` | Gemini chat, embeddings, optional image/audio client | Required for those calls | `core/llm.py`, embedding/tools |
| `TAVILY_API_KEY` | Tavily search authentication | Required when research runs | `tools/web_search.py` |
| `CLOUDFLARE_SCERET` | Cloudflare Worker bearer secret; spelling is part of code | Required for default image generation | `tools/image_generate.py` |
| `IMAGE_MODEL` | Optional Gemini image model | Required only if `USE_GEMINI=True` | `services/image_service.py` |
| `AUDIO_MODEL` | Gemini audio model | Required for configured audio generation | `services/audio_service.py` |
| `X_CLIENT_ID` | Intended X OAuth client ID | Not used by an active route | `core/social_config.py` |
| `X_CLIENT_SECRET` | Intended X OAuth client secret | Not used by an active route | `core/social_config.py` |
| `X_REDIRECT_URI` | Intended X OAuth redirect | Not used by an active route | `core/social_config.py` |
| `LINKEDIN_CLIENT_ID` | Intended LinkedIn OAuth client ID | Not used by an active route | `core/social_config.py` |
| `LINKEDIN_CLIENT_SECRET` | Intended LinkedIn OAuth client secret | Not used by an active route | `core/social_config.py` |
| `LINKEDIN_REDIRECT_URI` | Intended LinkedIn OAuth redirect | Not used by an active route | `core/social_config.py` |
| `LINKEDIN_API_VERSION` | LinkedIn REST header; defaults to `20240201` | Optional | `core/social_config.py`, publishing service |

No actual values are included here. `.env` loading is performed by modules that need it; no `.env.example` was found in the inspected repository.

## 18. Error Handling

- API validation: Pydantic validates declared request shapes and literal values where used. Main `IdeaRequest` fields are unrestricted strings. FastAPI handles malformed JSON/type errors automatically.
- Unsupported upload: returns an error JSON object instead of raising an HTTP error.
- Knowledge list: catches its own recursion/runtime exception and returns an error object.
- Graph nodes: most exceptions propagate and stop graph execution. There are no node retries, fallbacks, or centralized graph error persistence.
- LLM and structured-output failures: propagate from `.invoke()` and stop the request.
- Research failures: Tavily exceptions propagate.
- Database failures: generally propagate; commits are local to each operation.
- Image/audio services: convert many provider exceptions to strings/placeholders, so downstream nodes may persist an apparent URL that is actually an error or null.
- Human review: invalid actions and empty edits raise in the node; the API catches exceptions and returns a normal JSON message response.
- Publishing: provider errors are recorded in `generated_content.publish_error`, status is set to `failed`, and the API returns HTTP 500. Missing content/account and state errors are mapped to HTTP 404/400/409 as appropriate.
- Graph execution failure: no explicit logging or persistence beyond any earlier committed rows/checkpoints.

Potentially incomplete behavior confirmed by source includes no timeout for Gemini/Tavily calls in application code, no retry policy, no request-wide transaction, no rejection path, and inconsistent conversion of provider failures into values rather than exceptions.

## 19. Logging and Observability

There is no configured logging framework. Startup/shutdown and image generation use `print()`. The publishing and graph layers do not log request IDs, node entry/exit, prompts, scores, exceptions, or external latency.

LangGraph checkpointing provides persisted state snapshots by thread ID, which is the main execution visibility mechanism. There is no LangSmith integration or explicit tracing configuration. The graph does not attach a request ID other than the manually generated topic/platform thread ID.

A developer currently debugs by reading returned route payloads, inspecting `content.db` and `content_engine_checkpoints.db`, printing test results, and reproducing graph calls in the test scripts. The repository tests are mostly executable examples rather than assertion-based tests: `tests/test_content_graph.py` and `tests/test_human_review.py` invoke the graph and print results; `tests/test_retrieval.py` runs retrieval and prints matches.

The attempted local bootstrap check in this environment could not run because `langgraph` is not installed in the active Python environment. That is an environment limitation, not a source-code conclusion.

## 20. Complete End-to-End Execution Trace

Example: a client posts `{"topic":"LangGraph interrupts","platform":"LinkedIn","content_type":"technical"}` to `/api/content/generate`.

1. `main.py` receives the request through the router registered from `app/api/routes.py`.
2. `generate_content()` creates a thread ID such as `content-langgraph-interrupts-linkedin` and calls the global compiled `graph.invoke()`.
3. `retrieve_personal_knowledge()` calls `retrieve_relevant_chunks()`, which embeds the topic with Google embeddings, scans `document_chunks`, calculates cosine similarity, and places up to five matches in `retrieved_context`.
4. `decide_research()` sees `technical`, sets `research_required=True`, and routes to query generation.
5. `generate_research_query()` calls Gemini and writes the returned query to `research_query`.
6. `research_topic()` calls Tavily advanced search and stores mapped title/URL/content records in `research_results`; nothing is saved to SQLite.
7. `generate_content_ideas()` builds a prompt with personal and web context, calls Gemini structured output, and stores five `ContentIdea` objects in `ideas`.
8. `quality_check()` removes only ideas with blank title, angle, or reason.
9. `save_ideas_node()` inserts each surviving idea into `content_ideas` and stores IDs in `saved_ids`.
10. `generate_content_node()` selects `ideas[0]`, calls the generation service, sends all context to Gemini, and stores `selected_idea`, `generated_content`, and count zero.
11. `evaluate_content_node()` calls Gemini evaluation and stores score/feedback.
12. If score is below 8 and count is below 2, `refine_content_node()` calls Gemini again with feedback appended to the idea angle, increments the count, and returns to evaluation. Otherwise it proceeds.
13. `save_generated_content_node()` inserts a draft in `generated_content`, stores its ID as `content_id`, and copies generated text to `final_content`.
14. `human_review_node()` constructs the review payload and interrupts the graph. The checkpoint is stored in `content_engine_checkpoints.db`. The initial HTTP response contains `requires_review=true` and the interrupt payload.
15. The client sends the returned thread ID and action to `/api/reveiw`. The route resumes the same checkpoint with `Command(resume=...)`.
16. For approve, `human_review_node()` sets approve state. For edit, it validates and stores replacement text. `finalize_human_review_node()` selects the edited or original text.
17. `save_approval_node()` updates `generated_content.content`, sets status `approved`, and writes `approved_at` in `content.db`.
18. `image_router` sees no `image_requested` in the initial state and selects `image_skipped`.
19. `_audio_decision_node()` returns the state unchanged. `audio_router` sees no `audio_requested` and selects `audio_skipped`.
20. The graph reaches `END`; the review-resume response contains the terminal state. No media row is created.
21. To publish, the client calls the effective publication route `/api/api/publish`. The route reads the generated row, verifies approved status and `can_publish()`, loads a social account from SQLite, marks `publishing`, calls X or LinkedIn, then records published status/external ID or failed status/error.

For `build_in_public`, steps 4-6 differ: the deterministic decision skips query generation and Tavily, so idea generation receives no research results.

## 21. Actual Architecture vs Diagram

| Diagram component | Exists in code? | Actual implementation | Difference |
|---|---|---|---|
| START -> retrieve personal knowledge | Yes | Graph edge to `retrieve_personal_knowledge` | Matches |
| retrieve personal knowledge | Yes | Embedding query plus brute-force SQLite cosine scan | Implemented locally, not a vector DB |
| decide research | Yes | Deterministic content-type switch | No LLM decision |
| research branch | Yes | Gemini query generation then Tavily tool | Matches at high level |
| generate branch | Yes | Directly enters idea generation | Matches |
| generate content ideas | Yes | Gemini structured `ContentIdeas`, requests five | Matches |
| quality check | Yes | Blank title/angle/reason filter | Not a broad quality/duplicate/relevance evaluation |
| save ideas | Yes | Inserts ideas in `content_ideas` | Matches |
| generate content | Yes | Selects only first idea and uses Gemini structured output | Diagram does not show first-idea selection |
| evaluate content | Yes | Gemini score/feedback | Router ignores `should_refine` |
| refine loop | Yes | At most two refinements, then forced approval | Diagram omits the maximum/forced approval rule |
| save generated content | Yes | Saves draft before human review | Matches |
| human review | Yes | LangGraph `interrupt()` with SQLite checkpoint | Matches, with route named `/reveiw` |
| finalize human review | Yes | Chooses edit or original | Matches |
| save approval | Yes | Updates row to approved | Matches |
| generate image / image skipped | Yes | State-flag conditional branches | Flags are never populated by active input/graph |
| audio decision | Yes | Identity node `_audio_decision_node` | It does not make a decision; `audio_router` does |
| generate audio / audio skipped | Yes | State-flag conditional branches | Normal requests skip because flag is absent |
| END | Yes | Both audio branches lead to END | Matches |
| publishing after END | No active graph edge | Separate `/api/api/publish` route and unused `publish_content_node` | Publishing is outside the shown workflow |
| persistent state | Partly | LangGraph SQLite checkpoint DB | Diagram does not show checkpoint storage |
| rejection path | No | Only approve/edit accepted | Diagram implies review but not rejection behavior |

The current source does not contain the older report's claimed unknown edge. The more significant diagram mismatch is operational: media generation is represented structurally but not requested/populated in the active API flow.

## 22. Backend Architecture Diagram in Text

```text
CLIENT
  |
  +--> FastAPI /api/content/generate or /api/ideas
  |      |
  |      +--> global LangGraph graph.invoke(thread_id)
  |             |
  |             +--> retrieve_personal_knowledge
  |             |      +--> Google Gemini embeddings
  |             |      +--> SQLite content.db document_chunks
  |             |
  |             +--> decide_research
  |             |      +--> [research] generate_research_query -> Gemini
  |             |      |                 -> research -> Tavily
  |             |      +--> [skip] generate_content_ideas
  |             |
  |             +--> generate_content_ideas -> Gemini structured output
  |             +--> quality_check -> save_ideas_node -> SQLite content_ideas
  |             +--> generate_content -> Gemini structured output
  |             +--> evaluate_content -> Gemini structured output
  |             |      +--> [low score/count < 2] refine_content -> evaluate_content
  |             |      +--> [approved/limit] save_generated_content -> SQLite generated_content
  |             +--> human_review -> LangGraph interrupt/checkpoint DB
  |
  +--> FastAPI /api/reveiw
  |      +--> Command(resume) -> same checkpoint/thread
  |      +--> finalize_human_review -> save_approval -> SQLite generated_content
  |      +--> image_router -> optional Gemini prompt + Cloudflare image -> SQLite content_media
  |      +--> audio_router -> optional Gemini audio -> SQLite content_media
  |      +--> END
  |
  +--> FastAPI /api/api/publish
         +--> SQLite generated_content/social_accounts
         +--> X API or LinkedIn REST API
         +--> SQLite publication status
```

## 23. Things I now know about this backend

1. The FastAPI object is created in `main.py`.
2. Startup calls `init_db()` before yielding from the lifespan.
3. Application data uses relative SQLite file `content.db`.
4. LangGraph checkpoints use `content_engine_checkpoints.db` through `SqliteSaver`.
5. The active graph is compiled globally when `content_graph.py` is imported.
6. The graph state is the `ContentState` TypedDict.
7. Main generation accepts unrestricted string topic, platform, and content type fields.
8. Personal knowledge is embedded with `gemini-embedding-2`.
9. Retrieval scans every stored chunk and computes cosine similarity in Python.
10. Retrieval returns at most five chunks with score at least `0.35`.
11. Research is deterministic by content type, not an LLM classification.
12. Research uses a Gemini-generated query and Tavily advanced search.
13. Search results are held in state and are not persisted.
14. Ideas use Gemini structured output and request five ideas.
15. The quality check only removes blank title, angle, or reason fields.
16. Every surviving idea is inserted into `content_ideas`.
17. Content generation always selects the first idea.
18. Content evaluation uses Gemini and a 1-10 score schema.
19. The router approves scores of 8 or higher.
20. Two refinements are the maximum before forced approval.
21. Generated content is saved as draft before human review.
22. Human review uses `interrupt()` and checkpoint resume.
23. Human review supports approve and edit, but not reject.
24. Approval updates content text, status, and approved timestamp.
25. Media flags are in state but are not populated by the active generation route.
26. The effective publish route is `/api/api/publish` because of double router prefixes.
27. X and LinkedIn credentials are read from the `social_accounts` table.
28. No OAuth callback or account-connection route exists.
29. The old `report.md` is not authoritative for the current source.
30. The current terminal could not execute the graph because `langgraph` is not installed there.

## 24. Unknown / Uncertain Areas

### Confirmed

- Source-level graph nodes, edges, routers, state fields, SQL statements, provider URLs, model names, route declarations, and environment variable names listed above.
- The main graph has the named diagram nodes and currently has no unknown-node edge in the inspected source.
- The normal initial API state omits image/audio request flags.

### Partially confirmed

- Whether the Gemini `response.content` shape matches the assumptions in `generate_research_query()` and `generate_image_prompt()` depends on the installed LangChain Google integration/version and actual provider responses.
- Whether `gemini-3.5-flash` and `gemini-embedding-2` are available to the configured account depends on provider/account configuration.
- Exact LangGraph interrupt response serialization depends on the installed LangGraph version.
- Whether checkpoint files and application DB resolve to the intended directory depends on the process working directory because paths are relative.
- Actual publication response shapes depend on X/LinkedIn API responses and account permissions.

### Cannot determine from this repository

- The real secret values, provider quotas, latency, rate limits, or network availability.
- Whether any external frontend exists outside this repository.
- Whether social-account rows are populated manually or by an omitted deployment process.
- Whether the current media provider endpoints accept the configured credentials in production.
- The exact Uvicorn/process-manager command used to deploy the app.
- Runtime behavior in the active environment, because the inspected terminal lacks the declared dependencies; no source changes were made to compensate.

## 25. Final Technical Summary

### A. Architecture summary

A synchronous FastAPI service delegates content creation to a compiled LangGraph. Services isolate SQLite CRUD, provider clients, retrieval, document ingestion, content prompting, media, and publication.

### B. Workflow summary

The active graph retrieves personal context, deterministically chooses research, optionally searches Tavily, generates and filters ideas, saves them, generates/evaluates/refines the first idea, saves a draft, interrupts for review, saves approval, conditionally handles media, and ends.

### C. State summary

`ContentState` carries request data, retrieved context, research, ideas, generated text, evaluation, human-review values, IDs, approval, and media flags. LangGraph checkpoints it by thread ID; application records are separately persisted in SQLite.

### D. Database summary

`content.db` contains ideas, documents, chunks/JSON embeddings, generated content, media references, and social accounts. Generated content moves from draft to approved and independently tracks publication status. Checkpoints are in a different SQLite file.

### E. AI/LLM summary

Gemini chat is used for query generation, structured ideas, structured post generation, evaluation, and image prompts. Google embeddings power RAG. Scores drive refinement, but the evaluation `should_refine` flag is ignored.

### F. External services summary

Tavily handles research; a Cloudflare Worker is the default image provider; Google GenAI is used for optional image/audio generation; X and LinkedIn REST APIs handle publication. No OAuth implementation or LangSmith tracing is present.

### G. Human-in-the-loop summary

The graph pauses with `interrupt()` after saving a draft. A separate misspelled review endpoint resumes by thread ID with approve/edit data. Rejection, timeout, and explicit feedback are not implemented.

### H. Current limitations

Media choices are not populated in the normal request path. The publication route has a double `/api` prefix. The knowledge list handler shadows its imported DB function. Provider failures are inconsistently raised versus stored as strings/placeholders. There are no graph retries, central logs, or request IDs. The repository tests are mostly print-based examples.

### I. Important implementation details

The graph compiles from the current source without the obsolete unknown-edge issue described in the existing report, but runtime validation was unavailable in the current terminal because dependencies are missing. The source itself is the basis for this report; no redesign or code modification was performed.

# Backend Mental Model

Think of the backend as three connected systems. FastAPI receives a request and starts or resumes a LangGraph state machine. The graph gathers context, asks Gemini and Tavily for the material needed to write and judge a post, saves intermediate/final records in SQLite, and pauses at human review. A second SQLite file remembers paused graph state. Once a human approves or edits the draft, the graph can skip or run media based on state flags and finish. Publishing is a separate approved-content API path that reads SQLite and calls X or LinkedIn; it is not part of the graph's terminal path.
