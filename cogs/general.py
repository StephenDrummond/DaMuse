"""General commands, and the bot's `!help`.

The help text comes from each command: `brief` is its line in the `!help`
overview, `usage` its arguments, and the docstring the details shown by
`!help <command>`. Docstrings are unwrapped for Discord (see `unwrap`), so
they can be wrapped normally in the source."""

import difflib
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import discord
from discord.ext import commands

INTRO = (
    "I play music for everyone in your voice channel, picking songs from the "
    "combined taste of whoever is listening."
)

# Order and grouping of the `!help` overview. Commands not listed here go
# under FALLBACK_SECTION, so a new command is never left out.
SECTIONS = (
    ("Playing", ("play", "switch", "skip", "stop")),
    ("Feedback", ("like", "dislike")),
    ("Other", ("hello", "help")),
)
FALLBACK_SECTION = "Other"

COLOUR = discord.Colour.blurple()

HELP_DOC = """Show every command, or the details of one.

Examples:
- `!help`
- `!help play`"""


def usage_line(command: commands.Command, prefix: str) -> str:
    """`!play [song]`: the explicit `usage` if set, else the signature."""
    usage = command.usage if command.usage is not None else command.signature
    return f"{prefix}{command.qualified_name} {usage}".rstrip()


def summary(command: commands.Command) -> str:
    return command.brief or command.short_doc or "No description yet."


def unwrap(text: str) -> str:
    """Join source-wrapped lines so Discord reflows them. Blank lines separate
    paragraphs, and lines starting with "- " stay on their own line."""
    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        lines: List[str] = []
        for raw in paragraph.splitlines():
            line = raw.strip()
            if not line:
                continue
            if lines and not line.startswith("- "):
                lines[-1] += " " + line
            else:
                lines.append(line)
        if lines:
            paragraphs.append("\n".join(lines))
    return "\n\n".join(paragraphs)


def command_lines(cmds: Iterable[commands.Command], prefix: str) -> str:
    return "\n".join(f"`{usage_line(c, prefix)}` — {summary(c)}" for c in cmds)


def overview_embed(cmds: Iterable[commands.Command], prefix: str) -> discord.Embed:
    remaining = {c.name: c for c in cmds}
    sections: Dict[str, List[commands.Command]] = {}
    for title, names in SECTIONS:
        sections[title] = [remaining.pop(n) for n in names if n in remaining]
    sections.setdefault(FALLBACK_SECTION, []).extend(
        sorted(remaining.values(), key=lambda c: c.name)
    )

    embed = discord.Embed(title="DaMuse commands", description=INTRO, colour=COLOUR)
    for title, section in sections.items():
        if section:
            embed.add_field(
                name=title, value=command_lines(section, prefix), inline=False
            )
    embed.set_footer(
        text=f"Type {prefix}help <command> for details, e.g. {prefix}help play"
    )
    return embed


def command_embed(command: commands.Command, prefix: str) -> discord.Embed:
    description = unwrap(command.help) if command.help else summary(command)
    embed = discord.Embed(
        title=usage_line(command, prefix), description=description, colour=COLOUR
    )
    if command.aliases:
        embed.add_field(
            name="Also works as",
            value=", ".join(f"`{prefix}{alias}`" for alias in command.aliases),
            inline=False,
        )
    return embed


def cog_embed(
    name: str, cmds: Sequence[commands.Command], prefix: str
) -> discord.Embed:
    embed = discord.Embed(
        title=f"{name} commands",
        description=command_lines(cmds, prefix) or "No commands.",
        colour=COLOUR,
    )
    embed.set_footer(text=f"Type {prefix}help <command> for details")
    return embed


def not_found_message(name: str, known: Sequence[str], prefix: str) -> str:
    match = difflib.get_close_matches(name.lower(), known, n=1)
    hint = (
        f"Did you mean `{prefix}{match[0]}`?"
        if match
        else f"Type `{prefix}help` to see them all."
    )
    # echoed user input: no pings or formatting, and not a wall of text
    shown = discord.utils.escape_mentions(discord.utils.escape_markdown(name[:50]))
    return f'No command called "{shown}". {hint}'


class DaMuseHelp(commands.HelpCommand):
    def __init__(self) -> None:
        super().__init__(
            command_attrs={
                "brief": "Show this list, or the details of one command.",
                "usage": "[command]",
                "help": HELP_DOC,
            }
        )

    async def send_bot_help(
        self,
        mapping: Mapping[Optional[commands.Cog], List[commands.Command[Any, ..., Any]]],
    ) -> None:
        cmds = await self.filter_commands(self.context.bot.commands)
        embed = overview_embed(cmds, self.context.clean_prefix)
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog) -> None:
        cmds = await self.filter_commands(cog.get_commands(), sort=True)
        embed = cog_embed(cog.qualified_name, cmds, self.context.clean_prefix)
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command: commands.Command) -> None:
        embed = command_embed(command, self.context.clean_prefix)
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group: commands.Group) -> None:
        await self.send_command_help(group)

    def command_not_found(self, string: str) -> str:
        known = [c.name for c in self.context.bot.commands if not c.hidden]
        return not_found_message(string, known, self.context.clean_prefix)


class General(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Install the custom !help while this cog is loaded (discord.py's
        # documented pattern), and put it back on unload.
        self._original_help = bot.help_command
        help_command = DaMuseHelp()
        help_command.cog = self
        bot.help_command = help_command

    async def cog_unload(self) -> None:
        self.bot.help_command = self._original_help

    @commands.command(brief="Check that I'm online.")
    async def hello(self, ctx: commands.Context) -> None:
        """Check that I'm online. I reply with your name and the server you're
        in."""
        guild_name = ctx.guild.name if ctx.guild else "no server"
        await ctx.send(f"Hello {ctx.author}! You are a member of {guild_name}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
