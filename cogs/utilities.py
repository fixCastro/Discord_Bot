import discord
from discord.ext import commands
#pip install googletrans==4.0.0-rc1
from googletrans import Translator

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(aliases=['t'])
    async def translate(self, ctx, lang, *, args):
        t = Translator()
        content = t.translate(str(args), dest=lang)
        if lang == 'ja':
            await ctx.send(f'```ini\n[{content.text} - {content.pronunciation}]\n```')
        else:
            await ctx.send(f'```ini\n[{content.text}]\n```')

    @translate.before_invoke
    async def typing(self, ctx):
        await ctx.trigger_typing()

def setup(bot):
    bot.add_cog(Utilities(bot))
