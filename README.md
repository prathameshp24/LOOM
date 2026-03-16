# 🧵 L.O.O.M. (Layered Orchestration & Operational Mind)

**An autonomous, ambient, and deterministic desktop orchestrator built for the Linux Wayland ecosystem.**

L.O.O.M. acts as a local "Jarvis-like" daemon that translates natural language commands into hardware control, file system operations, API interactions, and long-term memory retrieval. It is a **Heterogeneous Multi-Agent System** designed to optimize for both deep reasoning and lightning-fast physical execution.

---

## 🧠 Core Architecture: The "Split-Brain" System

L.O.O.M. decouples cognitive planning from physical tool usage through a sophisticated multi-agent design:

### 1. The Orchestrator (The Brain)
| Attribute | Details |
|-----------|---------|
| **Role** | Analyzes user intent, builds multi-step JSON execution plans, and routes tasks to specialized sub-agents |
| **Engine** | Powered by **OpenRouter API** (supports deep-reasoning models like `hunter-alpha` or fast routers like `gemini-2.5-flash`) |
| **State** | Stateless by default; memory is manually managed via persistent conversational arrays to preserve reasoning tokens |
| **Location** | `core/orchestrator.py` |

### 2. The Desktop Agent (The Hands)
| Attribute | Details |
|-----------|---------|
| **Role** | Executes the Orchestrator's JSON plan flawlessly using native Linux tools and APIs |
| **Engine** | Powered by the universal **OpenAI tool-calling standard** (e.g., `nvidia/nemotron-3-nano-30b-a3b:free`) |
| **Execution** | Features a custom-built, infinite `while True` loop that dynamically extracts JSON schemas, runs local Python functions, and feeds terminal output back to the LLM until task completion |
| **Location** | `agents/desktop_agent/agent.py` |

### 3. The Conversational Agent (The Voice)
| Attribute | Details |
|-----------|---------|
| **Role** | Handles casual chat, contextual jokes, and general knowledge without wasting compute cycles on tool-calling evaluations |
| **Usage** | Automatically selected by the Orchestrator for non-task queries |

---

## ⚡ Current Capabilities (V1)

### Hardware & OS Control
Native integration with **Fedora Linux (Wayland)** for:
- **Application Management**: Open/close apps via `flatpak` or native binaries (`gnome-calculator`, `spotify`, etc.)
- **System Volume**: Adjust, set, or mute using `wpctl`
- **Screen Brightness**: Read, set, or adjust using `brightnessctl`
- **System Timers**: Set countdown timers and alarms

### Media Orcheststration
Deep **Spotify API** integration via `spotipy`:
- Intelligently search, parse, and play music tracks without requiring exact URI strings
- Control playback (play/pause, skip, previous track)
- Read currently playing track metadata via D-Bus

### File System Navigation
- Locate files/folders by name recursively across the Linux directory tree
- Read and summarize local text files (notes, scripts, configs)
- Returns absolute paths with truncated content for large files

### Semantic Long-Term Memory
| Component | Details |
|-----------|---------|
| **Vector Database** | Local **Qdrant** instance (`loom_db/`) |
| **Embeddings** | 3072-dimensional vectors via `gemini-embedding-001` |
| **Operations** | `remember_fact` (write) and `recall_fact` (semantic similarity search) |
| **Usage** | Desktop Agent dynamically stores/retrieves user preferences |

