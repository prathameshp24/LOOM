import logging
import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

load_dotenv()

SPOTIFY_SCOPES = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "playlist-modify-public "
    "playlist-modify-private "
    "playlist-read-private "
    "playlist-read-collaborative "
    "user-read-private"
)

try:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback"),
        scope=SPOTIFY_SCOPES,
        cache_path=".spotify_cache"
    ))

except Exception as e:
    logging.error(f"Failed to authenticate with Spotify: {e}")
    sp = None

def getSpotifyPlayer():
    """Helper function to lazily load the spotify MPRIS proxy object"""
    import pydbus
    try:
        bus = pydbus.SessionBus()
        return bus.get('org.mpris.MediaPlayer2.spotify', '/org/mpris/MediaPlayer2')
    
    except Exception as e:
        logging.warning("Spotify doesn't appear to be running...")
        return None


def togglePlayPause() -> bool:
    """Toggles play / pause on spotify"""
    player = getSpotifyPlayer()
    if player:
        try:
            player.PlayPause()
            logging.info("Spotify play / pause toggled")
            return True
        
        except Exception as e:
            logging.error(f"Failed to toggle spotify : {e}")
            return False
        
    
    return False



def nextTrack() -> bool:
    """Skips to next track"""
    player = getSpotifyPlayer()

    if player:
        try:
            player.Next()
            logging.info("Skipped to next track")
            return True
        
        except Exception as e:
            logging.error(f"Failed to skip to next track. {e}")
            return False
        
    return False


def previousTrack() -> bool:
    """Skips to previous track"""
    player = getSpotifyPlayer()

    if player:
        try:
            player.Previous()
            player.Previous()
            logging.info("PLayed previous track")
            return True
        
        except Exception as e:
            logging.error(f"Failed to skip to previous track : {e}")
            return False
    
    return False

def getCurrentTrackInfo() -> dict:
    """Reads metadata of currently playing song"""
    player = getSpotifyPlayer()

    if player:
        try:
            metadata = player.Metadata
            title = metadata.get('xesam:title', "Unknown title")
            artists = metadata.get('xesam:artist', ["Unknown artist"])
            artistStr = ", ".join(artists)

            status = player.PlaybackStatus

            logging.info(f"Currently {status}: {title} by {artistStr}")

            return {"title": title, "artist": artistStr, "status": status}
        
        except Exception as e:
            logging.error(f"Error loading metadata: {e}")
            return {}
        

    return {}



def searchSpotifyUri(query: str, searchType: str = 'track') -> str:
    """Searches spotify API for track / playlist / album and returns its native URI"""
    if not sp:
        logging.error("Spotify client could not be initialized")
        return ""
    
    try:
        results = sp.search(q=query, limit=1, type=searchType)
        
        if searchType == "track" and results['tracks']['items']:
            track = results['tracks']['items'][0]
            logging.info(f"Found.. {track['name']} by {track['artists'][0]['name']}")
            return track['uri']
        

        elif searchType == "playlist" and results['playlists']['items']:
            playlist = results['playlists']['items'][0]
            logging.info(f"Found... {playlist['name']}")
            return playlist['uri']
        
    except Exception as e:
        logging.error(f"Spotify API search failed : {e}")

    return ""


def playUri(uri: str)->bool:
    """Instantly plays a specific spotify URI by dbus"""
    if not uri:
        return False
    
    player = getSpotifyPlayer()

    if player:
        try:
            player.OpenUri(uri)
            logging.info(f"Instructing OS to play uri : {uri}")
            return True
        
        except Exception as e:
            logging.error(f"Failed to play uRI via D-bus : {e}")
            return False
        
    return False



def searchAndPlay(query: str, searchType: str = "track")->bool:
    """Search Spotify and play the result. searchType must be one of: 'track', 'album', 'artist', 'playlist'. Defaults to 'track'."""
    logging.info(f"Agent requested to play : {query}")
    uri = searchSpotifyUri(query, searchType)
    if uri:
        return playUri(uri)
    
    else:
        logging.warning(f"Could not fing match for {query}")
        return False




