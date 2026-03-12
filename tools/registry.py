import logging

from tools.system.app_manager import is_app_running, open_app, close_app
from tools.system.dbus_hardware import getBrightness, setBrightness, adjustBrightness, toggleMute, setVolume, adjustVolume
from tools.system.dbus_media import togglePlayPause, nextTrack, previousTrack, getCurrentTrackInfo, searchAndPlay
from tools.system.time_alarms import getCurrentTime, setTimer
from tools.fs.search import readFile, findFiles

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
    readFile
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

if __name__ == "__main__":
    print("LOOM Tool registry loaded successfully")
    print("-"*40)
    tools = getToolNames()
    print(f"Total tools exposed to AI : {len(tools)}")
    for t in tools:
        print(f"{t}")
