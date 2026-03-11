import logging
import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


load_dotenv()


try:
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET")
    ))

except Exception as e:
    logging.error(f"Failed to authenticate in spotify API : {e}")
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
    """This is the entry point for LOOM to play a query"""
    logging.info(f"Agent requested to play : {query}")
    uri = searchSpotifyUri(query, searchType)
    if uri:
        return playUri(uri)
    
    else:
        logging.warning(f"Could not fing match for {query}")
        return False




if __name__ == "__main__":
    searchAndPlay("Main rang sharbaton ka", "track")