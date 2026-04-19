import asyncio
import wavelink
import discord

async def test():
    node = wavelink.Node(uri='http://127.0.0.1:2333', password='youshallnotpass')
    await wavelink.Pool.connect(nodes=[node], client=discord.Client(intents=discord.Intents.default()))
    print("Connected")
    
    # Test track search
    print("\n--- TRACK SEARCH ---")
    tracks = await wavelink.Playable.search("ytsearch:hello adele")
    print("Type:", type(tracks))
    print("Is Playlist?", isinstance(tracks, wavelink.Playlist))
    
    # Test playlist search
    print("\n--- PLAYLIST SEARCH ---")
    try:
        # Lofi Girl playlist
        pl = await wavelink.Playable.search("https://www.youtube.com/playlist?list=PLofht4BTc5vSWMILB1s7C_Pj4R52n3I3C")
        print("Type:", type(pl))
        print("Is Playlist?", isinstance(pl, wavelink.Playlist))
        if isinstance(pl, wavelink.Playlist):
            print("Name:", pl.name)
            print("Tracks len:", len(pl.tracks))
        elif isinstance(pl, list):
            print("List len:", len(pl))
    except Exception as e:
        print("Playlist error:", e)

    await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test())
