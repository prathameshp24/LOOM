# 🧵 L.O.O.M.
### Layered Orchestration & Operational Mind

A voice-first, multi-agent personal AI OS built for Fedora Linux (Wayland). LOOM sits on your desktop and controls your machine through natural language — playing music, adjusting brightness, searching the web, managing files, tracking habits, scheduling recurring jobs, and more. It is not a product. It is built for one user, optimized for speed and capability.

---

## What It Does

You talk (or type) to LOOM. LOOM figures out what agent to use, builds a plan, executes it using real tools, and speaks the result back — while showing a live execution DAG in the UI.

```
You: "Search the web for today's top AI news and summarize it"
LOOM → browser_agent → web_search → get_page_text → speaks summary aloud
```

```
You: "Turn brightness to 40% and play something chill on Spotify"
LOOM → desktop_agent → setBrightness(40) → searchAndPlay("chill music")
```

```
You: "Schedule a standup summary every weekday at 10am"
LOOM → desktop_agent → createJobTool → fires every morning, notifies + speaks result
```

```
You: "Remember that my gym is at 6am every Tuesday"
LOOM → desktop_agent → rememberFact(topic, fact) → stored in Qdrant forever
```

---

## Architecture

```
User Input (Web UI / CLI / Wake Word / Mic Button)
          │
          ▼
    ┌─────────────────────────────────────────────┐
    │              ORCHESTRATOR                   │
    │  core/orchestrator.py                       │
    │                                             │
    │  1. Query Qdrant for implicit memory        │
    │  2. Call LLM → JSON routing decision        │
    │  3. Smart reasoning: ON for complex only    │
    │  4. Emit DAG init event with plan steps     │
    │  5. Route to the right agent                │
    │  6. Log task run to SQLite                  │
    └──────────────┬──────────────────────────────┘
                   │  { target_agent, plan }
          ┌────────┴────────┐
          ▼                 ▼
   desktop_agent       browser_agent
   OS, hardware,       Web search,
   Spotify, files,     page reading,
   memory, timers,     Playwright automation
   habits, jobs
          │                 │
          ▼                 ▼
    ┌─────────────────────────────────┐
    │          TOOL REGISTRY          │
    │  tools/registry.py              │
    │  31 tools, auto-exposed as      │
    │  OpenAI function-call schema    │
    └─────────────────────────────────┘
          │
          ▼
    ┌─────────────────────────────────┐
    │        JOB SCHEDULER            │
    │  core/job_scheduler.py          │
    │  APScheduler, cron-based,       │
    │  notify-send + TTS on fire      │
    └─────────────────────────────────┘
```

**Emit pattern:** All output goes through an `emit(msg)` callback. The same orchestrator code powers CLI (print), Web SSE, wake word TTS, and scheduled job notifications — no branching needed.

**Smart routing:** The orchestrator only enables LLM reasoning tokens for complex queries (>12 words, or multi-step keywords like "and then", "schedule", "research"). Simple commands skip reasoning — ~3-4s faster.

---

## Current Features

### Agents

| Agent | Status | What it handles |
|-------|--------|----------------|
| `desktop_agent` | ✅ Live | OS, Spotify, hardware, files, memory, timers, habits, jobs |
| `browser_agent` | ✅ Live | Web search, page reading, Playwright automation |
| `conversational` | ✅ Live | Direct chat, no tool use, memory-aware |
| `coding_agent` | 🔜 Planned | Write + run Python in a sandboxed workspace |

### Desktop Tools (31 total)

| Category | Tools |
|----------|-------|
| Apps | `is_app_running`, `open_app`, `close_app` |
| Hardware | `getBrightness`, `setBrightness`, `adjustBrightness`, `setVolume`, `adjustVolume`, `toggleMute` |
| Spotify playback | `searchAndPlay`, `getCurrentTrackInfo`, `togglePlayPause`, `nextTrack`, `previousTrack` |
| Spotify playlists | `saveCurrentSongToMemory`, `listRememberedSongs`, `createPlaylistFromMemory`, `getUserPlaylists`, `playUserPlaylist` |
| Files | `findFiles`, `readFile` |
| Time | `getCurrentTime`, `setTimer` |
| Memory | `rememberFact`, `recallFact` |
| Habits | `logHabitTool`, `getHabitStatus`, `createHabitTool` |
| Jobs | `createJobTool`, `deleteJobTool` |

### Browser Tools (6 total)

