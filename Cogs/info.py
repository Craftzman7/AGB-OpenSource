import datetime
import aiohttp
import json
import os
import pathlib
import random
import time
from typing import List, Union

import discord
from discord import app_commands
import googletrans
import psutil
import requests
from discord.ext import commands
from index import (
    EMBED_COLOUR,
    config,
    cursor_n,
    delay,
    emojis,
    mydb_n,
)
from Manager.commandManager import cmd
from utils import default, permissions


def list_items_in_english(l: List[str], oxford_comma: bool = True) -> str:
    """
    Produce a list of the items formatted as they would be in an English sentence.
    So one item returns just the item, passing two items returns "item1 and item2" and
    three returns "item1, item2, and item3" with an optional Oxford comma.
    """
    return ", ".join(
        l[:-2] + [((oxford_comma and len(l) != 2) * "," + " and ").join(l[-2:])]
    )


class Information(commands.Cog, name="info"):
    """Info commands for info related things"""

    def __init__(self, bot):
        """Info commands for info related things"""
        self.bot = bot
        self.trans = googletrans.Translator()
        self.config = default.get("config.json")
        self.lunar_headers = {f"{config.lunarapi.header}": f"{config.lunarapi.token}"}
        # self.thanks = default.get("thanks.json")
        # self.blist_api = blist.Blist(bot, token=self.config.blist)
        self.process = psutil.Process(os.getpid())

    async def cog_unload(self):
        self.process.stop()

    def parse_weather_data(self, data):
        data = data["main"]
        del data["humidity"]
        del data["pressure"]
        return data

    def weather_message(self, data, location):
        location = location.title()
        embed = discord.Embed(
            title=f"{location} Weather",
            description=f"Here is the weather data for {location}.",
            color=EMBED_COLOUR,
        )
        embed.add_field(
            name=f"Temperature", value=f"{str(data['temp'])}° F", inline=False
        )
        embed.add_field(
            name=f"Minimum temperature",
            value=f"{str(data['temp_min'])}° F",
            inline=False,
        )
        embed.add_field(
            name=f"Maximum temperature",
            value=f"{str(data['temp_max'])}° F",
            inline=False,
        )
        embed.add_field(
            name=f"Feels like", value=f"{str(data['feels_like'])}° F", inline=False
        )
        return embed

    def error_message(self, location):
        location = location.title()
        return discord.Embed(
            title=f"Error caught!",
            description=f"There was an error finding weather data for {location}.",
            color=EMBED_COLOUR,
        )

    async def create_embed(self, ctx, error):
        embed = discord.Embed(
            title=f"Error Caught!", color=0xFF0000, description=f"{error}"
        )
        embed.set_thumbnail(url=self.bot.user.avatar)
        await ctx.send(embed=embed)

    class MemberConverter(commands.MemberConverter):
        async def convert(self, ctx, argument):
            try:
                return await super().convert(ctx, argument)
            except commands.BadArgument:
                members = [
                    member
                    for member in ctx.guild.members
                    if member.display_name.lower().startswith(argument.lower())
                ]
                if len(members) == 1:
                    return members[0]
                else:
                    raise commands.BadArgument(
                        f"{len(members)} members found, please be more specific."
                    )

    @commands.command(usage="`tp!weather location`")
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def Weather(self, ctx, *, location=None):
        """Get weather data for a location
        You can use your zip code or your city name.
        Ex; `tp!weather City / Zip Code` or `tp!weather City,Town`"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return
        if location == None:
            await ctx.send("Please send a valid location.")
            return

        URL = f"http://api.openweathermap.org/data/2.5/weather?q={location.lower()}&appid={config.Weather}&units=imperial"
        try:
            data = json.loads(requests.get(URL).content)
            data = self.parse_weather_data(data)
            await ctx.send(embed=self.weather_message(data, location))
        except KeyError:
            await ctx.send(embed=self.error_message(location))

    @app_commands.command(description="Convert Fahrenheit to Celcius")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def f2c(self, interaction, *, temp: str, ephemeral: bool = False):
        if temp is None:
            await interaction.response.send_message(
                "Please send a valid temperature.", ephemeral=True
            )
            return

        temp = float(temp)
        cel = (temp - 32) * (5 / 9)
        await interaction.response.send_message(
            f"{temp}°F is {round(cel, 2)}°C", ephemeral=ephemeral
        )

    @app_commands.command(description="Convert Celcius to Fahrenheit")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def c2f(self, interaction, *, temp: str, ephemeral: bool = False):
        """Convert Celcius to Fahrenheit"""
        if temp is None:
            await interaction.response.send_message(
                "Please send a valid temperature.", ephemeral=True
            )
            return

        temp = float(temp)
        fah = (temp * (9 / 5)) + 32
        await interaction.response.send_message(
            f"{temp}°C is {round(fah, 2)}°F", ephemeral=ephemeral
        )

    @commands.command()
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def uptime(self, ctx):
        """Get the uptime of the bot in days, hours, minutes, and seconds"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        embed = discord.Embed(
            title=f"Uptime: {default.uptime(start_time=self.bot.launch_time)}"
        )
        await ctx.send(embed=embed)

    @commands.command(usage="`tp!vote`")
    @permissions.dynamic_ownerbypass_cooldown(1, 3, commands.BucketType.user)
    async def Vote(self, ctx):
        """Vote for the bot"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        embed = discord.Embed(color=EMBED_COLOUR, timestamp=ctx.message.created_at)
        embed.set_author(
            name=ctx.bot.user.name,
            icon_url=ctx.bot.user.avatar,
        )
        embed.set_thumbnail(url=ctx.bot.user.avatar)
        embed.add_field(
            name="Thank You!", value=f"[Click Me]({config.Vote})", inline=True
        )
        embed.add_field(
            name=f"{ctx.bot.user.name} was made with love by: {'' if len(self.config.owners) == 1 else ''}",
            value=", ".join(
                [str(await self.bot.fetch_user(x)) for x in self.config.owners]
            ),
            inline=False,
        )
        embed.set_thumbnail(url=ctx.author.avatar)
        try:
            await ctx.send(embed=embed)
        except Exception as err:
            await ctx.send(err)

    @app_commands.command(description="ping the bot")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def ping(self, interaction, ephemeral: bool = False):
        embed = discord.Embed(color=EMBED_COLOUR)
        embed.set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar,
        )
        embed.add_field(
            name="Ping", value=f"{round(self.bot.latency * 1000)}ms", inline=True
        )
        embed.set_thumbnail(url=interaction.user.avatar)
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @commands.command(usage="`tp!todo`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def Todo(self, ctx):
        """Stuff to come, future updates i have planned for this bot"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        channel = self.bot.get_channel(784053877040873522)
        message = await channel.fetch_message(784054226439372832)
        await ctx.send(message.content)

    @commands.command(
        aliases=["supportserver", "feedbackserver", "support"], usage="`tp!support`"
    )
    @commands.bot_has_permissions(embed_links=True)
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def Botserver(self, ctx):
        """Get an invite to our support server!"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        if (
            isinstance(ctx.channel, discord.DMChannel)
            or ctx.guild.id != 755722576445046806
        ):
            embed = discord.Embed(
                color=ctx.author.color, timestamp=ctx.message.created_at
            )
            embed.set_author(
                name=ctx.bot.user.name,
                icon_url=ctx.bot.user.avatar,
            )
            embed.add_field(
                name="You can join here:", value=f"[Click Here.]({config.Server})"
            )
            return await ctx.send(embed=embed)
        embed = discord.Embed(color=ctx.author.color, timestamp=ctx.message.created_at)
        embed.set_author(
            name=ctx.bot.user.name,
            icon_url=ctx.bot.user.avatar,
        )
        embed.add_field(
            name=f"{ctx.author.name}, you're already in it.",
            value=f"Regardless, a bot invite is [here]({config.Invite}) \n A server invite is also [here]({config.Server})",
        )
        await ctx.send(embed=embed)

    @app_commands.command(description="Invite me to your server")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def invite(self, interaction, ephemeral: bool = False):
        embed = discord.Embed(color=EMBED_COLOUR)
        embed.set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar,
        )
        embed.set_thumbnail(url=self.bot.user.avatar)
        embed.add_field(
            name="Bot Invite", value=f"[Invite Me!]({config.Invite})", inline=True
        )
        embed.add_field(
            name=f"Support Server",
            value=f"[Join Our Server!!]({config.Server})",
            inline=True,
        )
        embed.add_field(
            name=f"{self.bot.user.name} was made with love by: {'' if len(self.config.owners) == 1 else ''}",
            value=", ".join(
                [str(await self.bot.fetch_user(x)) for x in self.config.owners]
            ),
            inline=False,
        )
        embed.set_thumbnail(url=interaction.user.avatar)
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    # @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    # @commands.command(usage="`tp!source`")
    # async def Source(self, ctx):
    #     """Who Coded This Bot """
    #     embed = discord.Embed(color=EMBED_COLOUR,
    #                           timestamp=ctx.message.created_at)
    #     embed.add_field(name="**The repo is private**",
    #                     value=f"This command really doesn't have a purpose. \nBut its here for when the repo does become public.")
    #     embed.add_field(name="Look at these",
    #                     value=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})", inline=False)
    #     await ctx.send(embed=embed)

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=["info", "stats", "status"], usage="`tp!about`")
    @commands.bot_has_permissions(embed_links=True)
    async def About(self, ctx):
        """About the bot"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        discord_version = discord.__version__
        chunked = []
        for guild in self.bot.guilds:
            if guild.chunked:
                chunked.append(guild)
        msg = await ctx.send("Fetching...")
        ramUsage = self.process.memory_full_info().rss / 1024**2
        intervals = (
            ("w", 604800),  # 60 * 60 * 24 * 7
            ("d", 86400),  # 60 * 60 * 24
            ("h", 3600),  # 60 * 60
            ("m", 60),
            ("s", 1),
        )

        def display_time(seconds, granularity=2):
            result = []

            for name, count in intervals:
                value = seconds // count
                if value:
                    seconds -= value * count
                    if value == 1:
                        name = name.rstrip("s")
                    result.append("{}{}".format(value, name))
            return " ".join(result[:granularity])

        async def lunar_api_stats(self):
            async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
                try:
                    async with s.get(f"https://lunardev.group/api/ping") as r:
                        j = await r.json()
                        seconds = j["uptime"]

                        # str(await lunar_api_stats(self)).partition(".")

                        if r.status == 200:
                            return display_time(int(str(seconds).partition(".")[0]), 4)
                        elif r.status == 503:
                            return "❌ API Error"
                        else:
                            return "❌ API Error"
                except:
                    return "❌ API Error"

        async def lunar_api_cores(self):
            async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
                try:
                    async with s.get(f"https://lunardev.group/api/ping") as r:
                        j = await r.json()
                        cores = j["system"]["cores"]

                        # str(await lunar_api_stats(self)).partition(".")

                        if r.status == 200:
                            return cores
                        elif r.status == 503:
                            return "❌ API Error"
                        else:
                            return "❌ API Error"
                except:
                    return "❌ API Error"

        async def lunar_api_files(self):
            async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
                try:
                    async with s.get(f"https://lunardev.group/api/ping") as r:
                        j = await r.json()
                        files = j["images"]["total"]

                        # str(await lunar_api_stats(self)).partition(".")

                        if r.status == 200:
                            return f"{int(files):,}"
                        elif r.status == 503:
                            return "❌ API Error"
                        else:
                            return "❌ API Error"
                except:
                    return "❌ API Error"

        async def lunar_system_uptime(self):
            async with aiohttp.ClientSession(headers=self.lunar_headers) as s:
                try:
                    async with s.get(f"https://lunardev.group/api/ping") as r:
                        j = await r.json()
                        uptime = j["system"]["uptime"]

                        # str(await lunar_api_stats(self)).partition(".")

                        if r.status == 200:
                            return display_time(int(str(uptime).partition(".")[0]), 4)
                        elif r.status == 503:
                            return "❌ API Error"
                        else:
                            return "❌ API Error"
                except:
                    return "❌ API Error"

        async def line_count(self):
            total = 0
            file_amount = 0
            ENV = "env"

            for path, _, files in os.walk("."):
                for name in files:
                    file_dir = str(pathlib.PurePath(path, name))
                    # ignore env folder and not python files.
                    if not name.endswith(".py") or ENV in file_dir:
                        continue
                    if "__pycache__" in file_dir:
                        continue
                    if ".git" in file_dir:
                        continue
                    if ".local" in file_dir:
                        continue
                    if ".config" in file_dir:
                        continue
                    if "?" in file_dir:
                        continue
                    if ".cache" in file_dir:
                        continue
                    file_amount += 1
                    with open(file_dir, "r", encoding="utf-8") as file:
                        for line in file:
                            if not line.strip().startswith("#") or not line.strip():
                                total += 1
            return f"{total:,} lines, {file_amount:,} files"

        # create the cpu usage embed
        cpu = psutil.cpu_percent()
        cpu_box = default.draw_box(round(cpu), ":blue_square:", ":black_large_square:")
        ramlol = round(ramUsage) // 10
        ram_box = default.draw_box(ramlol, ":blue_square:", ":black_large_square:")
        GUILD_MODAL = f"""{len(ctx.bot.guilds)} Guilds are seen,\n{default.commify(len(self.bot.users))} users."""
        PERFORMANCE_MODAL = f"""
        `RAM Usage: {ramUsage:.2f}MB / 1GB scale`
        {ram_box}
        `CPU Usage: {cpu}%`
        {cpu_box}"""
        API_UPTIME = await lunar_api_stats(self)
        BOT_INFO = f"""Latency: {round(self.bot.latency * 1000, 2)}ms\nLoaded CMDs: {len([x.name for x in self.bot.commands])}\nMade: <t:1592620263:R>\n{await line_count(self)}\nUptime: {default.uptime(start_time=self.bot.launch_time)}"""
        API_INFO = f"""API Uptime: {API_UPTIME}\nCPU Cores: {await lunar_api_cores(self)}\nTotal Images: {await lunar_api_files(self)}"""
        SYS_INFO = f"""System Uptime: {await lunar_system_uptime(self)}\nCPU Cores: {await lunar_api_cores(self)}"""

        embed = discord.Embed(
            color=EMBED_COLOUR,
            description=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate})",
            timestamp=ctx.message.created_at,
        )
        embed.set_thumbnail(url=ctx.bot.user.avatar)
        embed.add_field(
            name="Performance Overview", value=PERFORMANCE_MODAL, inline=False
        )
        embed.add_field(
            name="Guild Information",
            value=GUILD_MODAL,
            inline=False,
        )
        if len(chunked) == len(self.bot.guilds):
            embed.add_field(
                name="\u200b", value=f"**All servers are cached!**", inline=False
            )
        else:
            embed.add_field(
                name="\u200b",
                value=f"**{len(chunked)}** / **{len(self.bot.guilds)}** servers are cached.",
            )
        embed.add_field(name="Bot Information", value=BOT_INFO, inline=False)
        embed.add_field(name="API Information", value=API_INFO, inline=False)
        embed.add_field(name="System Information", value=SYS_INFO, inline=False)
        embed.set_image(
            url="https://media.discordapp.net/attachments/940897271120273428/954507474394808451/group.gif"
        )
        embed.set_footer(
            text=f"Made with ❤️ by the Lunar Development team.\nLibrary used: Discord.py{discord_version}"
        )
        await msg.edit(
            content=f"ℹ About **{ctx.bot.user}** | **{self.config.version}**",
            embed=embed,
        )

    @commands.check(permissions.is_owner)
    @commands.command(aliases=["guilds"], hidden=True)
    async def Servers(self, ctx):
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        await ctx.send(
            "alright, fetching all the servers now, please wait, this can take some time...",
            delete_after=delay,
        )
        filename = random.randint(1, 20)
        f = open(f"{str(filename)}.txt", "a", encoding="utf-8")
        try:
            for guild in self.bot.guilds:
                data = f"Guild Name:{(guild.name)}, Guild ID:{(guild.id)}, Server Members:{(len(guild.members))}, Bots: {len([bot for bot in guild.members if bot.bot])}"
                f.write(data + "\n")
                #        await asyncio.sleep(5)
                continue
        except:
            pass
        f.close()
        try:
            await ctx.send(file=discord.File(f"{str(filename)}.txt"))
        except:
            pass
        os.remove(f"{filename}.txt")

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command(usage="`tp!say message`")
    @commands.bot_has_permissions(embed_links=True)
    async def Say(self, ctx, *, message):
        """Speak through the bot uwu"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return
        # if message.
        try:
            await ctx.message.delete()
        except:
            pass
        await ctx.send(message)

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command(usage="`tp!policy`")
    @commands.bot_has_permissions(embed_links=True)
    async def Policy(self, ctx):
        """Privacy Policy"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        embed = discord.Embed(color=EMBED_COLOUR, timestamp=ctx.message.created_at)
        embed.set_author(
            name=ctx.bot.user.name,
            icon_url=ctx.bot.user.avatar,
        )
        embed.set_thumbnail(url=ctx.bot.user.avatar)
        embed.add_field(
            name="Direct Link To The Privacy Policy ",
            value=f"[Click Here](https://gist.github.com/Motzumoto/2f25e114533a35d86078018fdc2dd283)",
            inline=True,
        )
        embed.add_field(
            name="Backup To The Policy ",
            value=f"[Click Here](https://pastebin.com/J5Zj8U1q)",
            inline=False,
        )
        embed.add_field(
            name=f"Support If You Have More Questions",
            value=f"[Click Here To Join]({config.Server})",
            inline=True,
        )
        embed.add_field(
            name=f"{ctx.bot.user.name} was made with love by: {'' if len(self.config.owners) == 1 else ''}",
            value=", ".join(
                [str(await self.bot.fetch_user(x)) for x in self.config.owners]
            ),
            inline=False,
        )
        embed.add_field(
            name="Look at these",
            value=f"[Add me]({config.Invite}) | [Support]({config.Server}) | [Vote]({config.Vote}) | [Donate]({config.Donate}) ",
            inline=False,
        )
        await ctx.send(embed=embed)

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command(usage="`tp!profile`")
    @commands.bot_has_permissions(embed_links=True)
    async def profile(self, ctx, user: Union[MemberConverter, discord.User] = None):
        """Show your user profile"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        usr = user or ctx.author

        msg = await ctx.send("Fetching...")

        cursor_n.execute(f"SELECT * FROM public.usereco WHERE \"userid\" = '{usr.id}'")
        usereco = cursor_n.fetchall()

        try:
            user_balance = f"${int(usereco[0][1]):,}"
        except:
            user_balance = "$0"
            pass
        try:
            user_bank = f"${int(usereco[0][2]):,}"
        except:
            user_bank = "$0"
            pass
        mydb_n.commit()
        try:
            cursor_n.execute(f"SELECT * FROM public.badges WHERE userid = '{usr.id}'")
            userdb = cursor_n.fetchall()
            badges = ""
            if userdb[0][1] != "false":
                badges += f"{emojis.dev}"
            if userdb[0][2] != "false":
                badges += f" {emojis.admin}"
            if userdb[0][3] != "false":
                badges += f" {emojis.mod}"
            if userdb[0][4] != "false":
                badges += f" {emojis.partner}"
            if userdb[0][5] != "false":
                badges += f" {emojis.support}"
            if userdb[0][6] != "false":
                badges += f" {emojis.friend}"
            if (
                userdb[0][1] == "false"
                and userdb[0][2] == "false"
                and userdb[0][3] == "false"
                and userdb[0][4] == "false"
                and userdb[0][5] == "false"
                and userdb[0][6] == "false"
            ):
                badges += ""
        except:
            badges += ""
            pass

        mydb_n.commit()

        cursor_n.execute(f"SELECT * FROM public.users WHERE userid = '{usr.id}'")
        udb = cursor_n.fetchall()

        usedCommands = ""
        if int(udb[0][1]) >= 0:
            usedCommands += f"{udb[0][1]}"

        # **Profile Info**\nBadges: {badges}\n\n
        title = f"{usr.name}#{usr.discriminator}"
        description = f"""{badges}\n\n**💰 Economy Info**
        `Balance`: **{user_balance}**
        `Bank`: **{user_bank}**
        
        **📜 Misc Info**
        `Commands Used`: **{usedCommands}**
        
        **<:users:770650885705302036> Overview**
        `User Bio`\n{udb[0][2]}"""

        embed = discord.Embed(title=title, color=EMBED_COLOUR, description=description)
        embed.set_thumbnail(url=usr.avatar)
        await msg.edit(content="", embed=embed)

    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    @commands.command(usage="`tp!bio new_bio`")
    @commands.bot_has_permissions(embed_links=True)
    async def bio(self, ctx, *, bio=None):
        """Set your profile bio"""
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        if bio is None:
            await ctx.send("Incorrect usage. Check the usage below:", delete_after=10)
            await ctx.send_help(str(ctx.command))
            ctx.command.reset_cooldown(ctx)
            return

        cursor_n.execute(f"SELECT * FROM public.users WHERE userid = '{ctx.author.id}'")
        cursor_n.execute(
            f"UPDATE public.users SET bio = '{bio}' WHERE userid = '{ctx.author.id}'"
        )
        mydb_n.commit()
        embed = discord.Embed(
            title="User Bio",
            color=EMBED_COLOUR,
            description=f"Your bio has been set to: `{bio}`",
        )
        await ctx.send(embed=embed)

    @commands.command(usage="`tp!timestamp <MM/DD/YYYY HH:MM:SS>`")
    @permissions.dynamic_ownerbypass_cooldown(1, 5, commands.BucketType.user)
    async def timestamp(self, ctx, date, time=None):
        """
        Displays given time in all Discord timestamp formats.
        Example: 12/22/2005 02:20:00
        You don't need to specify time. It will automatically round it to midnight.
        """
        cmdEnabled = cmd(str(ctx.command.name).lower(), ctx.guild.id)
        if cmdEnabled:
            await ctx.send(":x: This command has been disabled!")
            return

        if time is None:
            time = "00:00:00"

        datetime_object = datetime.datetime.strptime(
            f"{date} {time}", "%m/%d/%Y %H:%M:%S"
        )
        uts = str(datetime_object.timestamp())[:-2]
        await ctx.send(
            embed=discord.Embed(
                title="Here's the timestamp you asked for",
                color=EMBED_COLOUR,
                description=f"""
                Short Time: <t:{uts}:t> | \\<t:{uts}:t>
                Long Time: <t:{uts}:T> | \\<t:{uts}:T>
                Short Date: <t:{uts}:d> | \\<t:{uts}:d>
                Long Date: <t:{uts}:D> | \\<t:{uts}:D>
                Short Date/Time: <t:{uts}:f> | \\<t:{uts}:f>
                Long Date/Time: <t:{uts}:F> | \\<t:{uts}:F>
                Relative Time: <t:{uts}:R> | \\<t:{uts}:R>
                """,
            ),
        )


async def setup(bot):
    await bot.add_cog(Information(bot))
