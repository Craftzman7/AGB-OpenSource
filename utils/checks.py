import aiohttp
import discord
from discord.ext import commands

from typing import Optional

import discord
from typing import List, Optional
from discord.ext import commands


from utils import default
from utils.default import log

owners = default.get("config.json").owners
config = default.get("config.json")
TOP_GG_TOKEN = config.topgg


async def check_permissions(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    resolved = ctx.channel.permissions_for(ctx.author)
    return check(
        getattr(resolved, name, None) == value for name, value in perms.items()
    )


def has_permissions(*, check=all, **perms):
    async def pred(ctx):
        return await check_permissions(ctx, perms, check=check)

    return commands.check(pred)


async def check_guild_permissions(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    if ctx.guild is None:
        return False

    resolved = ctx.author.guild_permissions
    return check(
        getattr(resolved, name, None) == value for name, value in perms.items()
    )


async def send_embed(ctx, embed):
    """
    Function that handles the sending of embeds
    -> Takes context and embed to send
    - tries to send embed in channel
    - tries to send normal message when that fails
    - tries to send embed private with information abot missing permissions
    If this all fails: https://youtu.be/dQw4w9WgXcQ
    """
    try:
        await ctx.send(
            embed=embed,
        )
    except discord.errors.Forbidden:
        try:
            await ctx.send(
                "Hey, seems like I can't send embeds. Please check my permissions :)"
            )
        except discord.errors.Forbidden:
            try:
                await ctx.author.send(
                    f"Hey, seems like I can't send any message in {ctx.channel.name} on {ctx.guild.name}\n"
                    f"May you inform the server team about this issue?",
                    embed=embed,
                )
            except discord.errors.Forbidden:
                pass


def has_guild_permissions(*, check=all, **perms):
    async def pred(ctx):
        return await check_guild_permissions(ctx, perms, check=check)

    return commands.check(pred)


class NotVoted(commands.CheckFailure):
    """Exception raised when an operation does not work without a user voting

    This inherits from :exc:`CheckFailure`
    """

    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(
            message
            or "You need to vote to use this command, vote [here](https://top.gg/bot/723726581864071178/vote)"
        )


class MusicGone(commands.CheckFailure):
    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(
            message
            or "Music is unavailable!\nThe music system is currently unavailable. The devs are working hard on fixing it!"
        )


async def check_voter(user_id):
    if user_id in owners:
        return True
    async with aiohttp.ClientSession() as s:
        async with s.get(
            f"https://top.gg/api/bots/723726581864071178/check?userId={user_id}",
            headers={"Authorization": TOP_GG_TOKEN, "Content-Type": "application/json"},
        ) as r:
            vote = await r.json()
            if vote["voted"] == 1:
                log(f"{user_id} voted")
                return True
            else:
                log(f"{user_id} not voted")
                return False


def voter_only():
    async def predicate(ctx):
        if ctx.author.id in owners:
            return True
        check_vote = await check_voter(ctx.author.id)
        if not check_vote:
            raise NotVoted(
                "You need to vote to use this command, vote [here](https://top.gg/bot/723726581864071178/vote)"
            )
        return True

    return commands.check(predicate)


# These do not take channel overrides into account


def is_mod():
    async def pred(ctx):
        return await check_guild_permissions(ctx, {"manage_guild": True})

    return commands.check(pred)


def is_admin():
    async def pred(ctx):
        return await check_guild_permissions(ctx, {"administrator": True})

    return commands.check(pred)


def mod_or_permissions(**perms):
    perms["manage_guild"] = True

    async def predicate(ctx):
        return await check_guild_permissions(ctx, perms, check=any)

    return commands.check(predicate)


def admin_or_permissions(**perms):
    perms["administrator"] = True

    async def predicate(ctx):
        return await check_guild_permissions(ctx, perms, check=any)

    return commands.check(predicate)


def is_in_guilds(*guild_ids):
    def predicate(ctx):
        guild = ctx.guild
        if guild is None:
            return False
        return guild.id in guild_ids

    return commands.check(predicate)


class Paginator(discord.ui.View):
    def __init__(self, ctx: commands.Context, embeds: List[discord.Embed]):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.embeds = embeds
        self.current = 0

    async def edit(self, msg, pos):
        em = self.embeds[pos]
        em.set_footer(text=f"Page: {pos+1}/{len(self.embeds)}")
        await msg.edit(embed=em)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.blurple)
    async def bac(self, b, i):
        if self.current == 0:
            return
        await self.edit(i.message, self.current - 1)
        self.current -= 1

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.blurple)
    async def stap(self, b, i):
        await i.message.delete()

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.blurple)
    async def nex(self, b, i):
        if self.current + 1 == len(self.embeds):
            return
        await self.edit(i.message, self.current + 1)
        self.current += 1

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message("Not your command", ephemeral=True)
