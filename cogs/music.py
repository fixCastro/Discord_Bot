import asyncio
from async_timeout import timeout
import itertools
import youtube_dl
import discord
from discord.ext import commands
from discord.utils import get

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'ChunkSize': 2000000,
    'MaxSimultaneousChunkDownloads': 8,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
    }

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'
    }

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, ctx, volume=0.1):
        super().__init__(source, volume)
        self.data = data
        self.ctx = ctx
        self.title = data.get('title')
        self.url = data.get('url')
        self.alt_title = data.get('alt_title')
        self.release_date = data.get('release_date ')
        self.web_url = data.get('webpage_url')
        self.thumbnail = data['thumbnails'][0]['url']
        self.duration = data.get('duration')

    @classmethod
    async def from_url(cls, ctx, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data, ctx=ctx.author)

    @classmethod
    async def embending(self, created_at, thumbnail, title, alt_title, avatar, author, web_url):
        ui_embed = discord.Embed(timestamp=created_at)
        ui_embed.set_thumbnail(
            url=thumbnail
        )
        ui_embed.add_field(
            name=title,
            value=alt_title if alt_title is not None else f'...'
        )
        ui_embed.set_footer(
            icon_url=avatar,
            text=f'Música pedida por {author}'
        )
        ui_embed.add_field(
            name='Link do vídeo',
            value=web_url,
            inline=False
        )
        return ui_embed

class MusicPlayer:
    __slots__ = ('member', 'bot', 'guild', 'channel', 'queue', 'next', 'current', 'np')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self.member = ctx
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        self.np = None
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                async with timeout(300):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                await self.guild.voice_client.disconnect()
                await self.guild.voice_client.cleanup()

            if not isinstance(source, YTDLSource):
                try:
                    source = await YTDLSource.from_url(self.member, source, loop=self.bot.loop)
                except Exception as e:
                    await self.channel.send(f'Erro.')
                    print(e)
                    continue

            self.current = source

            self.guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            ui = await YTDLSource.embending(self.member.message.created_at, source.thumbnail, source.title, source.alt_title, self.member.message.author.avatar_url, self.member.message.author.name, source.web_url)
            self.np = await self.channel.send(embed=ui)
            await self.next.wait()
            source.cleanup()
            self.current = None

class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.players = {}
    
    def get_player(self, ctx):
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command(name='play')
    async def play(self, ctx, *, url):
        await ctx.trigger_typing()
        player = self.get_player(ctx)
        source = await YTDLSource.from_url(ctx, url, loop=self.bot.loop, stream=True)
        await player.queue.put(source)
        if ctx.voice_client.is_playing():
            await ctx.send(f'```ini\n[{source.title} adicionada à fila.]\n```')
    
    @commands.command(aliases=['q', 'playlist'])
    async def queue(self, ctx):
        voice = ctx.voice_client

        if not voice or not voice.is_connected():
            return await ctx.send(f'```ini\n[Não estou tocando nada.]\n```')

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send(f'```ini\n[A fila está vazia.]\n```')

        upcoming = list(itertools.islice(player.queue._queue, 0, 10))

        fmt = '\n'.join(f'**`{i["title"]}`**' for i in upcoming)
        embed = discord.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt)

        await ctx.send(embed=embed)

    @commands.command(name='skip', aliases=['n', 'next'])
    async def skip(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            return await ctx.send('Não estou tocando nada.')

        if ctx.voice_client.is_paused():
            pass
        elif not ctx.voice_client.is_playing():
            return

        ctx.voice_client.stop()
        await ctx.send(f'```ini\n[{ctx.author} pulou a música.]\n```')

    @commands.command(aliases=['vol'])
    async def volume(self, ctx, volume: int):
        if ctx.voice_client is None:
            return await ctx.send("Não estou conectado a um canal de voz.")

        if volume > 0 and volume <= 100: 
            ctx.voice_client.source.volume = volume / 100
            await ctx.send("Volume alterado para {}%".format(volume))
        elif volume == 0:
            await ctx.send(f'O volume atual é {ctx.voice_client.source.volume * 100}%.')

    @commands.command(aliases=['pausa'])
    async def pause(self, ctx):
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if voice and voice.is_playing():
            voice.pause()
            await ctx.send(f"Aúdio pausado por {ctx.author}.")
        else:
            await ctx.send(f"Não há nada para pausar.")
    
    @commands.command(aliases=['continuar', 'retornar'])
    async def resume(self, ctx):
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if voice and voice.is_paused():
            voice.resume()
            await ctx.send(f"Aúdio retomado por {ctx.author}.")
        else:
            await ctx.send(f"Não há aúdio pausado.")

    @commands.command()
    async def stop(self, ctx):
        await ctx.voice_client.disconnect()
        await ctx.voice_client.cleanup()

    @skip.before_invoke
    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("Conecte-se a um canal de voz.")
                raise commands.CommandError("Membro não conectado à um canal de voz.")
        elif ctx.voice_client.is_playing():
            pass

def setup(bot):
    bot.add_cog(Music(bot))