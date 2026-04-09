# 🧵 L.O.O.M.
### Layered Orchestration & Operational Mind

A voice-first, multi-agent personal AI OS built for Fedora Linux (Wayland). LOOM sits on your desktop and controls your machine through natural language — playing music, adjusting brightness, searching the web, managing files, and more. It is not a product. It is built for one user, optimized for speed and capability.

---

## What It Does

You talk (or type) to LOOM. LOOM figures out what agent to use, builds a plan, executes it using real tools, and speaks the result back.

```
You: "Search the web for today's top AI news and summarize it"
LOOM → browser_agent → web_search → get_page_text → speaks summary aloud
```

```
You: "Turn brightness to 40% and play something chill on Spotify"
LOOM → desktop_agent → setBrightness(40) → searchAndPlay("chill music")
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
    │  4. Route to the right agent                │
    └──────────────┬──────────────────────────────┘
                   │  { target_agent, plan }
          ┌────────┴────────┐
          ▼                 ▼
   desktop_agent       browser_agent
   OS, hardware,       Web search,
   Spotify, files,     page reading,
   memory, timers      Playwright automation
          │                 │
          ▼                 ▼
    ┌─────────────────────────────────┐
    │          TOOL REGISTRY          │
    │  tools/registry.py              │
    │  27 tools, auto-exposed as      │
    │  OpenAI function-call schema    │
    └─────────────────────────────────┘
```

**Emit pattern:** All output goes through an `emit(msg)` callback. The same orchestrator code powers CLI (print), Web SSE, and wake word TTS — no branching needed.

**Smart routing:** The orchestrator only enables LLM reasoning tokens for complex queries (>12 words, or multi-step keywords like "and then", "schedule", "research"). Simple commands skip reasoning — ~3-4s faster.

---

## Current Features

### Agents

| Agent | Status | What it handles |
|-------|--------|----------------|
| `desktop_agent` | ✅ Live | OS, Spotify, hardware, files, memory, timers |
| `browser_agent` | ✅ Live | Web search, page reading, Playwright automation |
| `conversational` | ✅ Live | Direct chat, no tool use, memory-aware |
| `coding_agent` | 🔜 Planned | Write + run Python in a sandboxed workspace |

### Desktop Tools (27 total)

| Category | Tools |
|----------|-------|
| Apps | `is_app_running`, `open_app`, `close_app` |
| Hardware | `getBrightness`, `setBrightness`, `adjustBrightness`, `setVolume`, `adjustVolume`, `toggleMute` |
| Spotify playback | `searchAndPlay`, `getCurrentTrackInfo`, `togglePlayPause`, `nextTrack`, `previousTrack` |
| Spotify playlists | `saveCurrentSongToMemory`, `listRememberedSongs`, `createPlaylistFromMemory`, `getUserPlaylists`, `playUserPlaylist` |
| Files | `findFiles`, `readFile` |
| Time | `getCurrentTime`, `setTimer` |
| Memory | `rememberFact`, `recallFact` |

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
| TTS | ✅ Live | espeak-ng via subprocess, non-blocking, strips markdown |
| Mic button | ✅ Live | Hold-to-record in web UI, auto-submits on release |
| Voice mode | ✅ Live | Toggle in navbar — every response spoken aloud |
| Wake word | ✅ Live | OpenWakeWord `hey_jarvis` model, background thread |

### Memory System

LOOM uses a Qdrant vector DB for long-term, semantic memory.

- **Explicit memory:** `rememberFact(topic, fact)` stores anything you tell it. `recallFact(query)` retrieves by meaning, not exact match.
- **Implicit context:** Before every orchestrator call, `getImplicitContext()` silently finds the 3 most relevant memories and injects them into the prompt. You don't ask — LOOM just knows.
- **Song memory:** `saveCurrentSongToMemory()` reads D-Bus metadata for the now-playing track, finds its Spotify URI, and stores it. `createPlaylistFromMemory()` turns all saved songs into a real Spotify playlist.
- **Embeddings:** Google Gemini `gemini-embedding-001` (3072 dimensions), LRU-cached with `@lru_cache(maxsize=256)`.

### Web UI

