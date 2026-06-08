import asyncio
import wavelink
import logging

async def main():
    node = wavelink.Node(uri='http://127.0.0.1:2333', password='youshallnotpass')
    await wavelink.Pool.connect(nodes=[node])
    
    urls = [
        "https://www.youtube.com/playlist?list=PLxA687tYuMWi8OUus77n7ZiquRq0Wlbl2",
        "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    ]
    
    for url in urls:
        print(f"\nSearching: {url}")
        try:
            tracks = await wavelink.Playable.search(url)
            print(f"Type: {type(tracks)}")
            print(f"Is Playlist? {isinstance(tracks, wavelink.Playlist)}")
            print(f"Length: {len(tracks) if tracks else 0}")
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(main())