| Tool | What it does |
|------|-------------|
| `web_search` | DuckDuckGo search, no API key needed |
| `get_page_text` | HTTP fetch + BeautifulSoup, returns clean text (max 3000 chars) |
| `open_url` | Playwright navigates to URL |
| `click_element` | Playwright click by CSS selector |
| `fill_form` | Playwright type into input field |
| `take_screenshot` | Saves PNG to `~/Pictures/loom_screenshots/` |

### Voice Pipeline

| Feature | Status | Details |
|---------|--------|---------|
| STT | ✅ Live | faster-whisper `base.en`, CPU, lazy-loaded |
| TTS | ✅ Live | Piper TTS via subprocess, non-blocking, strips markdown |
| Mic button | ✅ Live | Hold-to-record in web UI, auto-submits on release |
| Voice mode | ✅ Live | Toggle in navbar — every response spoken aloud |
| Wake word | ✅ Live | OpenWakeWord `hey_jarvis` model, background thread |

### Habit Tracker

LOOM tracks daily and weekly habits with streaks, goals, and history. Accessible at `/habits` in the web UI and conversationally through chat.

```
You: "I just did DSA today"
LOOM → desktop_agent → logHabitTool("DSA") → "Logged. 2/3 this week. Streak: 1 week."

You: "Track DSA practice 3 times a week, goal 21 sessions"
LOOM → desktop_agent → createHabitTool("DSA practice", frequency_per_week=3, goal_days=21)

You: "How's my DSA streak?"
LOOM → getHabitStatus("DSA") → answers conversationally from habit context
```

**Storage:** SQLite at `loom_db/habits.sqlite`.

**Auto-context injection:** When any message is habit-related, `getHabitContextForOrchestrator()` prepends a `[SYSTEM HABIT CONTEXT: ...]` block to the orchestrator prompt — no embedding call needed.

**Habit page** (`/habits`): Cards showing streak, weekly progress badge, goal progress bar, and inline history. Add, check in, and delete habits from the UI.

### Jobs & Scheduler

LOOM can schedule recurring tasks that run automatically on a cron schedule. Results are delivered via desktop notification (`notify-send`) and spoken aloud if voice mode is on.

```
You: "Schedule a standup summary every weekday at 10am"
LOOM → desktop_agent → createJobTool("Daily Standup", prompt, "0 10 * * 1-5", ...)

You: "Cancel the standup job"
LOOM → desktop_agent → deleteJobTool("Daily Standup")
```

**Jobs page** (`/jobs`): Two sections:
- **Scheduled Jobs** — all active cron jobs with next/last run times, enable/disable toggle, delete
- **Run History** — every task run (manual and scheduled) with agent badge, result preview, tool call log, and duration. Expandable per run. Individually deletable.

**Create from UI:** New job form with name, prompt textarea, time picker, and repeat dropdown (daily / weekdays / weekends / Monday / Friday / hourly) — auto-generates cron expression.

**Storage:** SQLite at `loom_db/jobs.db` with `jobs` and `task_runs` tables. Every desktop and browser agent execution is logged automatically.

**Notification on fire:** `notify-send` always fires. TTS speaks the result if voice mode is on.

### Live Execution DAG

Every time a task routes to an agent, a DAG panel slides in from the right showing the plan steps as nodes. Tool calls appear live as they execute, and all nodes turn green on completion.

- Pending steps: gray dot
- Active step: pulsing cyan dot
- Completed steps: green dot
- Tool call feed shows tool name + result snippet in real time
- Dismiss button; hides automatically on next message

### Memory System

LOOM uses a Qdrant vector DB for long-term, semantic memory.

- **Explicit memory:** `rememberFact(topic, fact)` stores anything you tell it. `recallFact(query)` retrieves by meaning, not exact match.
- **Implicit context:** Before every orchestrator call, `getImplicitContext()` silently finds the 3 most relevant memories and injects them into the prompt. You don't ask — LOOM just knows.
- **Song memory:** `saveCurrentSongToMemory()` reads D-Bus metadata for the now-playing track and stores its Spotify URI. `createPlaylistFromMemory()` turns all saved songs into a real Spotify playlist.
- **Embeddings:** Google Gemini `gemini-embedding-001` (3072 dimensions), LRU-cached.

### Web UI

