import discord
from discord.ext import commands
import wavelink

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

    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        # Wavelink 3.0+ menangani pemutaran antrean otomatis melalui vc.autoplay
        # Jadi kita tidak perlu memanggil player.play(next_track) secara manual.
        pass

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

bot = MusicBot()

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

# PENTING: Jangan berikan token ini ke publik!
bot.run('')