def saveCurrentSongToMemory() -> str:
    """Saves the currently playing Spotify track to L.O.O.M.'s recommendation memory"""
    from core.memory_manager import rememberSongToStorage
    info = getCurrentTrackInfo()
    if not info or not info.get("title"):
        return "No song is currently playing"
    uri = searchSpotifyUri(f"{info['title']} {info['artist']}", "track")
    if not uri:
        return f"Could not find Spotify URI for {info['title']}"
    return rememberSongToStorage(info["title"], info["artist"], uri)


def listRememberedSongs() -> str:
    """Lists all songs saved in L.O.O.M.'s recommendation memory"""
    from core.memory_manager import getAllRememberedSongs
    songs = getAllRememberedSongs()
    if not songs:
        return "No songs saved in memory yet. Play a song and ask me to remember it!"
    lines = [f"{i+1}. {s['name']} by {s['artist']}" for i, s in enumerate(songs)]
    return f"Remembered songs ({len(songs)}):\n" + "\n".join(lines)


def createPlaylistFromMemory(playlist_name: str) -> str:
    """Creates a new Spotify playlist from all songs saved in L.O.O.M.'s recommendation memory"""
    from core.memory_manager import getAllRememberedSongs
    if not sp:
        return "Spotify client not available"
    songs = getAllRememberedSongs()
    if not songs:
        return "No songs in memory to create a playlist from. Save some songs first!"
    try:
        user_id = sp.current_user()["id"]
        playlist = sp.user_playlist_create(
            user_id, playlist_name, public=False,
            description="Created by L.O.O.M."
        )
        # Deduplicate URIs, add in batches of 100 (Spotify limit)
        uris = list(dict.fromkeys(s["uri"] for s in songs))
        for i in range(0, len(uris), 100):
            sp.playlist_add_items(playlist["id"], uris[i:i + 100])
        logging.info(f"Created playlist '{playlist_name}' with {len(uris)} tracks")
        return f"Created playlist '{playlist_name}' with {len(uris)} songs on Spotify."
    except Exception as e:
        logging.error(f"Failed to create playlist: {e}")
        return f"Failed to create playlist: {e}"


def getUserPlaylists() -> str:
    """Lists all Spotify playlists owned by the current user"""
    if not sp:
        return "Spotify client not available"
    try:
        results = sp.current_user_playlists(limit=50)
        playlists = results["items"]
        if not playlists:
            return "You have no playlists on Spotify."
        lines = [
            f"{i+1}. {p['name']} ({(p.get('tracks') or {}).get('total', '?')} tracks)"
            for i, p in enumerate(playlists)
        ]
        return f"Your Spotify playlists ({len(playlists)}):\n" + "\n".join(lines)
    except Exception as e:
        logging.error(f"Failed to fetch playlists: {e}")
        return f"Failed to fetch playlists: {e}"


def playUserPlaylist(playlist_name: str) -> str:
    """Finds and plays one of the current user's own Spotify playlists by name"""
    if not sp:
        return "Spotify client not available"
    try:
        results = sp.current_user_playlists(limit=50)
        playlists = results["items"]
        # Case-insensitive match — prefer exact, fall back to substring
        name_lower = playlist_name.lower()
        match = next((p for p in playlists if p["name"].lower() == name_lower), None)
        if not match:
            match = next((p for p in playlists if name_lower in p["name"].lower()), None)
        if not match:
            names = ", ".join(p["name"] for p in playlists)
            return f"No playlist named '{playlist_name}' found. Your playlists: {names}"
        uri = match["uri"]
        success = playUri(uri)
        if success:
            track_count = (match.get('tracks') or {}).get('total', '?')
            logging.info(f"Playing user playlist: {match['name']}")
            return f"Playing your playlist: {match['name']} ({track_count} tracks)"
        return f"Found playlist '{match['name']}' but failed to start playback"
    except Exception as e:
        logging.error(f"Failed to play user playlist: {e}")
        return f"Failed to play playlist: {e}"


if __name__ == "__main__":
    searchAndPlay("Main rang sharbaton ka", "track")