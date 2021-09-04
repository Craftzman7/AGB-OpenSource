import asyncio
import concurrent
import importlib
import io
import json
import os
import subprocess
import textwrap
import traceback
from contextlib import redirect_stdout

import aiohttp
import discord
import requests
import speedtest
from discord.ext import commands
from discord_argparse import ArgumentConverter, OptionalArgument
from index import EMBED_COLOUR, cursor, delay
from utils import default, http, permissions

from .Utils import *


class create_dict(dict):
    def __init__(self):
        self = dict()

    def add(self, key, value):
        self[key] = value


class Admin(commands.Cog, name='admin', command_attrs=dict(hidden=True)):
    """ Commands that arent for you lol """

    def __init__(self, bot, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = default.get("config.json")
        os.environ.setdefault("JISHAKU_HIDE", "1")
        self._last_result = None
        self.last_change = None
        with open('blacklist.json') as f:
            self.blacklist = json.load(f)
            bot.add_check(self.blacklist_check)
  #this is mainly to make sure that the code is loading the json file if new data gets added

    def blacklist_check(self, ctx):
        return ctx.author.id not in self.blacklist

    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await self.bot.loop.run_in_executor(None, process.communicate)
        return [output.decode() for output in result]

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])
        # remove `foo`
        return content.strip('` \n')

    async def try_to_send_msg_in_a_channel(self, guild, msg):
        for channel in guild.channels:
            try:
                await channel.send(msg)
                break
            except:
                pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if "N Word" in guild.name.lower():
            await self.try_to_send_msg_in_a_channel(guild, "im gonna leave cuz of the server name")
            return await guild.leave()
        for channel in guild.channels:
            if "N Word" in channel.name.lower():
                await self.try_to_send_msg_in_a_channel(guild, f"im gonna leave cuz of the channel name {channel.mention}")
                return await guild.leave()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member, guild=None):
        me = self.bot.get_user(101118549958877184)
        guild = member.guild
        embed = discord.Embed(
            title="User Joined",
            colour=discord.Colour.green()
        )
        embed.add_field(name=f"Welcome {member}", value=f"Enjoy your stay here \rThis server is for <@723726581864071178>, if you want some more info about it, do `tp!help` in <#755722577279713280>\nIf you want colour roles, do `tp!colors` first to see what you can give yourself, then do `tp!colorme <color` <color> being the color thats displayed.")
        embed.add_field(name="Account Created", value=member.created_at.strftime(
            "%a, %#d %B %Y, %I:%M %p UTC"), inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        if member.guild.id == 755722576445046806:
            if member.bot:
                role = discord.utils.get(guild.roles, name="Bots")
                await member.add_roles(role)
                await me.send(f"A bot was just added to anxiety zone... {member.bot.user.name} / {member.bot.user.mention}")
                return
            else:
                role = discord.utils.get(guild.roles, name="Members")
                await member.add_roles(role)
                channel = self.bot.get_channel(755722577049026567)
                await channel.send(embed=embed)

    @commands.Cog.listener(name='on_member_join')
    async def anxiety_advert(self, member: discord.Member, guild=None):
        guild = member.guild
        if member.guild.id == 755722576445046806:
            try:
                await member.send("Hey, thank you for joining our server! Please, if you feel so kind, join the host of this bot! Its a super cheap bot host and has amazing hardware!\nhttps://discord.gg/3ZzQ7S2bNE")
            except discord.Forbidden:
                pass

    @commands.group(invoke_without_command=True, usage="tp!blacklist <a:user> <r:user>")
    @commands.check(permissions.is_owner)
    async def blacklist(self, ctx):
        """ Blacklist users from using the bot. Send with no args to see who's blacklisted."""
        conv = commands.UserConverter()
        users = await asyncio.gather(*[conv.convert(ctx, str(_id)) for _id in self.blacklist])
        names = [user.name for user in users]
        await ctx.send('\t'.join(names) or 'No one has been blacklisted')

    @blacklist.command(usage="tp!blacklist a <user>", aliases=["a"])
    @commands.check(permissions.is_owner)
    async def add(self, ctx, user: discord.User):
        """Add a user to blacklist"""
        if user.id == ctx.author.id:
            await ctx.send("You can't blacklist yourself!")
        if user.id in self.blacklist:
            await ctx.send(f"{user} is already blacklisted!")
            await ctx.message.add_reaction('\u274C')
            return
        with open('blacklist.json', 'w') as f:
            self.blacklist.append(user.id)
            json.dump(self.blacklist, f)
        await ctx.send(f"{user} has been blacklisted!")
        await ctx.message.add_reaction('\u2705')

    @blacklist.command(usage="tp!blacklist r <user>", aliases=["r"])
    @commands.check(permissions.is_owner)
    async def remove(self, ctx, user: discord.User):
        """Remove a user from blacklist"""
        if user.id in self.blacklist:
            with open('blacklist.json', 'w') as f:
                self.blacklist.remove(user.id)
                json.dump(self.blacklist, f)
            await ctx.send(f"{user} has been removed from the blacklist.")
            await ctx.message.add_reaction('\u2705')
        else:
            await ctx.send(f"{user} is not blacklisted.")
            await ctx.message.add_reaction('\u274C')

    @blacklist.command(name="clear")
    @commands.check(permissions.is_owner)
    async def blacklist_clear(self, ctx):
        """ Clear the blacklist. """
        self.blacklist = []
        with open('blacklist.json', 'w') as f:
            json.dump(self.blacklist, f)
        await ctx.send("Blacklist cleared")
        
    @commands.check(permissions.is_owner)
    @commands.command()
    async def apt(self, ctx):
        """Check autpost"""
        cursor.execute(f"SELECT DISTINCT hentai_channel FROM guilds WHERE hentai_channel IS NOT NULL")
        for row in cursor.fetchall():
            if row[0] == None:
                return
            else:
                channel = self.bot.get_channel(int(row[0]))
                if channel != None:
                    if not channel.is_nsfw():
                        return
                    else:
                        try:
                            # print(channel)
                            print(channel.id)
                            #mention the guild owner
                            await channel.send(f"{ctx.guild.owner.mention}, I will have to start be using Webhooks for autoposting. Please make sure I have the permission to create a Webhook.\n**If you've already been pinged,just ignore this message.**")
                            await asyncio.sleep(2)
                        except discord.Forbidden:
                            return

    @commands.check(permissions.is_owner)
    @commands.command()
    async def eval(self, ctx, *, body: str):
        """Evaluates a code"""
        async with ctx.channel.typing():
            if 'token' in body:
                await ctx.send("We're no strangers to love \nYou know the rules and so do I \nA full commitment's what I'm thinking of \nYou wouldn't get this from any other guy \nI just wanna tell you how I'm feeling\nGotta make you understand\nNever gonna give you up\nNever gonna let you down\nNever gonna run around and desert you\nNever gonna make you cry\nNever gonna say goodbye\nNever gonna tell a lie and hurt you")
                return
        env = {
            'self': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }
        env.update(globals())
        body = self.cleanup_code(body)
        stdout = io.StringIO()
        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'
        
        embed = discord.Embed(
            title="Evaluation",
            colour=EMBED_COLOUR,
            description="** **"
        )
        
        try:
            exec(to_compile, env)
        except Exception as e:
            await ctx.message.add_reaction('\u274C')
            embed.add_field(name="Error", value=f"```py\n{e.__class__.__name__}: {e}\n```", inline=True)
            # await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')
            await ctx.send("test1")
            await ctx.send(embed=embed)
            return

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            embed.add_field(name='Result', value=f"```py\n{value}{traceback.format_exc()}\n```", inline=True)
            # await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
            await ctx.send("test2")
            await ctx.send(embed=embed)
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass
            if ret is None:
                if value:
                    embed.add_field(name='Result', value=f"```py\n{value}\n```", inline=True)
                    # await ctx.send(f'```py\n{value}\n```')
                    await ctx.send("test3")
                    await ctx.send(embed=embed)
            else:
                self._last_result = ret
                embed.add_field(name='Result', value=f"```py\n{value}{ret}\n```", inline=True)
                # await ctx.send(f'```py\n{value}{ret}\n```')
                await ctx.send("test4")
                await ctx.send(embed=embed)

    @commands.check(permissions.is_owner)
    @commands.command(hidden=True)
    async def ghost(self, ctx):
        try:
            await ctx.message.delete()
        except:
            pass

    @commands.check(permissions.is_owner)
    @commands.command()
    async def test(self, ctx):
        await ctx.send("BIG BALLS")
        raise KeyError

    @commands.command()
    async def owner(self, ctx):
        """ Did you code me? """
        async with ctx.channel.typing():
            try:
                await ctx.message.delete()
            except:
                pass
            if ctx.author.id in self.config.owners:
                return await ctx.send(f"Yes **{ctx.author.name}** \nYou Coded Me ", delete_after=delay)
            if ctx.author.id == 632753468896968764:
                return await ctx.send(f"**{ctx.author.name}**Hi there :)", delete_after=delay)
            await ctx.send(f"no, heck off {ctx.author.name}", delete_after=delay)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def load(self, ctx, *names):
        """ Loads an extension. """
        try:
            await ctx.message.delete(delay=delay)
        except:
            pass
        for name in names:
            try:
                self.bot.load_extension(f"Cogs.{name}")
            except Exception as e:
                await ctx.send(default.traceback_maker(e))
                await ctx.message.add_reaction('\u274C')
                return
            await ctx.message.add_reaction('\u2705')
            await ctx.send(f"Loaded extension **{name}.py**", delete_after=delay)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def unload(self, ctx, *names):
        """ Unloads an extension. """
        try:
            await ctx.message.delete(delay=delay)
        except:
            pass
        for name in names:
            try:
                self.bot.unload_extension(f"Cogs.{name}")
            except Exception as e:
                return await ctx.send(default.traceback_maker(e))
            await ctx.send(f"Unloaded extension **{name}.py** {ctx.author.mention}", delete_after=delay)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def reload(self, ctx, *names):
        """ Reloads an extension. """
        try:
            await ctx.message.delete(delay=delay)
        except:
            pass
        for name in names:
            try:
                self.bot.reload_extension(f"Cogs.{name}")
            except Exception as e:
                await ctx.send(default.traceback_maker(e))
                await ctx.message.add_reaction('\u274C')
                return
            await ctx.message.add_reaction('\u2705')
            await ctx.send(f"Reloaded extension **{name}.py** {ctx.author.mention}", delete_after=delay)

    @commands.command(aliases=["speedtest"])
    @commands.check(permissions.is_owner)
    async def netspeed(self, ctx):
        """Test your servers internet speed.
        Note that this is the internet speed of the server your bot is running on,
        not your internet speed.
        """
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()
        s = speedtest.Speedtest(secure=True)
        the_embed = await ctx.send(embed=self.generate_embed(0, s.results.dict()))
        await loop.run_in_executor(executor, s.get_servers)
        await loop.run_in_executor(executor, s.get_best_server)
        await the_embed.edit(embed=self.generate_embed(1, s.results.dict()))
        await loop.run_in_executor(executor, s.download)
        await the_embed.edit(embed=self.generate_embed(2, s.results.dict()))
        await loop.run_in_executor(executor, s.upload)
        await the_embed.edit(embed=self.generate_embed(3, s.results.dict()))

    @staticmethod
    def generate_embed(step: int, results_dict):
        """Generate the embed."""
        measuring = ":mag: Measuring..."
        waiting = ":hourglass: Waiting..."

        color = 0xff0000
        title = "Measuring internet speed..."
        message_ping = measuring
        message_down = waiting
        message_up = waiting
        if step > 0:
            message_ping = f"**{results_dict['ping']}** ms"
            message_down = measuring
        if step > 1:
            message_down = f"**{results_dict['download'] / 1_000_000:.2f}** mbps"
            message_up = measuring
        if step > 2:
            message_up = f"**{results_dict['upload'] / 1_000_000:.2f}** mbps"
            title = "NetSpeed Results"
            color = discord.Color.green()
        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="Ping", value=message_ping)
        embed.add_field(name="Download", value=message_down)
        embed.add_field(name="Upload", value=message_up)
        return embed

    @commands.command()
    @commands.check(permissions.is_owner)
    async def loadall(self, ctx):
        """Loads all extensions"""
        try:
            await ctx.message.delete(delay=delay)
        except:
            pass
        error_collection = []
        for file in os.listdir("Cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                try:
                    self.bot.load_extension(f"Cogs.{name}",)
                except Exception as e:
                    error_collection.append(
                        [file, default.traceback_maker(e, advance=False)]
                    )
        if error_collection:
            output = "\n".join(
                [f"**{g[0]}** ```diff\n- {g[1]}```" for g in error_collection])
            await ctx.message.add_reaction('\u274C')
            return await ctx.send(
                f"Attempted to load all extensions, was able to but... "
                f"the following failed...\n\n{output}"
            )
        await ctx.message.add_reaction('\u2705')
        await ctx.send(f"Successfully loaded all extensions {ctx.author.mention}", delete_after=delay)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def reloadall(self, ctx):
        """ Reloads all extensions. """
        try:
            await ctx.message.delete(delay=delay)
        except:
            pass
        error_collection = []
        for file in os.listdir("Cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                try:
                    self.bot.reload_extension(f"Cogs.{name}",)
                except Exception as e:
                    error_collection.append(
                        [file, default.traceback_maker(e, advance=False)]
                    )
        if error_collection:
            output = "\n".join(
                [f"**{g[0]}** ```diff\n- {g[1]}```" for g in error_collection])
            await ctx.message.add_reaction('\u274C')
            return await ctx.send(
                f"Attempted to reload all extensions, was able to reload, "
                f"however the following failed...\n\n{output}"
            )
        await ctx.message.add_reaction('\u2705')
        await ctx.send(f"Successfully reloaded all extensions {ctx.author.mention}", delete_after=delay)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def reloadutils(self, ctx, name: str):
        """ Reloads a utils module. """
        try:
            await ctx.message.delete(delay=delay)
        except:
            pass
        name_maker = f"utils/{name}.py"
        try:
            module_name = importlib.import_module(f"utils.{name}")
            importlib.reload(module_name)
        except ModuleNotFoundError:
            return await ctx.send(f"Couldn't find module named **{name_maker}**")
        except Exception as e:
            error = default.traceback_maker(e)
            return await ctx.send(f"Module **{name_maker}** returned error and was not reloaded...\n{error}")
        await ctx.send(f"Reloaded module **{name_maker}**")

    @commands.command()
    @commands.check(permissions.is_owner)
    async def reboot(self, ctx):
        """ Reboot the bot """
        try:
            await ctx.message.delete()
        except:
            pass
        await self.bot.change_presence(status=discord.Status.idle, activity=discord.Activity(type=discord.ActivityType.playing, name="Restarting..."))
        embed = discord.Embed(title="Cya, lmao.",
                              color=EMBED_COLOUR, description="Rebooting... 👌")
        await ctx.send(embed=embed)
        url = "https://panel.ponbus.com/api/client/servers/1acee413/power"

        payload_kill = json.dumps({
            "signal": "kill"
        })
        payload_restart = json.dumps({
            "signal": "restart"
        })
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'{self.config.ponbus}'
        }

        response = requests.request(
            "POST", url, headers=headers, data=payload_restart)
        print(response.text)

        response2 = requests.request(
            "POST", url, headers=headers, data=payload_kill)
        print(response2.text)
        # await sys.exit(0)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def shutdown(self, ctx):
        """completely shut the bot down"""
        try:
            await ctx.message.delete()
        except:
            pass
        await self.bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.playing, name="Shutting down..."))
        embed = discord.Embed(
            title="Cya, lmao.", color=EMBED_COLOUR, description="Shutting Down...👌")
        await ctx.send(embed=embed)
        url = "https://panel.ponbus.com/api/client/servers/1acee413/power"

        payload_kill = json.dumps({
            "signal": "kill"
        })
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'{self.config.ponbus}'
        }

        response2 = requests.request(
            "POST", url, headers=headers, data=payload_kill)
        print(response2.text)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def pull(self, ctx):
        try:
            await ctx.message.delete(delay=delay)
        except:
            pass
        async with ctx.channel.typing():
            #this a real pain in the ass
            await asyncio.create_subprocess_shell('git pull')
            await ctx.send("Code has been pulled from github.", delete_after=delay)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def debug(self, ctx, *, arg):
        await ctx.invoke(self.bot.get_command('jsk debug'), command_string=arg)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def source(self, ctx, arg):
        await ctx.invoke(self.bot.get_command('jsk source'), command_name=arg)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def dm(self, ctx, user: discord.User, *, message):
        """DMs the user of your choice.
        If you somehow found out about this command, it is owner ONLY
        you cannot use it."""
        if user.bot:
            return await ctx.send("I can't DM bots.\nI mean I can, I just don't want to...")
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        embed2 = discord.Embed(
            title=f"New message to {user}", description=message)
        embed2.set_footer(
            text=f"tp!dm {user.id} ", icon_url=ctx.author.avatar_url)
        embed = discord.Embed(
            title=f"New message From {ctx.author.name}", description=message)
        embed.set_footer(text=f"To contact me, just DM the bot",
                         icon_url=ctx.author.avatar_url)
        try:
            await user.send(embed=embed)
            await ctx.send(embed=embed2)
        except discord.Forbidden:
            await ctx.send("This user might be having DMs blocked.", delete_after=delay)

    @commands.command()
    @commands.check(permissions.is_owner)
    async def toggle(self, ctx, *, command):
        command = self.bot.get_command(command)

        if command is None:
            await ctx.send("I can't find a command with that name!")

        elif ctx.command == command:
            await ctx.send("You cannot disable this command.")

        else:
            command.enabled = not command.enabled
            ternary = "enabled" if command.enabled else "disabled"
            await ctx.send(f"I have {ternary} {command.qualified_name} for you!")

    @commands.group(case_insensitive=True)
    @commands.check(permissions.is_owner)
    async def change(self, ctx):
        try:
            await ctx.message.delete(delay=delay)
        except:
            pass
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @change.command(name="username")
    @commands.check(permissions.is_owner)
    async def change_username(self, ctx, *, name: str):
        """ Change username. """
        try:
            await ctx.message.delete()
        except:
            pass
        try:
            await self.bot.user.edit(username=name)
            await ctx.send(f"Successfully changed username to **{name}** {ctx.author.mention}. Lets hope I wasn't named something retarded", delete_after=delay)
        except discord.HTTPException as err:
            await ctx.send(err)

    @change.command(name="nickname")
    @commands.check(permissions.is_owner)
    async def change_nickname(self, ctx, *, name: str = None):
        """ Change nickname. """
        try:
            await ctx.message.delete()
        except:
            pass
        try:
            await ctx.guild.me.edit(nick=name)
            if name:
                await ctx.send(f"Successfully changed nickname to **{name}**", delete_after=delay)
            else:
                await ctx.send("Successfully removed nickname", delete_after=delay)
        except Exception as err:
            await ctx.send(err)

    @change.command(name="avatar")
    @commands.check(permissions.is_owner)
    async def change_avatar(self, ctx, url: str = None):
        """ Change avatar. """
        try:
            await ctx.message.delete()
        except:
            pass
        if url is None and len(ctx.message.attachments) == 1:
            url = ctx.message.attachments[0].url
        else:
            url = url.strip('<>') if url else None
        try:
            bio = await http.get(url, res_method="read")
            await self.bot.user.edit(avatar=bio)
            await ctx.send(f"Successfully changed the avatar. Currently using:\n{url}", delete_after=delay)
        except aiohttp.InvalidURL:
            await ctx.send("The URL is invalid...", delete_after=delay)
        except discord.InvalidArgument:
            await ctx.send("This URL does not contain a useable image", delete_after=delay)
        except discord.HTTPException as err:
            await ctx.send(err)
        except TypeError:
            await ctx.send("You need to either provide an image URL or upload one with the command", delete_after=delay)

    @commands.check(permissions.is_owner)
    @commands.command()
    async def ownersay(self, ctx, *, message):
        try:
            await ctx.message.delete()
        except:
            pass
        await ctx.send(message)

    param_converter = ArgumentConverter(
        age=OptionalArgument(
            int,
            default=0
        ),
        uses=OptionalArgument(
            int,
            default=0
        ),
        temp=OptionalArgument(
            bool,
            default=False
        ),
        unique=OptionalArgument(
            bool,
            default=True
        ),
    )

    @commands.check(permissions.is_owner)
    @commands.command()
    async def geninvite(self, ctx, guild: int, *, params: param_converter = param_converter.defaults()):
        try:
            guild = self.bot.get_guild(guild)
            first_channel = guild.text_channels[0]
            invite = await first_channel.create_invite(
                max_age=params['age'],
                max_uses=params['uses'],
                temporary=params['temp'],
                unique=params['unique'],
                reason=f"Created by {str(ctx.author)}"
            )
            await ctx.send(str(invite))
        except:
            await ctx.send(f"```{traceback.format_exc()}```")

    @commands.check(permissions.is_owner)
    @commands.command(hidden=True)
    async def helptest(self, ctx):
        for cog in self.bot.extensions:
            await ctx.send(cog[5:])
        # embed = discord.Embed(title=f"{self.bot.user.name} | Help", description="Test")
        # for module in self.extensions:
        #     str1 = module[5:]
        #     strf = str1.replace("ku", "")
        #     # embed.add_field(name=f"{strf}", value="test")
        #     await ctx.send(f"{strf}")
        #     # await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.guild is None:
            return
        else:
            pass
        if not ctx.guild.chunked:
            try:
                await ctx.guild.chunk()
            except:
                pass
        else:
            pass

    @commands.Cog.listener(name='on_message')
    async def linkblacklist(self, message):
        if message.guild is None:
            return
        me = self.bot.get_user(101118549958877184)
        blacklisted_links = ["cehfhc.dateshookp.com",
                             "streancommunnity.ru", "steancomunnity.ru",
                             "steancomunlty.me", "stearncomminuty.ru",
                             "steamcommunytu.ru", "steamconmmuntiy.ru",
                             "steamcomminytu.ru", "steamcommutiny.com",
                             "streancommunnity.com", "steancomunnity.com",
                             "steancomunlty.me", "stearncomminuty.com",
                             "steamcommunytu.com", "steamconmmuntiy.com",
                             "steamcomminytu.com", "bit.ly/Discord--Nitro-Generator",
                             "store-steampowered.ru", "steamnconnmunity.com",
                             "discordgivenitro.com", " https://steamcommunity",
                             "http://steamcommunity", "freenitros.ru", "freenitros.com"]
        
        if any(elem in message.content for elem in blacklisted_links):
            await me.send(f"**New Scammer**\n**{message.guild.id}** | **{message.guild.name}**\n{message.author.id}\n`{message.content}`\n")
            try:
                await message.delete()
            except:
                pass

    # @commands.Cog.listener(name='on_message')
    # async def FuckFear(self, message):
    #     if message.author.id == 683530527239962627:
    #         try:
    #             await message.delete()
    #         except:
    #             pass
    #     else:
    #         return


def setup(bot):
    bot.add_cog(Admin(bot))