- Dark theme, aurora background blobs, SSE streaming responses
- **Markdown rendering** — tables, bold, headers, code blocks, links all render correctly (via marked.js)
- **Mic button** — hold to record, release to transcribe and auto-submit
- **Voice toggle** — speaker icon in navbar, turns purple when ON (responses spoken aloud)
- **Wake word toggle** — broadcast icon in navbar, turns pink and pulses when actively listening
- **Mode toggle** — switch Cloud ↔ Local at runtime, context is cleared on switch

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
sudo dnf install ffmpeg espeak-ng brightnessctl

# Ubuntu / Debian
sudo apt install ffmpeg espeak-ng brightnessctl
```

| Package | Why |
|---------|-----|
| `ffmpeg` | faster-whisper needs it to decode browser WebM audio |
| `espeak-ng` | TTS engine for voice output |
| `brightnessctl` | Screen brightness control via D-Bus |

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
- **Spotify:** Create an app at the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard). Add `http://127.0.0.1:8888/callback` to Redirect URIs. On first run, a browser window opens for OAuth consent — this only happens once, then the token is cached at `.spotify_cache`.

### 5. (Optional) Local mode with Ollama

```bash
# Install Ollama from https://ollama.com, then:
ollama pull qwen3:4b
```

---

## Running

### Web UI

```bash
uvicorn interfaces.web.server:app --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080`.

### CLI

```bash
python3 main.py
```

Plain text loop — no voice, no streaming. Useful for testing.

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

### Mic button (Web UI)

Hold the mic button → recording starts (red pulse animation, "Listening..." in status bar).
Release → audio is sent to `/api/voice` → faster-whisper transcribes it → input field populates → form auto-submits.

The Whisper model loads lazily on the first voice request (~3-4s). All subsequent requests are instant.

### Voice mode (TTS)

Click the speaker icon in the navbar. When active (purple), every LOOM response is spoken aloud via espeak-ng after the SSE stream completes. Markdown is stripped before speaking so bold/code/headers read naturally.

### Wake word

Click the broadcast icon in the navbar. The server starts a background thread that continuously listens on the microphone.

Say **"Hey Jarvis"** → LOOM plays "Yes?" → speak your command → LOOM processes it and speaks the response.

The wake word model downloads from HuggingFace on first activation (~5 seconds), then is cached locally.

> **On the wake phrase:** OpenWakeWord ships with `hey_jarvis`, `alexa`, `hey_mycroft`, and `hey_rhasspy`. There is no built-in "Hey LOOM" model. `hey_jarvis` is used as the default. Custom "Hey LOOM" training is on the roadmap (openwakeword supports synthetic data fine-tuning).

---

## API Reference

### Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/chat` | Send a message. Returns SSE stream. Body: `{"message": "..."}` |
| `GET` | `/api/status` | Returns `{mode, voiceMode, wakeWordActive}` |
| `POST` | `/api/mode` | Switch cloud/local. Body: `{"mode": "cloud"}` |
| `POST` | `/api/voice` | Upload raw `audio/webm` bytes → `{"text": "..."}` |
| `POST` | `/api/voice-mode` | Toggle TTS. Body: `{"enabled": true}` |
| `GET` | `/api/voice-mode` | Current TTS state |
| `POST` | `/api/wake-word` | Start/stop wake word thread. Body: `{"enabled": true}` |

### SSE event types

| Event | Data | Meaning |
|-------|------|---------|
| `status` | Plain string | Status hint shown below chat ("Thinking...", "Browsing the web...") |
| `message` | `{"text": "..."}` | Response text chunk to append to the bubble |
| `done` | (empty) | Stream complete |

---

## Project Structure

```
l.o.o.m/
├── main.py                          # CLI entry point
│
├── core/
│   ├── orchestrator.py              # Intent routing, LLM calls, memory injection
│   ├── state.py                     # Global singleton: clients, chat histories, flags
│   └── memory_manager.py            # Qdrant, Gemini embeddings, implicit context
│
├── agents/
│   ├── desktop_agent/agent.py       # OS execution agent (10-iter tool-call loop)
│   └── browser_agent/agent.py       # Web research/automation agent (8-iter loop)
│
├── tools/
│   ├── registry.py                  # Dynamic OpenAI schema generation + tool lookup
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
│   │       ├── index.html           # Single-page UI
│   │       ├── app.js               # SSE client, mic, wake/voice toggles
│   │       └── style.css            # Dark theme, aurora, markdown styles
│   └── voice/
│       ├── stt_whisper.py           # faster-whisper STT (lazy model load)
│       ├── tts_piper.py             # espeak-ng TTS
│       └── wake_word.py             # OpenWakeWord background detection thread
│
└── loom_db/                         # Qdrant vector DB (local, persisted to disk)
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
"What songs have I saved?"
"Create a playlist called Focus Mode from my saved songs"
"Show all my Spotify playlists"

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

# Memory
"Remember that my standup is every day at 10am"
"Remember I prefer dark roast coffee"
"What do you know about my schedule?"
"Do you know my coffee preference?"
```