### Vendor Agnosticism
- Completely decoupled from proprietary SDKs (e.g., Google GenAI's Automatic Function Calling)
- All tools are dynamically converted to **OpenAI JSON schemas** via `get_openai_tools()`
- Enables instant, one-line model swapping via OpenRouter

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3 |
| **OS Target** | Fedora Linux (Wayland) |
| **LLM Gateway** | OpenRouter API (via OpenAI Python SDK) |
| **Vector Database** | Local Qdrant (`qdrant-client`) |
| **State Management** | Custom Global Memory (`core/state.py`) |
| **Tool Registry** | Dynamic Schema Generator (`tools/registry.py`) |
| **Spotify Integration** | `spotipy` + D-Bus (`pydbus`) |
| **Voice (Experimental)** | `faster-whisper`, `sounddevice`, `SpeechRecognition` |

---

## 📁 Project Structure

```
l.o.o.m./
├── main.py                     # Entry point: CLI loop
├── core/
│   ├── orchestrator.py         # Main routing logic
│   ├── state.py                # Global state holder
│   ├── memory_manager.py       # Qdrant vector operations
│   └── config.py               # Configuration (if any)
├── agents/
│   ├── base_agent.py           # Base agent class
│   ├── desktop_agent/          # ✅ ACTIVE: OS control
│   ├── coding_agent/           # ⏸️ OFFLINE (V2)
│   └── research_agent/         # ⏸️ OFFLINE (V2)
├── tools/
│   ├── registry.py             # Tool schema generator
│   ├── system/
│   │   ├── app_manager.py      # Open/close apps
│   │   ├── dbus_hardware.py    # Volume, brightness
│   │   ├── dbus_media.py       # Spotify control
│   │   └── time_alarms.py      # Timers, clocks
│   ├── fs/
│   │   └── search.py           # File search & read
│   └── vision/                 # (Future)
├── interfaces/
│   ├── cli.py                  # CLI interface
│   ├── htl.py                  # (Future)
│   └── voice/
│       ├── stt_whisper.py      # Speech-to-text (local)
│       ├── tts_whisper.py      # Text-to-speech (future)
│       └── wake_word.py        # Wake word detection
└── loom_db/                    # Qdrant vector storage
```

---

## 🚀 Getting Started

### Prerequisites
- **OS**: Fedora Linux (Wayland) or compatible Wayland compositor
- **Python**: 3.8+
- **System Tools**: `brightnessctl`, `wpctl`, `flatpak` (optional)
- **API Keys**: OpenRouter, Spotify (optional)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd l.o.o.m.
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (`.env`):
   ```bash
   OPENROUTER_API_KEY=your_openrouter_key
   SPOTIPY_CLIENT_ID=your_spotify_client_id
   SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
   ```

4. **Run L.O.O.M.**:
   ```bash
   python main.py
   ```

---

## 📖 Usage Examples

### Basic Commands
```
👤 You: Open Spotify
🧵 (Desktop): Spotify launched successfully

👤 You: Play some Amit Trivedi
🧵 (Desktop): Now playing: [track name] by Amit Trivedi

👤 You: Set brightness to 70%
🧵 (Desktop): Brightness set to 70%

👤 You: Find my README file
🧵 (Desktop): Found: /home/prats/Documents/Fun/l.o.o.m./README.md
```

### Memory Operations
```
👤 You: Remember that I prefer lo-fi music for coding
🧵 (Desktop): Memory saved successfully

👤 You: What music do I like for coding?
🧵: Found these memories from the past:
    - I prefer lo-fi music for coding (Topic: User Preferences)
```

---

## 🛣️ Roadmap: What's Next (V2 & V3)

The core execution loop is stable. The next phases of development will expand L.O.O.M.'s sensory inputs, agent roster, and user interface.

### V2: Expanded Capabilities
- [ ] **The Browser/Web Agent**: A new specialized agent equipped with web-scraping/Selenium tools to fetch live data (weather, news, research)
- [ ] **The Voice Pipeline**: Integrating `stt_whisper.py` for continuous, hands-free auditory input with local `faster-whisper` models
- [ ] **The "Hacker" Terminal UI**: Replacing standard `print()` logs with the `rich` library for live tables, loading spinners, colored tool-execution blocks, and markdown rendering
- [ ] **The Coding Agent**: Equipping a specialized agent with tools to read the `l.o.o.m.` codebase, write Python files, and run local linters to self-improve

### V3: Advanced Features
- [ ] **Implicit RAG Memory**: Upgrading Qdrant from an "explicit tool" to a pre-prompt injection layer, so the Orchestrator intrinsically knows user preferences without needing to ask the Desktop Agent to search for them
- [ ] **100% Offline Orchestration**: Fine-tuning a small ~3B parameter model (like `Qwen-2.5`) using Unsloth/LoRA strictly on L.O.O.M.'s JSON routing schemas to permanently replace the OpenRouter Orchestrator with a free, instant, local brain
- [ ] **Cross-Platform Support**: Extending beyond Wayland to support GNOME (X11), KDE, and potentially macOS/Windows

---

## 🔧 Available Tools

| Tool | Function | Description |
|------|----------|-------------|
| `open_app` | `command: str` | Launch applications (binaries or Flatpaks) |
| `close_app` | `process_name: str` | Force-close running applications |
| `is_app_running` | `process_name: str` | Check if a process is active |
| `setBrightness` | `percentage: int` | Set screen brightness (0-100) |
| `adjustBrightness` | `stepPercentage: int` | Increase/decrease brightness |
| `getBrightness` | - | Get current brightness level |
| `setVolume` | `percentage: int` | Set system volume (0-100) |
| `adjustVolume` | `percentage: int` | Increase/decrease volume |
| `toggleMute` | - | Toggle audio mute state |
| `searchAndPlay` | `query: str, searchType: str` | Search & play Spotify tracks/playlists |
| `getCurrentTrackInfo` | - | Get currently playing track metadata |
| `togglePlayPause` | - | Toggle Spotify playback |
| `nextTrack` / `previousTrack` | - | Skip tracks |
| `setTimer` | `minutes: int` | Set a system timer/alarm |
| `getCurrentTime` | - | Get current system time |
| `findFiles` | `fileName: str, searchDir: str` | Search for files recursively |
| `readFile` | `filePath: str` | Read file contents (max 2000 chars) |
| `remember_fact` | `topic: str, fact: str` | Save to long-term vector memory |
| `recall_fact` | `query: str` | Search memory by semantic similarity |

---

## 📝 Notes

- **Tested On**: Fedora Linux with Wayland compositor
- **Memory**: Qdrant stores vectors locally in `loom_db/` directory
- **Privacy**: All processing is local except LLM calls via OpenRouter
- **Extensibility**: New tools can be added by registering functions in `tools/registry.py`

---

## 🤝 Contributing

L.O.O.M. is a personal project, but contributions are welcome! Areas of interest:
- New tool integrations (more Linux utilities, APIs)
- UI/UX improvements (TUI, GUI, web interface)
- Model optimization (local LLM fine-tuning)
- Cross-platform compatibility layers

---

## 📄 License

[Add your license here]

---

## 🙏 Acknowledgments

- **OpenRouter** for unified LLM access
- **Qdrant** for local vector storage
- **Spotipy** for Spotify API integration
- **Faster Whisper** for local speech-to-text

---

<div align="center">

**Built with 🧵 for the Linux community**

*Layered Orchestration & Operational Mind*

</div>
