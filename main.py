import discord
from discord.ext import commands
import wavelink

class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # Pastikan Lavalink server sudah aktif di port 2333
        # Jika menggunakan Spotify, pastikan plugin LavaSrc sudah terpasang di Lavalink
        node = wavelink.Node(uri='http://127.0.0.1:2333', password='youshallnotpass')
        await wavelink.Pool.connect(nodes=[node], client=self)

    # EVENT: Otomatis putar lagu berikutnya jika antrean masih ada
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)
        else:
            await player.disconnect()

bot = MusicBot()

@bot.command()
async def play(ctx, *, search: str):
    if not ctx.author.voice:
        return await ctx.send("Masuk ke voice channel dulu ya!")

    if not ctx.voice_client:
        vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
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

@bot.command()
async def skip(ctx):
    """Perintah untuk melewati lagu saat ini"""
    if ctx.voice_client:
        await ctx.voice_client.skip()
        await ctx.send("Lagu dilewati ⏭️")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Bot berhenti dan keluar.")

# PENTING: Jangan berikan token ini ke publik!
bot.run('MTM5MDEyNDE2MTI2MjgxMzE4NA.Go23NC.QC3t1dlsH-iLjIRViR_UtqCpeMEGZp7Mtk3Los')
