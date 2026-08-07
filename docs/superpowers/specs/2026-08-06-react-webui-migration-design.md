# React WebUI Migration — Architecture Design

Date: 2026-08-06
Status: Draft

## Context

The current TrendPipe/MoneyPrinterTurbo web UI is a single Streamlit app
(`webui/Main.py`, ~4100 lines) that runs server-side in-process: it holds
UI state in `st.session_state` and calls Python service functions
(`app/services/webui_task.py`, `app/services/state.py`, etc.) directly.
There is no HTTP boundary between the UI and the business logic today.

A separate FastAPI backend already exists (`app/asgi.py`, `app/router.py`,
`app/controllers/v1/{video,llm}.py`) exposing task creation/query/list/delete
for video generation, script/terms/social-metadata generation via LLM, and
BGM/material retrieve-upload. Critically, this API uses its **own**
`InMemoryTaskManager` instance, separate from the one instantiated in
`webui_task.py` for the Streamlit UI — today these are two independent task
queues that happen to share the same underlying service layer.

Goal: build a new React frontend that replicates all Streamlit
functionality, without modifying `webui/` or any existing behavior, until
the new frontend is fully validated — at which point the Streamlit app is
deleted.

## Non-goals

- No redesign of visual identity — same colors/typography/layout, just
  re-implemented with React + shadcn/ui components instead of Streamlit
  widgets.
- No changes to existing API endpoints' behavior or contracts.
- No authentication work — the app has none today (`verify_token`
  dependencies are commented out across controllers); the React app
  inherits that posture.
- No parallel/coexistence period in production usage — Streamlit stays
  untouched purely as a fallback during development/validation, not as a
  long-lived dual-serving setup.

## Architecture

```
TrendPipe/
├── webui/                 (untouched Streamlit app; deleted only at the end)
├── webui-react/           (new)
│   ├── src/
│   │   ├── api/           REST client (incl. status polling)
│   │   ├── components/    shadcn/ui primitives + app-specific components
│   │   ├── features/      generation, settings, tasks, onboarding
│   │   ├── i18n/          json copies from webui/i18n, react-i18next
│   │   └── styles/        Tailwind tokens ported from webui/styles.css
│   ├── Dockerfile         multi-stage: node build -> nginx serve
│   ├── nginx.conf         reverse-proxies /api to the api service
│   └── package.json
├── app/                   (only additive changes: new controllers/services)
└── docker-compose.yml     (+1 service: webui-react)
```

Stack: Vite + React + TypeScript + Tailwind + shadcn/ui. Communication with
the existing FastAPI backend via REST only — task progress/logs are
retrieved by polling a status endpoint every 1-2s, the same pattern
Streamlit's own fragment refresh already uses.

## Backend additions (`app/`)

All additions are new files; nothing existing is modified. Reuses existing
service-layer code wherever possible.

1. **Voice/TTS endpoints** — list voices per provider, synthesize a preview
   clip. Ports logic currently only reachable via
   `Main.py:_synthesize_voice_preview` and related helpers into a service
   function callable from a new controller.
2. **LLM provider listing** — expose `LLM_PROVIDER_REGISTRY`
   (`app/models/llm_provider.py`) over HTTP so the frontend can populate
   provider/model selectors.
3. **Runtime config get/set** — expose read/write of the settings currently
   held in `st.session_state` and persisted via `_save_runtime_config` /
   `_set_runtime_config` / `_delete_runtime_config` in `Main.py`, backed by
   the same `config.toml` persistence.
4. **Cache management** — stats and clear-cache endpoints, porting
   `_get_video_cache_stats` and the cache-clearing logic from
   `_render_cache_management_settings`.