---

## Roadmap

### Next

- [ ] **Tool call trace UI** — Collapsible steps inside the LOOM bubble showing which tools ran and what they returned. Emit `__tool__` / `__tool_result__` SSE prefixes; JS renders them.
- [ ] **Jobs page** — `/jobs` view with history of every task: input, agent used, tools called, result, timing.
- [ ] **Retry + backoff** — Exponential backoff on all LLM calls. Currently a failed API call silently returns nothing.
- [ ] **Coding agent** — Write + execute Python in `~/loom_workspace/`. Tools: `write_file`, `run_python`, `run_shell`, `install_package`.
- [ ] **Custom "Hey LOOM" wake word** — Train using openwakeword's synthetic data pipeline.

### Medium term

- [ ] **Task state machine** — `Task` object: `pending → running → done/failed`. Enables job history, retry, cancellation, and a stop button in the UI.
- [ ] **Async orchestrator** — Convert `processUserRequest` to `async def`. Enables parallel tool execution via `asyncio.gather()`.
- [ ] **Stop button** — Cancel an in-flight request without killing the server.
- [ ] **Base agent class** — `BaseAgent` with shared retry logic, tool-call loop, and structured step emission. `DesktopAgent` and `BrowserAgent` inherit.

### Long-term — always-on background companion

The end goal: LOOM runs continuously, learns your habits, checks in on your goals, and helps proactively rather than waiting to be asked.

- **Episodic memory** — SQLite log of every interaction. Daily summaries stored as vectors in Qdrant. LOOM remembers what you worked on yesterday.
- **Activity monitor** — Background daemon watches active windows via D-Bus, detects context (coding, browsing, idle), stores patterns.
- **Daily check-in** — systemd timer at login. Small popup window asks about your day, reviews goals, gives a plan.
- **Self-improvement layer** — LOOM surfaces habit patterns, tracks fitness and sleep goals, delivers weekly summaries.
- **Memory overhaul** — `importance` score + `last_accessed` on every Qdrant record. Decay low-importance facts over time. Separate episodic (event  ⏵⏵ accept edits on (shift+tab to cycle) · 

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM routing | [OpenRouter](https://openrouter.ai) (cloud) / [Ollama](https://ollama.com) (local) |
| Embeddings | Google Gemini `gemini-embedding-001` |
| Vector DB | [Qdrant](https://qdrant.tech) (local, on-disk) |
| Web framework | FastAPI + SSE Starlette |
| Browser automation | Playwright (Chromium headless) |
| Web search | DuckDuckGo via `ddgs` (no API key) |
| STT | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) `base.en` |
| TTS | espeak-ng |
| Wake word | [OpenWakeWord](https://github.com/dscripka/openWakeWord) |
| Spotify | [Spotipy](https://spotipy.readthedocs.io) (OAuth) |
| OS integration | pydbus, D-Bus, `brightnessctl`, `wpctl` (PipeWire) |
| Audio capture | sounddevice |
| Markdown render | marked.js (CDN) |

---

## Notes

- All processing is local except LLM API calls (OpenRouter) and embeddings (Gemini). Nothing else leaves the machine.
- The Qdrant database is at `loom_db/` — back it up if you have memories you care about.
- Screenshots are saved to `~/Pictures/loom_screenshots/`.
- In local mode, everything is offline except Gemini embeddings. A local embedding model replacement is on the roadmap.
- The browser agent caps at 8 tool-call iterations; the desktop agent at 10. This prevents infinite loops on weak models.
- `get_page_text` uses plain HTTP (no JS execution). For JS-heavy sites, use `open_url` first to load the page in Playwright, then scrape.