- Dark theme, aurora background blobs, SSE streaming responses
- **Markdown rendering** — tables, bold, headers, code blocks, links (via marked.js)
- **Mic button** — hold to record, release to transcribe and auto-submit
- **Voice toggle** — speaker icon in navbar, turns purple when ON
- **Wake word toggle** — broadcast icon in navbar, turns pink and pulses when listening
- **Mode toggle** — switch Cloud ↔ Local at runtime
- **Habits page** (`/habits`) — streak cards, check-ins, goal progress bars, inline history
- **Jobs page** (`/jobs`) — scheduled jobs + full run history with expandable tool traces
- **DAG panel** — live execution graph slides in during every agent task

---

## Installation

### 1. Clone and install Python dependencies

```bash
git clone <repo-url>
cd l.o.o.m.
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Install system packages

```bash
# Fedora / RHEL
sudo dnf install ffmpeg brightnessctl libnotify

# Ubuntu / Debian
sudo apt install ffmpeg brightnessctl libnotify-bin
```

| Package | Why |
|---------|-----|
| `ffmpeg` | faster-whisper needs it to decode browser WebM audio |
| `brightnessctl` | Screen brightness control |
| `libnotify` / `notify-send` | Desktop notifications for scheduled jobs |

### 3. Install Playwright browser

```bash
playwright install chromium
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
# OpenRouter — cloud LLM routing
OPENROUTER_API_KEY=sk-or-v1-...

# Google Gemini — embeddings (always used, even in local mode)
GEMINI_API_KEY=AIza...

# Spotify — music playback and playlist management
SPOTIPY_CLIENT_ID=...
SPOTIPY_CLIENT_SECRET=...
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

**Getting API keys:**

