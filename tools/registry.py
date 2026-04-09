import logging
import inspect

from tools.system.app_manager import is_app_running, open_app, close_app
from tools.system.dbus_hardware import getBrightness, setBrightness, adjustBrightness, toggleMute, setVolume, adjustVolume
from tools.system.dbus_media import (
    togglePlayPause, nextTrack, previousTrack, getCurrentTrackInfo, searchAndPlay,
    saveCurrentSongToMemory, listRememberedSongs, createPlaylistFromMemory,
    getUserPlaylists, playUserPlaylist
)
from tools.system.time_alarms import getCurrentTime, setTimer
from tools.fs.search import readFile, findFiles
from core.memory_manager import rememberFact, recallFact

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ── Master list (used by cloud mode and getToolByName) ───────────────────────
LOOM_TOOLS = [
    is_app_running, open_app, close_app,
    getBrightness, setBrightness, adjustBrightness, toggleMute, setVolume, adjustVolume,
    togglePlayPause, nextTrack, previousTrack, getCurrentTrackInfo, searchAndPlay,
    getCurrentTime, setTimer,
    findFiles, readFile,
    rememberFact, recallFact,
    saveCurrentSongToMemory, listRememberedSongs, createPlaylistFromMemory,
    getUserPlaylists, playUserPlaylist,
]

# ── Focused categories for local mode ────────────────────────────────────────
# Each category is a small, coherent set a 4B model can reason about quickly.
TOOL_CATEGORIES = {
    "media":    [searchAndPlay, togglePlayPause, nextTrack, previousTrack, getCurrentTrackInfo],
    "playlist": [getUserPlaylists, playUserPlaylist, saveCurrentSongToMemory,
                 listRememberedSongs, createPlaylistFromMemory],
    "system":   [is_app_running, open_app, close_app],
    "hardware": [getBrightness, setBrightness, adjustBrightness, setVolume, adjustVolume, toggleMute],
    "files":    [findFiles, readFile],
    "time":     [getCurrentTime, setTimer],
    "memory":   [rememberFact, recallFact],
}

# Keywords that map text → category (checked in priority order)
_CATEGORY_KEYWORDS = [
    ("playlist", ["playlist", "my playlist", "saved songs", "create playlist",
                  "remember song", "list songs"]),
    ("media",    ["spotify", "play", "music", "song", "track", "pause", "resume",
                  "next track", "previous track", "skip"]),
    ("hardware", ["volume", "brightness", "mute", "unmute", "bright", "dim",
                  "louder", "quieter", "screen"]),
    ("system",   ["open", "close", "launch", "start", "stop", "kill",
                  "running", "app", "application"]),
    ("files",    ["file", "find", "read", "document", "folder", "search files"]),
    ("time",     ["time", "timer", "alarm", "remind", "clock", "seconds", "minutes", "hours"]),
    ("memory",   ["remember", "recall", "memory", "fact", "save", "know", "memorize"]),
]


def get_tools_for_plan(plan: str, user_input: str = "") -> list:
    """
    Returns a focused tool subset by keyword-matching the plan + user input.
    Falls back to all tools if nothing matches (guarantees correctness).
    Unions multiple matched categories so cross-domain tasks still work
    (e.g. 'open Spotify and play music' → system + media).
    """
    text = (plan + " " + user_input).lower()
    selected_names: set[str] = set()
    selected: list = []

    for category, keywords in _CATEGORY_KEYWORDS:
        if any(kw in text for kw in keywords):
            for tool in TOOL_CATEGORIES[category]:
                if tool.__name__ not in selected_names:
                    selected_names.add(tool.__name__)
                    selected.append(tool)

    if not selected:
        logging.info("Tool selector: no category matched — using all tools")
        return LOOM_TOOLS

    logging.info(f"Tool selector: {len(selected)} tools → {[t.__name__ for t in selected]}")
    return selected


def getToolByName(name: str):
    """Fetches actual callable function by its string name (always searches full list)."""
    for tool in LOOM_TOOLS:
        if tool.__name__ == name:
            return tool
    return None


def get_openai_tools(tools: list | None = None) -> list:
    """
    Converts a tool list to OpenAI JSON Schema format.
    Pass a focused subset for local mode; omit for the full list (cloud mode).
    """
    source = tools if tools is not None else LOOM_TOOLS
    openai_tools = []
    for func in source:
        sig = inspect.signature(func)
        properties = {}
        required = []

        for name, param in sig.parameters.items():
            param_type = "string"
            if param.annotation == int:   param_type = "integer"
            elif param.annotation == float: param_type = "number"
            elif param.annotation == bool:  param_type = "boolean"
            properties[name] = {"type": param_type}
            if param.default == inspect.Parameter.empty:
                required.append(name)

        openai_tools.append({
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": func.__doc__ or f"Executes {func.__name__}",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })
    return openai_tools


def getToolNames() -> list[str]:
    return [tool.__name__ for tool in LOOM_TOOLS]
