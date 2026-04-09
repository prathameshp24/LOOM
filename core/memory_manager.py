import logging
import uuid
from functools import lru_cache
from qdrant_client import QdrantClient
from qdrant_client.http import models
from core.state import globalState

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

qdrant = QdrantClient(path="loom_db")
COLLECTION_NAME = "loom_memory"

try:
    qdrant.get_collection(collection_name=COLLECTION_NAME)

except Exception:
    logging.info("Creating new Qdrant vector collection for long term memory")
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=3072,
            distance=models.Distance.COSINE
        )
    )


@lru_cache(maxsize=256)
def getEmbedding(text: str) -> list[float]:
    """Translates text into a mathematical vector using Gemini. Result is cached."""
    response = globalState.geminiClient.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    return response.embeddings[0].values


def rememberFact(topic: str, fact: str) -> str:
    """Saves a fact, preference, or piece of context in L.O.O.M.'s long term memory"""
    logging.info(f"Saving memory about : {topic}")
    try:
        vector = getEmbedding(fact)
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={"topic": topic, "fact": fact}  
                )
            ]
        )

        return f"Successfully saved to long term memory: '{fact}'"
    
    except Exception as e:
        return f"Failed to save memory: {e}"
    

def recallFact(query: str) -> str:
    """Searches L.O.O.M.'s long term memory for information relevant to the user's query"""
    logging.info(f"Searching long term memory for : {query}")
    try:
        vector = getEmbedding(query)
        results = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=3
        )

        if not results.points:
            return "No relevant memories found in long term storage"
        
        memoryStrings = []
        for hit in results.points:
            if hit.score >= 0.5:
                memoryStrings.append(f"- {hit.payload['fact']} (Topic: {hit.payload['topic']})")

        if not memoryStrings:
            return "No highly relevant memories found"
        
        return "Found these memories from the past:\n" + "\n".join(memoryStrings)
        
    except Exception as e:
        return f"Failed to search memory: {e}"
    

def rememberSongToStorage(track_name: str, artist: str, uri: str) -> str:
    """Internal: saves a recommended song to Qdrant with its Spotify URI"""
    try:
        vector = getEmbedding(f"{track_name} by {artist}")
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "topic": "loom_recommended_song",
                        "fact": f"{track_name} | {artist} | {uri}"
                    }
                )
            ]
        )
        return f"Saved to memory: {track_name} by {artist}"
    except Exception as e:
        return f"Failed to save song: {e}"


def getAllRememberedSongs() -> list[dict]:
    """Returns all recommended songs stored in memory as list of {name, artist, uri}"""
    try:
        points, _ = qdrant.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[models.FieldCondition(
                    key="topic",
                    match=models.MatchValue(value="loom_recommended_song")
                )]
            ),
            limit=200,
            with_payload=True
        )
        songs = []
        for point in points:
            parts = point.payload.get("fact", "").split(" | ")
            if len(parts) == 3:
                songs.append({"name": parts[0], "artist": parts[1], "uri": parts[2]})
        return songs
    except Exception as e:
        logging.error(f"Failed to retrieve remembered songs: {e}")
        return []


def getImplicitContext(query: str) -> str:
    """Silently fetches relevant context for the orchestrator. Unlike recall_fact, this returns a hidden system string or empty string"""
    try:
        vector = getEmbedding(query)
        results = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=3
        )

        if not results.points:
            return ""
        
        memoryStrings = []
        for hit in results.points:
            if hit.score > 0.5:
                memoryStrings.append(f"{hit.payload['fact']}")
        
        if not memoryStrings:
             return ""
             
        # Format it as a hidden metadata block
        return f"[SYSTEM MEMORY: {' | '.join(memoryStrings)}]"
        
    except Exception as e:
        logging.error(f"Implicit memory fetch failed: {e}")
        return ""





    

if __name__ == "__main__":
    print("Testing Vector Database...")
    print(rememberFact("User Preferences", "Prathamesh loves Amit Trivedi's music."))
    print(recallFact("Who is my favorite artist?"))
    qdrant.close()