5. **Task log polling endpoint** (`GET /api/v1/tasks/{task_id}/logs`, new)
   — a status endpoint already exists (`GET /api/v1/tasks/{task_id}` in
   `app/controllers/v1/video.py`, returning state/progress/videos via
   `TaskQueryResponse`), so this item does **not** duplicate it. It adds
   only the log lines, read from the **video.py task queue** (not
   `webui_task.py`'s separate queue — see below). The frontend polls both
   endpoints every 1-2s while a task is active, mirroring Streamlit's
   existing fragment-refresh pattern. No persistent connection, no
   cross-thread-to-asyncio notification plumbing — the handler just reads
   the current state under lock and returns it.

   Note: per-task log capture (the `_task_logs` / `_append_task_log` /
   thread-filtered loguru sink machinery in `webui_task.py`) exists only
   on the Streamlit path today. `app/services/task.py` (used by
   `video.py`) has no equivalent. This is **new instrumentation to build**
   on the API queue's task-execution path, not something to port or wire
   up as-is — each task already runs on its own thread
   (`controllers/manager/base_manager.py`), so the same
   filter-by-thread-id approach transfers, but the sink itself doesn't
   exist yet there. Building it requires one small, deliberate exception
   to "additive only": `video.py`'s existing `create_task` helper must
   swap its call from `tm.start` to a new log-capturing wrapper so the
   sink gets installed on the right worker thread — a one-line internal
   change, no change to any endpoint's request/response contract. This
   applies regardless of transport (it was originally scoped for a
   WebSocket design; polling needs the same underlying log capture, just
   exposed via a plain GET instead of a push channel). See the "Backend
   API additions" sub-project plan for the exact implementation.

### Task queue unification

The React app exclusively uses the API v1 task queue
(`app/controllers/v1/video.py`'s `task_manager`), not the
`webui_task.py`-local one used by Streamlit. This avoids introducing a
third queue and avoids a live desync between what Streamlit's task manager
panel shows and what the React app shows. `webui_task.py` is not modified —
it keeps serving Streamlit exactly as it does today until Streamlit is
deleted.

## Frontend feature breakdown

1. **Main generation flow**: topic/keyword input -> script preview/edit ->
   generation settings -> submit -> progress shown via status polling ->
   result with download.
2. **Settings** (script / video / audio / subtitle / BGM tabs) — the
   largest single piece of UI, ported from `_render_settings_dialog`
   (`Main.py:1931`) and its per-section renderers
   (`Main.py:2194-3826`).
3. **Task manager / history** — table of past/active tasks, filtering,
   restore, delete — ported from `_render_task_manager_panel` and related
   helpers.
4. **i18n** — the 8 existing JSON files (`webui/i18n/*.json`) are copied
   into `webui-react/src/i18n/` and consumed via `react-i18next`. No
   backend involvement; these are static assets bundled with the frontend.
5. **Styling** — colors/typography/spacing extracted from
   `webui/styles.css` become Tailwind theme tokens; shadcn/ui supplies
   dialog/tabs/select/tooltip/etc. primitives instead of hand-rolled CSS.
6. **Onboarding tour** — reimplemented with a React tour library (e.g.
   `react-joyride`), following the same step sequence as the current
   `streamlit_tour.Tour` usage.

## Docker

New `webui-react` service in `docker-compose.yml`:
- Multi-stage Dockerfile: Node build stage produces a static bundle, nginx
  stage serves it.
- New port (e.g. `3000`), independent from `webui` (8501) and `api` (8080).
- Nginx config reverse-proxies `/api/*` to the `api` service, so the
  frontend never hardcodes the API's host/port and there's no CORS
  concern in production.
- `webui` and `api` service definitions are not modified.

## Validation and cutover

Each feature area (main flow, settings, task manager) is built and
manually validated against the live Streamlit app running side by side
before moving to the next. Only once everything is validated does a
follow-up piece of work remove `webui/`, the `webui` docker-compose
service, and related Dockerfile/script references (`webui.sh`,
`webui.bat`).

## Testing

- Frontend: Vitest + React Testing Library for component/unit tests.
- Backend additions: follow existing test conventions in `test/` (pytest).
- No end-to-end browser automation is in scope for the initial migration;
  manual validation against the running Streamlit app is the acceptance
  method for parity, per feature area.

## Open questions to resolve in per-feature specs

- Exact shape of the new voice-preview and config endpoints (request/response
  schemas) — deferred to the "Backend API additions" sub-project spec.
- Exact polling interval and backoff behavior (e.g. slow down polling for
  long-idle tasks, stop polling once a task reaches a terminal state) —
  deferred to the "Main generation flow" sub-project spec.

## Sub-projects (execution order)

1. Backend API additions (voice/TTS, LLM providers, config, cache, task log polling)
2. Main generation flow (MVP golden path)
3. Settings dialog
4. Task manager / history
5. i18n + styling + onboarding tour
6. Docker/compose integration
7. Streamlit removal (cutover)

Each sub-project gets its own implementation plan via the writing-plans
skill, scoped and reviewed independently.
