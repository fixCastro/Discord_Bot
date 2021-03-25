import discord
from discord.ext import commands
#pip install googletrans==4.0.0-rc1
from googletrans import Translator
import string, random

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(aliases=['t', 'traduzir'])
    async def translate(self, ctx, lang, *, args):
        t = Translator()
        content = t.translate(str(args), dest=lang)
        if lang == 'ja':
            await ctx.send(f'```ini\n[{content.text} - {content.pronunciation}]\n```')
        else:
            await ctx.send(f'```ini\n[{content.text}]\n```')
    
    @commands.command(
        aliases=['senha', 'pw'], 
        description='Gerador de senha, utilize o comando e a quantidade de caracteres desejada.')
    async def password(self, ctx, length):
        channel = await ctx.message.author.create_dm()
        digits = string.ascii_letters + string.digits
        punctuation = string.punctuation
        result = ''
        for _ in range(int(length)):
            result += random.choice(digits)
        result += random.choice(punctuation)
        try:
            await channel.send(f'```ini\nSenha gerada com sucesso: {result}\n```')
        except:
            await channel.send(f'```ini\nErro ao gerar a senha, tente novamente.\n```')

    @translate.before_invoke
    async def typing(self, ctx):
        await ctx.trigger_typing()
    
    @password.before_invoke
    async def delete(self, ctx):
        channel = ctx.channel
        try:
            await channel.purge(limit=1)
        except:
            pass

def setup(bot):
    bot.add_cog(Utilities(bot))
