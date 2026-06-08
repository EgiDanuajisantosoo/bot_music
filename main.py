import os
import discord
from discord.ext import commands
import wavelink
import logging
import sys
from dotenv import load_dotenv
from aiohttp import web, ClientSession
from urllib.parse import quote
import asyncio
import aiosqlite

load_dotenv()

# Configure logging to go to stdout immediately
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
    stream=sys.stdout
)
logger = logging.getLogger('MusicBot')


# --- CORS Middleware ---
@web.middleware
async def cors_middleware(request, handler):
    if request.method == 'OPTIONS':
        return web.Response(
            status=204,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
        )

    response = await handler(request)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# --- Database Initialization ---
async def init_db():
    async with aiosqlite.connect('bot_database.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER,
                track_query TEXT NOT NULL,
                track_title TEXT NOT NULL,
                FOREIGN KEY(playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
            )
        ''')
        await db.commit()


class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='kucay', intents=intents)

    async def setup_hook(self):
        # Pastikan Lavalink server sudah aktif di port 2333
        # Jika menggunakan Spotify, pastikan plugin LavaSrc sudah terpasang di Lavalink
        node = wavelink.Node(uri='http://127.0.0.1:2333', password='youshallnotpass')
        await wavelink.Pool.connect(nodes=[node], client=self)
        logger.info("setup_hook: Wavelink Pool connect initiated")
        
        await init_db()
        await bot.add_cog(PlaylistCommands())
        
        bot.loop.create_task(start_web_server())

    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        logger.info(f"Wavelink Node Ready: {payload.node!r} (Session ID: {payload.session_id})")

    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        logger.info(f"Wavelink Track Start: {payload.track.title} in guild {payload.player.guild.id}")

    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        logger.info(f"Wavelink Track End: {payload.track.title} in guild {payload.player.guild.id} (Reason: {payload.reason})")

    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        logger.error(f"Wavelink Track Exception on track {payload.track.title}: {payload.exception}")
        if payload.player:
            # Lewati ke lagu berikutnya agar antrean (100 lagu) tidak terhenti
            await payload.player.skip(force=True)

    async def on_wavelink_track_stuck(self, payload: wavelink.TrackStuckEventPayload):
        logger.warning(f"Wavelink Track Stuck on track {payload.track.title}")
        if payload.player:
            # Lewati ke lagu berikutnya agar antrean tidak terhenti
            await payload.player.skip(force=True)

    async def on_wavelink_websocket_closed(self, payload: wavelink.WebsocketClosedEventPayload):
        logger.warning(f"Wavelink Websocket Closed: Code={payload.code}, Reason={payload.reason}")

    async def on_command_error(self, ctx, error):
        logger.error(f"Command error in {ctx.command}: {error}", exc_info=error)
        await ctx.send(f"⚠️ Terjadi error saat menjalankan command: `{error}`")

class QueuePagination(discord.ui.View):
    def __init__(self, queue_list, timeout=180):
        super().__init__(timeout=timeout)
        self.queue_list = queue_list
        self.current_page = 1
        self.total_pages = max(1, (len(queue_list) + 9) // 10)

    def get_embed(self):
        start_idx = (self.current_page - 1) * 10
        end_idx = start_idx + 10
        embed = discord.Embed(title="🎶 Antrean Lagu", color=discord.Color.blue())
        for i, track in enumerate(self.queue_list[start_idx:end_idx], start=start_idx + 1):
            mins, secs = divmod(track.length // 1000, 60)
            embed.add_field(name=f"{i}. {track.title}", value=f"🎵 {track.author} | ⏱️ `{mins}:{secs:02d}`", inline=False)
        embed.set_footer(text=f"Halaman {self.current_page} dari {self.total_pages} | Total {len(self.queue_list)} lagu")
        return embed

    def update_buttons(self):
        self.prev_btn.disabled = self.current_page <= 1
        self.next_btn.disabled = self.current_page >= self.total_pages

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.primary, disabled=True)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

class PlaylistCommands(commands.Cog):
    def __init__(self):
        pass

    @commands.group(aliases=['pl'], invoke_without_command=True)
    async def playlist(self, ctx):
        await ctx.send("Gunakan: `kucaypl create <nama>`, `kucaypl list`, `kucaypl show <nama>`, `kucaypl add <nama> <lagu>`, `kucaypl remove <nama> <index>`, `kucaypl play <nama>`, `kucaypl delete <nama>`")

    @playlist.command()
    async def create(self, ctx, *, name: str):
        async with aiosqlite.connect('bot_database.db') as db:
            async with db.execute('SELECT id FROM playlists WHERE user_id = ? AND name = ?', (str(ctx.author.id), name)) as cursor:
                if await cursor.fetchone():
                    return await ctx.send("Playlist dengan nama tersebut sudah ada!")
            await db.execute('INSERT INTO playlists (user_id, name) VALUES (?, ?)', (str(ctx.author.id), name))
            await db.commit()
            await ctx.send(f"Playlist **{name}** berhasil dibuat!")

    @playlist.command()
    async def list(self, ctx):
        async with aiosqlite.connect('bot_database.db') as db:
            async with db.execute('SELECT name FROM playlists WHERE user_id = ?', (str(ctx.author.id),)) as cursor:
                rows = await cursor.fetchall()
                if not rows:
                    return await ctx.send("Anda belum memiliki playlist satupun.")
                msg = "**Daftar Playlist Anda:**\n" + "\n".join(f"- {r[0]}" for r in rows)
                await ctx.send(msg)

    @playlist.command()
    async def add(self, ctx, name: str, *, query: str):
        async with aiosqlite.connect('bot_database.db') as db:
            async with db.execute('SELECT id FROM playlists WHERE user_id = ? AND name = ?', (str(ctx.author.id), name)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return await ctx.send("Playlist tidak ditemukan!")
                playlist_id = row[0]
                
            tracks = await wavelink.Playable.search(query)
            if not tracks:
                return await ctx.send("Lagu tidak ditemukan.")
            
            # Jika yang ditambahkan adalah single track / hasil pencarian
            track = tracks[0] if isinstance(tracks, list) and not isinstance(tracks, wavelink.Playlist) else (tracks.tracks[0] if isinstance(tracks, wavelink.Playlist) else tracks[0])
            
            await db.execute('INSERT INTO playlist_tracks (playlist_id, track_query, track_title) VALUES (?, ?, ?)', (playlist_id, query, track.title))
            await db.commit()
            
            if ctx.voice_client:
                vc: wavelink.Player = ctx.voice_client
                if getattr(vc, 'active_playlist_id', None) == playlist_id:
                    await vc.queue.put_wait(track)
                    if not vc.playing:
                        await vc.play(vc.queue.get())
                        
            await ctx.send(f"Berhasil menambahkan **{track.title}** ke playlist **{name}**")

    @playlist.command()
    async def show(self, ctx, *, name: str):
        async with aiosqlite.connect('bot_database.db') as db:
            async with db.execute('SELECT id FROM playlists WHERE user_id = ? AND name = ?', (str(ctx.author.id), name)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return await ctx.send("Playlist tidak ditemukan!")
                playlist_id = row[0]
                
            async with db.execute('SELECT track_title FROM playlist_tracks WHERE playlist_id = ?', (playlist_id,)) as cursor:
                rows = await cursor.fetchall()
                if not rows:
                    return await ctx.send(f"Playlist **{name}** masih kosong.")
                msg = f"**Isi Playlist {name}:**\n" + "\n".join(f"{i+1}. {r[0]}" for i, r in enumerate(rows))
                await ctx.send(msg[:2000])

    @playlist.command()
    async def remove(self, ctx, name: str, index: int):
        async with aiosqlite.connect('bot_database.db') as db:
            async with db.execute('SELECT id FROM playlists WHERE user_id = ? AND name = ?', (str(ctx.author.id), name)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return await ctx.send("Playlist tidak ditemukan!")
                playlist_id = row[0]
            
            async with db.execute('SELECT id, track_title FROM playlist_tracks WHERE playlist_id = ?', (playlist_id,)) as cursor:
                rows = await cursor.fetchall()
                if index < 1 or index > len(rows):
                    return await ctx.send("Index tidak valid!")
                
                track_id = rows[index-1][0]
                track_title = rows[index-1][1]
                await db.execute('DELETE FROM playlist_tracks WHERE id = ?', (track_id,))
                await db.commit()
                await ctx.send(f"Berhasil menghapus **{track_title}** dari playlist **{name}**")

    @playlist.command()
    async def delete(self, ctx, *, name: str):
        async with aiosqlite.connect('bot_database.db') as db:
            async with db.execute('SELECT id FROM playlists WHERE user_id = ? AND name = ?', (str(ctx.author.id), name)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return await ctx.send("Playlist tidak ditemukan!")
                playlist_id = row[0]
            
            await db.execute('DELETE FROM playlist_tracks WHERE playlist_id = ?', (playlist_id,))
            await db.execute('DELETE FROM playlists WHERE id = ?', (playlist_id,))
            await db.commit()
            await ctx.send(f"Playlist **{name}** berhasil dihapus!")

    @playlist.command()
    async def play(self, ctx, *, name: str):
        async with aiosqlite.connect('bot_database.db') as db:
            async with db.execute('SELECT id FROM playlists WHERE user_id = ? AND name = ?', (str(ctx.author.id), name)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return await ctx.send("Playlist tidak ditemukan!")
                playlist_id = row[0]
            
            async with db.execute('SELECT track_query FROM playlist_tracks WHERE playlist_id = ?', (playlist_id,)) as cursor:
                rows = await cursor.fetchall()
                if not rows:
                    return await ctx.send(f"Playlist **{name}** masih kosong.")
                
                if not ctx.author.voice:
                    return await ctx.send("Masuk ke voice channel dulu ya!")

                if not ctx.voice_client:
                    vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
                    vc.autoplay = wavelink.AutoPlayMode.partial
                    vc.queue.mode = wavelink.QueueMode.loop_all
                else:
                    vc: wavelink.Player = ctx.voice_client
                
                if not vc.queue.is_empty:
                    vc.queue.clear()

                await ctx.send(f"Memuat {len(rows)} lagu dari playlist **{name}**...")
                
                added = 0
                for r in rows:
                    try:
                        tracks = await wavelink.Playable.search(r[0])
                        if tracks:
                            track = tracks[0] if isinstance(tracks, list) and not isinstance(tracks, wavelink.Playlist) else (tracks.tracks[0] if isinstance(tracks, wavelink.Playlist) else tracks[0])
                            await vc.queue.put_wait(track)
                            added += 1
                    except Exception as e:
                        logger.error(f"Failed to load track {r[0]}: {e}")
                
                await ctx.send(f"Berhasil memuat {added} lagu ke antrean dan langsung memutarnya!")
                
                vc.active_playlist_id = playlist_id
                
                if vc.playing:
                    await vc.skip(force=True)
                elif not vc.queue.is_empty:
                    await vc.play(vc.queue.get())

bot = MusicBot()

# ============================================
#  Discord Bot Commands
# ============================================

@bot.command(aliases=['p'])
async def play(ctx, *, search: str):
    if not ctx.author.voice:
        return await ctx.send("Masuk ke voice channel dulu ya!")

    if not ctx.voice_client:
        vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        # Aktifkan Autoplay parsial untuk otomatisasi antrean Wavelink
        vc.autoplay = wavelink.AutoPlayMode.partial
        # Jadikan kucaylp (Loop All) aktif secara default (otomatis mengulang antrean yang habis)
        vc.queue.mode = wavelink.QueueMode.loop_all
    else:
        vc: wavelink.Player = ctx.voice_client

    # Cari lagu atau playlist
    tracks = await wavelink.Playable.search(search)
    if not tracks:
        return await ctx.send("Lagu/Playlist tidak ditemukan.")

    if isinstance(tracks, wavelink.Playlist):
        # JIKA PLAYLIST (YouTube/Spotify)
        added = await vc.queue.put_wait(tracks)
        await ctx.send(f'Menambahkan playlist: **{tracks.name}** ({added} lagu) ke antrean.')
    else:
        # JIKA SINGLE TRACK
        track = tracks[0]
        await vc.queue.put_wait(track)
        await ctx.send(f'Menambahkan ke antrean: **{track.title}**')
        
    vc.active_playlist_id = None

    # Jika sedang tidak memutar lagu, langsung putar lagu pertama di antrean
    if not vc.playing:
        await vc.play(vc.queue.get())

@bot.command(aliases=['skp'])
async def skip(ctx):
    """Perintah untuk melewati lagu saat ini"""
    if ctx.voice_client:
        if not ctx.voice_client.playing:
            return await ctx.send("Tidak ada lagu yang sedang diputar.")
        await ctx.voice_client.skip(force=True)
        await ctx.send("Lagu berhasil dilewati ⏭️")

@bot.command(aliases=['q'])
async def queue(ctx):
    """Perintah untuk melihat antrean lagu"""
    if not ctx.voice_client:
        return await ctx.send("Bot tidak sedang berada di voice channel.")
    
    vc: wavelink.Player = ctx.voice_client
    if vc.queue.is_empty:
        return await ctx.send("Antrean saat ini kosong. Gunakan perintah play untuk menambahkan lagu!")

    queue_list = list(vc.queue)
    view = QueuePagination(queue_list)
    
    if view.total_pages > 1:
        view.update_buttons()
        await ctx.send(embed=view.get_embed(), view=view)
    else:
        await ctx.send(embed=view.get_embed())

@bot.command(aliases=['np'])
async def nowplaying(ctx):
    """Melihat lagu yang sedang diputar saat ini"""
    if not ctx.voice_client or not ctx.voice_client.playing:
        return await ctx.send("Bot tidak sedang memainkan lagu.")

    vc: wavelink.Player = ctx.voice_client
    track = vc.current
    if not track:
        return await ctx.send("Bot tidak sedang memainkan lagu.")
    
    mins, secs = divmod(track.length // 1000, 60)
    pos_mins, pos_secs = divmod(vc.position // 1000, 60)
    
    embed = discord.Embed(title="🎵 Sedang Diputar", description=f"**[{track.title}]({track.uri})**", color=discord.Color.green())
    embed.add_field(name="Author", value=track.author, inline=True)
    embed.add_field(name="Durasi", value=f"`{pos_mins}:{pos_secs:02d} / {mins}:{secs:02d}`", inline=True)
    
    if track.artwork:
        embed.set_thumbnail(url=track.artwork)
        
    await ctx.send(embed=embed)

@bot.command(aliases=['lp'])
async def loop(ctx):
    """Toggle untuk mengulang antrean lagu"""
    if not ctx.voice_client:
        return await ctx.send("Bot tidak sedang berada di voice channel.")
        
    vc: wavelink.Player = ctx.voice_client
    
    if vc.queue.mode == wavelink.QueueMode.normal:
        vc.queue.mode = wavelink.QueueMode.loop_all
        await ctx.send("Loop antrean diaktifkan 🔁. Antrean akan terus diputar ulang saat sudah habis!")
    else:
        vc.queue.mode = wavelink.QueueMode.normal
        await ctx.send("Loop antrean dimatikan ➡️.")

@bot.command(aliases=['clr'])
async def clear(ctx):
    """Menghapus semua lagu di antrean"""
    if not ctx.voice_client:
        return await ctx.send("Bot tidak sedang berada di voice channel.")
        
    vc: wavelink.Player = ctx.voice_client
    if vc.queue.is_empty:
        return await ctx.send("Antrean sudah kosong.")
        
    vc.queue.clear()
    vc.active_playlist_id = None
    await ctx.send("Semua antrean lagu telah dihapus 🗑️")

@bot.command(aliases=['sp'])
async def switchplaylist(ctx, *, search: str):
    """Menghapus antrean lama dan menggantinya dengan playlist/lagu baru"""
    if not ctx.author.voice:
        return await ctx.send("Masuk ke voice channel dulu ya!")

    if not ctx.voice_client:
        vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        vc.autoplay = wavelink.AutoPlayMode.partial
        vc.queue.mode = wavelink.QueueMode.loop_all
    else:
        vc: wavelink.Player = ctx.voice_client

    # Bersihkan antrean lama
    if not vc.queue.is_empty:
        vc.queue.clear()
        
    vc.active_playlist_id = None
        
    # Cari lagu atau playlist
    tracks = await wavelink.Playable.search(search)
    if not tracks:
        return await ctx.send("Lagu/Playlist tidak ditemukan.")

    if isinstance(tracks, wavelink.Playlist):
        added = await vc.queue.put_wait(tracks)
        await ctx.send(f'🗑️ Antrean lama dihapus.\n✅ Menambahkan playlist baru: **{tracks.name}** ({added} lagu).')
    else:
        track = tracks[0]
        await vc.queue.put_wait(track)
        await ctx.send(f'🗑️ Antrean lama dihapus.\n✅ Menambahkan lagu baru: **{track.title}**')

    # Langsung putar lagu baru (skip lagu yang sekarang sedang jalan jika ada)
    if vc.playing:
        await vc.skip(force=True)
    else:
        await vc.play(vc.queue.get())

@bot.command(aliases=['sh', 'acak'])
async def shuffle(ctx):
    """Mengacak urutan antrean lagu"""
    if not ctx.voice_client:
        return await ctx.send("Bot tidak sedang berada di voice channel.")
        
    vc: wavelink.Player = ctx.voice_client
    if vc.queue.is_empty or len(vc.queue) < 2:
        return await ctx.send("Antrean terlalu sedikit untuk diacak.")
        
    vc.queue.shuffle()
    await ctx.send("Berhasil mengacak urutan lagu di antrean 🔀. Cek dengan `kucayq`!")

@bot.command(aliases=['stp'])
async def stop(ctx):
    if ctx.voice_client:
        # await ctx.voice_client.disconnect()
        await ctx.send("Bot tidak diperbolehkan keluar oleh Admint")

@bot.command(aliases=['pp'])
async def playpriority(ctx, *, search: str):
    """Memprioritaskan lagu/playlist untuk diputar langsung tanpa menghapus antrean"""
    if not ctx.author.voice:
        return await ctx.send("Masuk ke voice channel dulu ya!")

    if not ctx.voice_client:
        vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        vc.autoplay = wavelink.AutoPlayMode.partial
        vc.queue.mode = wavelink.QueueMode.loop_all
    else:
        vc: wavelink.Player = ctx.voice_client

    # Cari lagu atau playlist
    tracks = await wavelink.Playable.search(search)
    if not tracks:
        return await ctx.send("Lagu/Playlist tidak ditemukan.")

    if isinstance(tracks, wavelink.Playlist):
        # JIKA PLAYLIST
        playlist_tracks = list(tracks)
        # Memasukkan dari urutan belakang agar playlist tersusun benar di awal antrean
        for track in reversed(playlist_tracks):
            vc.queue.put_at(0, track)
        await ctx.send(f'🌟 Memutar langsung playlist: **{tracks.name}** ({len(playlist_tracks)} lagu) tanpa menghapus antrean.')
    else:
        # JIKA SINGLE TRACK
        track = tracks[0]
        vc.queue.put_at(0, track)
        await ctx.send(f'🌟 Memutar langsung lagu: **{track.title}** tanpa menghapus antrean.')

    # Langsung putar lagu baru (skip lagu yang sekarang sedang jalan jika ada)
    if vc.playing:
        await vc.skip(force=True)
    else:
        await vc.play(vc.queue.get())


# ============================================
#  Web API Backend (aiohttp)
# ============================================
app = web.Application(middlewares=[cors_middleware])


def get_player():
    if not bot.voice_clients:
        return None
    return bot.voice_clients[0]


async def api_status(request):
    vc = get_player()
    if not vc:
        return web.json_response({"status": "disconnected", "queue_length": 0})
    
    current = vc.current
    if not current:
        return web.json_response({"status": "idle"})
        
    return web.json_response({
        "status": "playing" if vc.playing else "paused",
        "track": {
            "title": current.title,
            "author": current.author,
            "uri": current.uri,
            "length": current.length,
            "position": vc.position,
            "artwork": current.artwork
        },
        "queue_length": len(vc.queue)
    })


async def api_queue(request):
    vc = get_player()
    if not vc or vc.queue.is_empty:
        return web.json_response({"queue": []})
        
    queue_data = []
    for i, track in enumerate(vc.queue):
        queue_data.append({
            "index": i,
            "title": track.title,
            "author": track.author,
            "length": track.length
        })
    return web.json_response({"queue": queue_data})


async def api_play(request):
    vc = get_player()
    if not vc:
        return web.json_response({"success": False, "error": "Bot not in voice channel"}, status=400)

    try:
        data = await request.json()
        search = data.get("query")
        if not search:
            return web.json_response({"success": False, "error": "Empty query"}, status=400)

        tracks = await wavelink.Playable.search(search)
        if not tracks:
            return web.json_response({"success": False, "error": "Not found"}, status=404)

        if isinstance(tracks, wavelink.Playlist):
            added = await vc.queue.put_wait(tracks)
            message = f"Playlist '{tracks.name}' ditambahkan ({added} lagu)."
        else:
            track = tracks[0]
            await vc.queue.put_wait(track)
            message = f"Lagu '{track.title}' ditambahkan."
            
        vc.active_playlist_id = None

        if not vc.playing:
            await vc.play(vc.queue.get())

        return web.json_response({"success": True, "message": message})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)


async def api_playnext(request):
    """Add a song/playlist to the front of the queue (plays right after current track)."""
    vc = get_player()
    if not vc:
        return web.json_response({"success": False, "error": "Bot not in voice channel"}, status=400)

    try:
        data = await request.json()
        search = data.get("query")
        if not search:
            return web.json_response({"success": False, "error": "Empty query"}, status=400)

        tracks = await wavelink.Playable.search(search)
        if not tracks:
            return web.json_response({"success": False, "error": "Not found"}, status=404)

        if isinstance(tracks, wavelink.Playlist):
            playlist_tracks = list(tracks)
            for track in reversed(playlist_tracks):
                vc.queue.put_at(0, track)
            message = f"Playlist '{tracks.name}' ({len(playlist_tracks)} lagu) ditambahkan ke urutan berikutnya."
        else:
            track = tracks[0]
            vc.queue.put_at(0, track)
            message = f"Lagu '{track.title}' ditambahkan ke urutan berikutnya."

        if not vc.playing:
            await vc.play(vc.queue.get())

        return web.json_response({"success": True, "message": message})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)


async def api_skip(request):
    vc = get_player()
    if vc and vc.playing:
        await vc.skip(force=True)
        return web.json_response({"success": True, "message": "Lagu dilewati."})
    return web.json_response({"success": False, "error": "Not playing"}, status=400)


async def api_remove(request):
    vc = get_player()
    if not vc or vc.queue.is_empty:
        return web.json_response({"success": False, "error": "Queue kosong"}, status=400)

    try:
        data = await request.json()
        index = data.get("index")
        
        if index is None or not isinstance(index, int):
            return web.json_response({"success": False, "error": "Invalid index"}, status=400)
        
        if index < 0 or index >= len(vc.queue):
            return web.json_response({"success": False, "error": "Index out of range"}, status=400)
        
        removed_track = vc.queue[index]
        del vc.queue[index]
        
        return web.json_response({
            "success": True,
            "message": f"Lagu '{removed_track.title}' dihapus dari antrean."
        })
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)


async def api_clear(request):
    vc = get_player()
    if vc:
        vc.queue.clear()
        vc.queue.history.clear()
        vc.active_playlist_id = None
        return web.json_response({"success": True, "message": "Antrean dibersihkan."})
    return web.json_response({"success": False, "error": "Bot not in voice channel"}, status=400)


async def api_move(request):
    """Move a track inside the queue from one index to another.
    Expects JSON: {"from": int, "to": int}
    """
    vc = get_player()
    if not vc or vc.queue.is_empty:
        return web.json_response({"success": False, "error": "Queue kosong"}, status=400)

    try:
        data = await request.json()
        frm = data.get('from')
        to = data.get('to')

        if not isinstance(frm, int) or not isinstance(to, int):
            return web.json_response({"success": False, "error": "Invalid indices"}, status=400)

        items = list(vc.queue)
        n = len(items)
        if frm < 0 or frm >= n or to < 0 or to >= n:
            return web.json_response({"success": False, "error": "Index out of range"}, status=400)

        # perform move in a plain list
        item = items.pop(frm)
        items.insert(to, item)

        # rebuild the queue: clear and re-add items preserving order
        vc.queue.clear()
        for track in items:
            await vc.queue.put_wait(track)

        return web.json_response({"success": True, "message": "Antrean diperbarui."})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)


async def api_playlists(request):
    async with aiosqlite.connect('bot_database.db') as db:
        # Untuk web publik, tampilkan semua playlist
        async with db.execute('SELECT id, user_id, name FROM playlists') as cursor:
            rows = await cursor.fetchall()
            playlists = [{"id": r[0], "user_id": r[1], "name": r[2]} for r in rows]
            return web.json_response({"playlists": playlists})

async def api_playlist_tracks(request):
    playlist_id = request.match_info.get('id')
    if not playlist_id:
        return web.json_response({"success": False, "error": "Invalid ID"}, status=400)
    
    async with aiosqlite.connect('bot_database.db') as db:
        async with db.execute('SELECT id, track_query, track_title FROM playlist_tracks WHERE playlist_id = ?', (playlist_id,)) as cursor:
            rows = await cursor.fetchall()
            tracks = [{"id": r[0], "query": r[1], "title": r[2]} for r in rows]
            return web.json_response({"tracks": tracks})

async def api_playlist_create(request):
    try:
        data = await request.json()
        name = data.get("name")
        # Di web publik, user_id kita default "WebUser"
        user_id = data.get("user_id", "WebUser")
        
        if not name:
            return web.json_response({"success": False, "error": "Empty name"}, status=400)
            
        async with aiosqlite.connect('bot_database.db') as db:
            async with db.execute('SELECT id FROM playlists WHERE user_id = ? AND name = ?', (user_id, name)) as cursor:
                if await cursor.fetchone():
                    return web.json_response({"success": False, "error": "Playlist already exists"}, status=400)
            
            await db.execute('INSERT INTO playlists (user_id, name) VALUES (?, ?)', (user_id, name))
            await db.commit()
            return web.json_response({"success": True, "message": "Playlist created"})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)

async def api_playlist_add(request):
    try:
        data = await request.json()
        playlist_id = data.get("playlist_id")
        query = data.get("query")
        title = data.get("title")
        
        if not playlist_id or not query or not title:
            return web.json_response({"success": False, "error": "Missing data"}, status=400)
            
        async with aiosqlite.connect('bot_database.db') as db:
            await db.execute('INSERT INTO playlist_tracks (playlist_id, track_query, track_title) VALUES (?, ?, ?)', (playlist_id, query, title))
            await db.commit()
            
            vc = get_player()
            if vc and getattr(vc, 'active_playlist_id', None) == playlist_id:
                try:
                    tracks = await wavelink.Playable.search(query)
                    if tracks:
                        track = tracks[0] if isinstance(tracks, list) and not isinstance(tracks, wavelink.Playlist) else (tracks.tracks[0] if isinstance(tracks, wavelink.Playlist) else tracks[0])
                        await vc.queue.put_wait(track)
                        if not vc.playing:
                            await vc.play(vc.queue.get())
                except Exception as e:
                    pass

            return web.json_response({"success": True, "message": "Added to playlist"})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)

async def api_playlist_remove(request):
    try:
        data = await request.json()
        track_id = data.get("track_id")
        if not track_id:
             return web.json_response({"success": False, "error": "Missing data"}, status=400)
             
        async with aiosqlite.connect('bot_database.db') as db:
            await db.execute('DELETE FROM playlist_tracks WHERE id = ?', (track_id,))
            await db.commit()
            return web.json_response({"success": True, "message": "Track removed"})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)

async def api_playlist_delete(request):
    try:
        data = await request.json()
        playlist_id = data.get("playlist_id")
        if not playlist_id:
             return web.json_response({"success": False, "error": "Missing data"}, status=400)
             
        async with aiosqlite.connect('bot_database.db') as db:
            await db.execute('DELETE FROM playlist_tracks WHERE playlist_id = ?', (playlist_id,))
            await db.execute('DELETE FROM playlists WHERE id = ?', (playlist_id,))
            await db.commit()
            return web.json_response({"success": True, "message": "Playlist deleted"})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)

async def api_playlist_play(request):
    vc = get_player()
    if not vc:
        return web.json_response({"success": False, "error": "Bot not in voice channel"}, status=400)
        
    try:
        data = await request.json()
        playlist_id = data.get("playlist_id")
        
        if not playlist_id:
            return web.json_response({"success": False, "error": "Missing playlist_id"}, status=400)
            
        async with aiosqlite.connect('bot_database.db') as db:
            async with db.execute('SELECT track_query FROM playlist_tracks WHERE playlist_id = ?', (playlist_id,)) as cursor:
                rows = await cursor.fetchall()
                if not rows:
                    return web.json_response({"success": False, "error": "Playlist is empty"}, status=400)
                
                if not vc.queue.is_empty:
                    vc.queue.clear()

                added = 0
                for r in rows:
                    try:
                        tracks = await wavelink.Playable.search(r[0])
                        if tracks:
                            track = tracks[0] if isinstance(tracks, list) and not isinstance(tracks, wavelink.Playlist) else (tracks.tracks[0] if isinstance(tracks, wavelink.Playlist) else tracks[0])
                            await vc.queue.put_wait(track)
                            added += 1
                    except Exception as e:
                        logger.error(f"Failed to load track {r[0]}: {e}")
                        
                if vc.playing:
                    await vc.skip(force=True)
                elif not vc.queue.is_empty:
                    await vc.play(vc.queue.get())
                    
                vc.active_playlist_id = playlist_id
                    
                return web.json_response({"success": True, "message": f"Berhasil memutar {added} lagu dari playlist."})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)


# --- Static file serving ---
public_dir = os.path.join(os.path.dirname(__file__), 'public')
if not os.path.exists(public_dir):
    os.makedirs(public_dir)


async def index_handler(request):
    return web.FileResponse(os.path.join(public_dir, 'index.html'))


# Register API routes
app.router.add_get('/api/status', api_status)
app.router.add_get('/api/queue', api_queue)
app.router.add_post('/api/play', api_play)
app.router.add_post('/api/skip', api_skip)
app.router.add_post('/api/clear', api_clear)
app.router.add_post('/api/remove', api_remove)
app.router.add_post('/api/move', api_move)
app.router.add_post('/api/playnext', api_playnext)
app.router.add_get('/api/playlists', api_playlists)
app.router.add_get('/api/playlists/{id}', api_playlist_tracks)
app.router.add_post('/api/playlists/create', api_playlist_create)
app.router.add_post('/api/playlists/add', api_playlist_add)
app.router.add_post('/api/playlists/remove', api_playlist_remove)
app.router.add_post('/api/playlists/delete', api_playlist_delete)
app.router.add_post('/api/playlists/play', api_playlist_play)
app.router.add_get('/', index_handler)
app.router.add_static('/', public_dir)


async def start_web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8081)
    await site.start()
    print("Web Dashboard berjalan di http://localhost:8081")


# PENTING: Token dibaca dari file .env, jangan hardcode!
bot.run(os.environ['DISCORD_BOT_TOKEN'])
