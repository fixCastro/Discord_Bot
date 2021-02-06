import asyncio
import discord
import youtube_dl
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
queue = []

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.3):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.alt_title = data.get('alt_title')
        self.release_date = data.get('release_date ')
        self.web_url = data.get('webpage_url')
        self.thumbnail = data['thumbnails'][0]['url']

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command(name='play')
    async def play(self, ctx, *, url):
        global queue

        voice = get(self.bot.voice_clients, guild=ctx.guild)
        if voice and voice.is_playing():
            queue.append(url)
        else:
            async with ctx.typing():
                if queue:
                    while queue:
                        source = await YTDLSource.from_url(queue[0], loop=self.bot.loop, stream=True)
                        ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)
                        del(queue[0])
                else:
                    source = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                    ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)
        
        if ctx.voice_client.stop():
            self.skip(ctx)

        ui_embed = discord.Embed(timestamp=ctx.message.created_at)
        ui_embed.set_thumbnail(
            url=source.thumbnail
        )
        ui_embed.add_field(
            name=source.title,
            value=source.alt_title
        )
        ui_embed.set_footer(
            icon_url=ctx.message.author.avatar_url,
            text=f'Música pedida por {ctx.message.author.name}'
        )
        ui_embed.add_field(
            name='Link do vídeo',
            value=source.web_url,
            inline=False
        )
        await ctx.send(embed=ui_embed)
        print(f'Tocando música no servidor {ctx.guild}.')

    @commands.command(aliases=['fila', 'q'])
    async def queue(self, ctx, *, url= None):
        global queue

        if url is None:
            ui = discord.Embed(timestamp=ctx.message.created_at)
            for i in range(len(queue)):
                ui.add_field(
                    name=f'Próximas músicas',
                    value=queue[i]
                )
            if len(queue) > 0:
                await ctx.send(embed=ui)
            else:
                await ctx.send(f'**A fila está vazia.**')
        else:
            queue.append(url)
            source = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ui_embed = discord.Embed(timestamp=ctx.message.created_at)
            ui_embed.set_thumbnail(
                url=source.thumbnail
            )
            ui_embed.add_field(
                name=source.title,
                value='Adicionado à fila'
            )
            ui_embed.set_footer(
                icon_url=ctx.message.author.avatar_url,
                text=f'Música pedida por {ctx.message.author.name}'
            )
            ui_embed.add_field(
                name='Link do vídeo',
                value=source.web_url,
                inline=False
            )
            await ctx.send(embed=ui_embed)

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
    
    @commands.command(aliases=['next', 'n'])
    async def skip(self, ctx):
        global queue

        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('Não estou tocando nada!')

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return
        vc.stop()
        if queue:
            source = await YTDLSource.from_url(queue[0], loop=self.bot.loop, stream=True)
            ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)
            del(queue[0])
            ui_embed = discord.Embed(timestamp=ctx.message.created_at)
            ui_embed.set_thumbnail(
                url=source.thumbnail
            )
            ui_embed.add_field(
                name=source.title,
                value=source.alt_title
            )
            ui_embed.set_footer(
                icon_url=ctx.message.author.avatar_url,
                text=f'Música pedida por {ctx.message.author.name}'
            )
            ui_embed.add_field(
                name='Link do vídeo',
                value=source.web_url,
                inline=False
            )
            await ctx.send(embed=ui_embed)
        else:
            pass
        await ctx.send(f'Música pulada por {ctx.author}.')

    @commands.command(aliases=['vol'])
    async def volume(self, ctx, volume: int):
        if ctx.voice_client is None:
            return await ctx.send("Não estou conectado a um canal de voz.")

        if volume > 0 and volume <= 100: 
            ctx.voice_client.source.volume = volume / 100
            await ctx.send("Volume alterado para {}%".format(volume))
        elif volume == 0:
            await ctx.send(f'O volume atual é {ctx.voice_client.source.volume * 100}%.')

    @commands.command()
    async def stop(self, ctx):
        global queue
        await ctx.voice_client.disconnect()
        while queue:
            queue.pop

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("Conecte-se a um canal de voz.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

def setup(bot):
    bot.add_cog(Music(bot))