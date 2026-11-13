from types import SimpleNamespace

import discord
import pytest
import pytest_asyncio
from discord.ext import commands

from cogs.general import (
    SECTIONS,
    DaMuseHelp,
    General,
    command_embed,
    not_found_message,
    overview_embed,
    unwrap,
    usage_line,
)
from cogs.music import Music


@pytest_asyncio.fixture
async def bot():
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.none())
    bot.services = SimpleNamespace()  # type: ignore[attr-defined]  # Music stores it
    await bot.add_cog(General(bot))
    await bot.add_cog(Music(bot))  # type: ignore[arg-type]
    return bot


def field_commands(embed):
    """Section title -> command names, read back from the embed lines."""
    return {
        field.name: [
            line.split("`")[1].split()[0][1:] for line in field.value.split("\n")
        ]
        for field in embed.fields
    }


@pytest.mark.asyncio
async def test_custom_help_is_installed_and_restored(bot):
    assert isinstance(bot.help_command, DaMuseHelp)
    assert bot.get_command("help").cog_name == "General"
    await bot.remove_cog("General")
    assert not isinstance(bot.help_command, DaMuseHelp)


@pytest.mark.asyncio
async def test_overview_groups_commands_in_order(bot):
    embed = overview_embed(bot.commands, "!")
    sections = field_commands(embed)

    assert list(sections) == [title for title, _ in SECTIONS]
    assert sections == {title: list(names) for title, names in SECTIONS}
    listed = [name for names in sections.values() for name in names]
    assert sorted(listed) == sorted(c.name for c in bot.commands)


@pytest.mark.asyncio
async def test_unlisted_command_goes_under_other(bot):
    @commands.command(brief="Brand new.")
    async def shuffle(ctx):
        pass

    bot.add_command(shuffle)
    sections = field_commands(overview_embed(bot.commands, "!"))
    assert sections["Other"][-1] == "shuffle"


@pytest.mark.asyncio
async def test_usage_lines_use_friendly_argument_names(bot):
    assert usage_line(bot.get_command("play"), "!") == "!play [song]"
    assert usage_line(bot.get_command("switch"), "!") == "!switch [artist]"
    assert usage_line(bot.get_command("skip"), "!") == "!skip"
    assert usage_line(bot.get_command("help"), "!") == "!help [command]"


@pytest.mark.asyncio
async def test_every_command_has_help_within_discord_limits(bot):
    overview = overview_embed(bot.commands, "!")
    assert len(overview) <= 6000
    assert all(len(field.value or "") <= 1024 for field in overview.fields)
    for command in bot.commands:
        assert command.brief, command.name
        assert command.help, command.name
        embed = command_embed(command, "!")
        assert embed.description is not None
        assert len(embed.description) <= 4096
        assert "\n" not in embed.description.split("\n\n")[0]  # unwrapped


@pytest.mark.asyncio
async def test_command_embed_shows_details(bot):
    embed = command_embed(bot.get_command("play"), "!")
    assert embed.title == "!play [song]"
    assert embed.description is not None
    assert "Spotify track link" in embed.description
    assert "- `!play bulls on parade`" in embed.description


def test_unwrap_joins_lines_but_keeps_paragraphs_and_bullets():
    text = "One line\nwrapped here.\n\nExamples:\n- `!a`\n- `!b` that\n  wraps"
    assert (
        unwrap(text) == "One line wrapped here.\n\nExamples:\n- `!a`\n- `!b` that wraps"
    )


def test_not_found_suggests_close_match():
    known = ["play", "skip", "stop"]
    assert not_found_message("plya", known, "!") == (
        'No command called "plya". Did you mean `!play`?'
    )
    assert "Type `!help`" in not_found_message("xyzzy", known, "!")
    assert "@​everyone" in not_found_message("@everyone", known, "!")
