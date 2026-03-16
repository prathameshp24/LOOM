import logging
import inspect

from tools.system.app_manager import is_app_running, open_app, close_app
from tools.system.dbus_hardware import getBrightness, setBrightness, adjustBrightness, toggleMute, setVolume, adjustVolume
from tools.system.dbus_media import togglePlayPause, nextTrack, previousTrack, getCurrentTrackInfo, searchAndPlay
from tools.system.time_alarms import getCurrentTime, setTimer
from tools.fs.search import readFile, findFiles
from core.memory_manager import rememberFact, recallFact

logging.basicConfig(level=logging.INFO, format= '%(levelname)s: %(message)s')

LOOM_TOOLS = [
    is_app_running,
    open_app,
    close_app,
    getBrightness,
    setBrightness,
    adjustBrightness,
    toggleMute,
    setVolume,
    adjustVolume,
    togglePlayPause,
    nextTrack,
    previousTrack,
    getCurrentTrackInfo,
    searchAndPlay,
    getCurrentTime,
    setTimer,
    findFiles,
    readFile,
    rememberFact,
    recallFact
]

def getToolNames() -> list[str]:
    """Returns a list of all available tool names for logging"""
    return [tool.__name__ for tool in LOOM_TOOLS]

def getToolByName(name: str):
    """Fetches actual callable function by its string name"""
    for tool in LOOM_TOOLS:
        if tool.__name__ == name:
                return tool
        
    return None


def get_openai_tools():
    """Dynamically converts our Python LOOM_TOOLS into the OpenAI JSON Schema format."""
    openai_tools = []
    for func in LOOM_TOOLS:
        sig = inspect.signature(func)
        properties = {}
        required = []
        
        for name, param in sig.parameters.items():
            # Map Python types to JSON Schema types
            param_type = "string"
            if param.annotation == int: param_type = "integer"
            elif param.annotation == float: param_type = "number"
            elif param.annotation == bool: param_type = "boolean"
            
            properties[name] = {"type": param_type}
            
            # If the parameter has no default value, it is required
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
                    "required": required
                }
            }
        })
    return openai_tools