import asyncio
from async_timeout import timeout
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
        self.ctx = ctx
        self.data = data
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
            try:
                data = data['entries'][0]
            except:
                return

        filename = data['url']
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
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.cog = ctx.cog
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
                async with timeout(60):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.done(self.guild)

            if not isinstance(source, YTDLSource):
                try:
                    source = await YTDLSource.from_url(self.member, source, loop=self.bot.loop)
                except Exception as e:
                    await self.channel.send(f'Erro.')
                    print(e)
                    continue

            self.current = source

            self.guild.voice_client.play(source, 
                                        after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            ui = await YTDLSource.embending(self.member.message.created_at, 
                                            source.thumbnail, 
                                            source.title, 
                                            source.alt_title, 
                                            self.member.message.author.avatar_url, 
                                            self.member.message.author.name, 
                                            source.web_url)
            self.np = await self.channel.send(embed=ui)
            await self.next.wait()
            source.cleanup()
            self.current = None
    
    def done(self, guild):
        return self.bot.loop.create_task(self.cog.cleanup(guild))

class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.players = {}
    
    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    def player(self, ctx):
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel=None):
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        else:
            channel = ctx.author.voice.channel

        await channel.connect()

    @commands.command()
    async def play(self, ctx, *, url=None):
        if not ctx.voice_client:
            await ctx.invoke(self.join)

        if url is not None:
            player = self.player(ctx)
            source = await YTDLSource.from_url(ctx, url, loop=self.bot.loop, stream=True)
            await player.queue.put(source)
        
        if url is None and ctx.voice_client.is_playing():
            await ctx.send(f'```ini\n[Tem música tocando...]\n```')
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send(f'```ini\n[Aúdio retomado por {ctx.author}.]\n```')
        try:
            if ctx.voice_client.is_playing() and url is not None:
                await ctx.send(f'```ini\n[{source.title} adicionada à fila.]\n```')
        except:
            await ctx.send(f'```ini\n[Erro, tente novamente.]\n```')
    
    @commands.command(aliases=['q', 'playlist'])
    async def queue(self, ctx):
        player = self.player(ctx)
        if player.queue.empty():
            return await ctx.send(f'```ini\n[A fila está vazia.]\n```')

        a = player.queue.qsize()
        
        await ctx.send(f'```ini\n[Temos {a} música(s) na fila.]\n```')

    @commands.command(aliases=['n', 'next'])
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
            await ctx.send(f'```ini\n[Volume alterado para {volume}.]\n```')
        elif volume == 0:
            await ctx.send(f'```ini\n[O volume atual é {ctx.voice_client.source.volume * 100}%.]\n```')

    @commands.command(aliases=['pausa'])
    async def pause(self, ctx):
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if voice and voice.is_playing():
            voice.pause()
            await ctx.send(f'```ini\n[Aúdio pausado por {ctx.author}.]\n```')
        else:
            await ctx.send(f'```ini\n[Não há nada para pausar.]\n```')
    
    @commands.command(aliases=['continuar', 'retornar'])
    async def resume(self, ctx):
        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if voice and voice.is_paused():
            voice.resume()
            await ctx.send(f'```ini\n[Aúdio retomado por {ctx.author}.]\n```')
        else:
            await ctx.send(f'```ini\n[Não há aúdio pausado.]\n```')

    @commands.command()
    async def stop(self, ctx):
        await ctx.voice_client.disconnect()
        await self.cleanup(ctx.guild)

    # This command is bugging the PLAY command, 17-13-21.
    """
    @skip.before_invoke
    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("Conecte-se a um canal de voz.")
                raise commands.CommandError("Membro não conectado à um canal de voz.")
    """
    
    @resume.before_invoke
    @pause.before_invoke
    @queue.before_invoke
    @play.before_invoke
    @skip.before_invoke
    @volume.before_invoke
    async def typing(self, ctx):
        await ctx.trigger_typing()

def setup(bot):
    bot.add_cog(Music(bot))