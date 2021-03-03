import requests
import wikipedia
import discord
from discord.ext import commands

class Web(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(aliases=['check'])
    async def url(self, ctx, *, url):
        response = requests.get(url=url if url.startswith('http://') or url.startswith('https://') else 'https://' + url)
        status = response.status_code
        if status in range(200, 299):
            await ctx.send(f'```ini\n[O site está normal. Caso esteja com problemas verifique a sua conexão.]\n```')
        elif status in range(400, 499):
            await ctx.send(f'```ini\n[Hum... Parece que eu também estou com problemas neste site.]\n```')
        elif status in range(500, 599):
            await ctx.send(f'```ini\n[O servidor deste site está com problemas, tente mais tarde. Erro {status}.]\n```')

    @commands.command(aliases=['w'])
    async def wiki(self, ctx, *, search):
        wikipedia.set_lang('pt')
        page = wikipedia.page(search)
        await ctx.send(f'{page.url}')

    @url.before_invoke
    @wiki.before_invoke
    async def typing(self, ctx):
        await ctx.trigger_typing()

def setup(bot):
    bot.add_cog(Web(bot))