- **OpenRouter:** Register at [openrouter.ai](https://openrouter.ai). Free tier models are used by default.
- **Gemini:** Get a key at [aistudio.google.com](https://aistudio.google.com). Free tier is sufficient.
- **Spotify:** Create an app at the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard). Add `http://127.0.0.1:8888/callback` to Redirect URIs. On first run, a browser window opens for OAuth consent — this only happens once.

### 5. (Optional) Local mode with Ollama

```bash
# Install Ollama from https://ollama.com, then:
ollama pull qwen3:4b
```

---

## Running

```bash
uvicorn interfaces.web.server:app --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080`.

On startup you'll see:
```
INFO: ✅ Ollama Qwen3 warmed up
INFO: ⏰ Job scheduler started — N jobs loaded
```

---

## Models

| Context | Cloud (default) | Local |
|---------|-----------------|-------|
| Orchestrator | `arcee-ai/trinity-large-preview:free` | `qwen3:4b` |
| Agents | `nvidia/nemotron-3-nano-30b-a3b:free` | `qwen3:4b` |
| Embeddings | `gemini-embedding-001` (always) | `gemini-embedding-001` (always) |

Switch at runtime via the mode toggle in the web UI, or:
```bash
curl -X POST http://127.0.0.1:8080/api/mode \
     -H 'Content-Type: application/json' \
     -d '{"mode": "local"}'
```

---

## Voice Features

### Mic button
Hold the mic button → recording starts (red pulse, "Listening..." in status bar). Release → transcribed and auto-submitted.

### Voice mode (TTS)
Click the speaker icon. When active, every LOOM response is spoken aloud after the SSE stream completes. Markdown is stripped before speaking.

### Wake word
Click the broadcast icon. Say **"Hey Jarvis"** → LOOM plays "Yes?" → speak your command → spoken response.

The wake word model downloads from HuggingFace on first activation (~5 seconds), then cached locally.

---

## API Reference

### Chat & control

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/chat` | Send a message. Returns SSE stream. Body: `{"message": "..."}` |
| `GET` | `/api/status` | Returns `{mode, voiceMode, wakeWordActive}` |
| `POST` | `/api/mode` | Switch cloud/local. Body: `{"mode": "cloud"}` |
| `POST` | `/api/voice` | Upload raw `audio/webm` bytes → `{"text": "..."}` |
| `POST` | `/api/voice-mode` | Toggle TTS. Body: `{"enabled": true}` |
| `GET` | `/api/voice-mode` | Current TTS state |
| `POST` | `/api/wake-word` | Start/stop wake word thread. Body: `{"enabled": true}` |

### Habits

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/api/habits` | List all habits with streak + status |
| `POST` | `/api/habits` | Create habit |
| `POST` | `/api/habits/{id}/checkin` | Log a check-in |
| `DELETE` | `/api/habits/{id}` | Delete habit |
| `GET` | `/api/habits/{id}/logs` | Last 14 check-ins |

### Jobs & task runs

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/api/jobs` | List all scheduled jobs |
| `POST` | `/api/jobs` | Create a job. Body: `{name, prompt, cron, schedule_human}` |
| `PATCH` | `/api/jobs/{id}` | Toggle enabled. Body: `{"enabled": true}` |
| `DELETE` | `/api/jobs/{id}` | Delete a job |
| `GET` | `/api/task-runs` | Last 50 task runs |
| `DELETE` | `/api/task-runs/{id}` | Delete a run |

### SSE event types

| Event | Data | Meaning |
|-------|------|---------|
| `status` | Plain string | Status hint shown below chat |
| `message` | `{"text": "..."}` | Response text chunk |
| `dag` | `{"type": "init/tool", ...}` | DAG panel update |
| `done` | (empty) | Stream complete |

---

## Project Structure

```
l.o.o.m/
├── main.py                          # CLI entry point
│
├── core/
│   ├── orchestrator.py              # Intent routing, LLM calls, memory + habit injection, task logging
│   ├── state.py                     # Global singleton: clients, chat histories, flags
│   ├── memory_manager.py            # Qdrant, Gemini embeddings, implicit context
│   ├── habit_manager.py             # SQLite habit CRUD, streak logic, context builder
│   ├── task_logger.py               # SQLite task_runs + jobs tables, CRUD
│   └── job_scheduler.py             # APScheduler wrapper, cron execution, notifications
│
├── agents/
│   ├── desktop_agent/agent.py       # OS execution agent (10-iter tool-call loop)
│   └── browser_agent/agent.py       # Web research/automation agent (8-iter loop)
│
├── tools/
│   ├── registry.py                  # Dynamic OpenAI schema generation + local-mode tool filtering
│   ├── habits.py                    # logHabitTool, getHabitStatus, createHabitTool
│   ├── jobs.py                      # createJobTool, deleteJobTool
│   ├── system/
│   │   ├── app_manager.py           # open_app, close_app, is_app_running
│   │   ├── dbus_hardware.py         # brightness, volume, mute (D-Bus / wpctl)
│   │   ├── dbus_media.py            # Spotify playback + playlist memory
│   │   └── time_alarms.py           # getCurrentTime, setTimer
│   ├── fs/search.py                 # findFiles, readFile
│   └── browser/
│       ├── _browser.py              # Lazy Playwright singleton
│       ├── search.py                # web_search (DuckDuckGo)
│       ├── page.py                  # get_page_text, open_url
│       └── automation.py            # click_element, fill_form, take_screenshot
│
├── interfaces/
│   ├── web/
│   │   ├── server.py                # FastAPI app, SSE streaming, all API routes
│   │   └── static/
│   │       ├── index.html           # Home — chat UI with DAG panel
│   │       ├── habits.html          # Habits page
│   │       ├── jobs.html            # Jobs page — scheduled jobs + run history
│   │       ├── app.js               # SSE client, DAG renderer, mic, toggles
│   │       └── style.css            # Dark theme, aurora, DAG panel styles
│   └── voice/
│       ├── stt_whisper.py           # faster-whisper STT (lazy model load)
│       ├── tts_piper.py             # Piper TTS
│       └── wake_word.py             # OpenWakeWord background detection thread
│
└── loom_db/
    ├── collection/                  # Qdrant vector DB (persisted to disk)
    ├── habits.sqlite                # Habit tracking
    └── jobs.db                      # Scheduled jobs + task run history
```

---

## Example Commands

```
# Hardware
"Set volume to 60%"
"Mute"
"Turn brightness down to 30%"

# Apps
"Open Firefox"
"Is Spotify running?"
"Close the terminal"

# Music
"Play some lo-fi hip hop on Spotify"
"What's playing right now?"
"Skip to the next track"
"Remember this song"
"Create a playlist called Focus Mode from my saved songs"

# Time
"What time is it?"
"Set a timer for 25 minutes"

# Web research
"Search the web for the latest AI news and summarize it"
"What's the current price of Bitcoin?"
"Go to news.ycombinator.com and tell me the top 5 stories"

# Files
"Find all Python files modified today in my Documents folder"
"Read the file ~/notes/ideas.txt"

# Habits
"Track DSA practice 3 times a week, goal 21 sessions"
"I just meditated"
"Did I work out today?"
"How's my DSA streak?"

# Jobs
"Schedule a standup summary every weekday at 10am"
"Remind me to review PRs every Friday at 5pm"
"What jobs do I have scheduled?"
"Cancel the standup job"

# Memory
"Remember that I prefer dark roast coffee"
"What do you know about my schedule?"
```

---

## Roadmap

### Done

- [x] **Voice pipeline** — STT (faster-whisper), TTS (Piper), wake word (OpenWakeWord), mic button
- [x] **Browser agent** — DuckDuckGo search, BeautifulSoup page reading, Playwright automation
- [x] **Implicit memory** — Qdrant vector DB, Gemini embeddings, auto-injected context
- [x] **Habit tracker** — SQLite, streaks, weekly goals, `/habits` page
- [x] **Live DAG panel** — real-time execution graph per task, tool call feed, step highlighting
- [x] **Jobs & scheduler** — APScheduler cron jobs, `notify-send` + TTS notifications, `/jobs` page with run history

### Next

- [ ] **Coding agent** — Write + execute Python in `~/loom_workspace/`. Tools: `write_file`, `run_python`, `run_shell`, `install_package`.
- [ ] **Stop button** — Cancel an in-flight request without killing the server.
- [ ] **Retry + backoff** — Exponential backoff on LLM calls. Currently a failed API call silently returns nothing.
- [ ] **Custom "Hey LOOM" wake word** — Train using openwakeword's synthetic data pipeline.

### Medium term

- [ ] **Base agent class** — `BaseAgent` with shared retry logic, tool-call loop, and structured step emission. `DesktopAgent` and `BrowserAgent` inherit.
- [ ] **Habit analytics** — Weekly summary: streaks, goal alignment, patterns.
- [ ] **Filtering on Jobs page** — Filter run history by agent, status, date range.
- [ ] **Job editing** — Edit prompt/schedule without delete + recreate.

### Long-term — always-on background companion

The end goal: LOOM runs continuously, learns your habits, checks in on your goals, and helps proactively rather than waiting to be asked.

- **Episodic memory** — SQLite log of every interaction. Daily summaries stored as vectors. LOOM remembers what you worked on yesterday.
- **Activity monitor** — Background daemon watches active windows via D-Bus, detects context (coding, browsing, idle), stores patterns.
- **Daily standup** — Scheduled job pulls habit streaks + yesterday's task history + recent memories → generates a personalized standup report every morning.
- **Memory decay** — `importance` score + `last_accessed` on every Qdrant record. Low-importance facts fade over time.
- **Parallel tool execution** — `asyncio.gather()` for independent tool calls within a single agent iteration.
- **Inter-agent delegation** — desktop agent can spawn browser agent mid-task without returning to orchestrator.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM routing | [OpenRouter](https://openrouter.ai) (cloud) / [Ollama](https://ollama.com) (local) |
| Embeddings | Google Gemini `gemini-embedding-001` |
| Vector DB | [Qdrant](https://qdrant.tech) (local, on-disk) |
| Job scheduling | [APScheduler](https://apscheduler.readthedocs.io) (BackgroundScheduler + CronTrigger) |
| Web framework | FastAPI + SSE Starlette |
| Browser automation | Playwright (Chromium headless) |
| Web search | DuckDuckGo via `ddgs` (no API key) |
| STT | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) `base.en` |
| TTS | Piper TTS |
| Wake word | [OpenWakeWord](https://github.com/dscripka/openWakeWord) |
| Spotify | [Spotipy](https://spotipy.readthedocs.io) (OAuth) |
| OS integration | pydbus, D-Bus, `brightnessctl`, `wpctl` (PipeWire) |
| Notifications | `notify-send` (libnotify) |
| Audio capture | sounddevice |
| Markdown render | marked.js (CDN) |

---

## Notes

- All processing is local except LLM API calls (OpenRouter) and embeddings (Gemini). Nothing else leaves the machine.
- The Qdrant database is at `loom_db/collection/` — back it up if you have memories you care about.
- Scheduled job results are stored in `loom_db/jobs.db` alongside the full task run history.
- Screenshots are saved to `~/Pictures/loom_screenshots/`.
- In local mode, everything is offline except Gemini embeddings.
- The browser agent caps at 8 tool-call iterations; the desktop agent at 10. This prevents infinite loops on weak models.
- `get_page_text` uses plain HTTP (no JS execution). For JS-heavy sites, use `open_url` first to load the page in Playwright, then scrape.
