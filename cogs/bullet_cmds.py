import collections
import importlib
import typing

import dis_snek
import molter

import common.models as models
import common.utils as utils


class BulletCMDs(utils.Scale):
    """Commands for using and modifying Truth Bullets."""

    def __init__(self, bot):
        self.display_name = "Bullet"
        self.bot = bot

    @molter.msg_command()
    @utils.bullet_proper_perms()
    async def add_bullet(
        self,
        ctx: dis_snek.MessageContext,
        channel: typing.Annotated[dis_snek.GuildText, utils.ValidChannelConverter],
        name: str,
        *,
        description: str,
    ):
        """Adds a Truth Bullet to the list of Truth Bullets.
        Requires a channel (mentions or IDS work), name, and description of the Bullet itself.
        If you wish for the name/trigger to be more than one word, put quotes around it.
        The name must be under or at 100 characters, and the description must be at or under 1900 characters.
        Requires being able to Manage Truth Bullets."""

        if len(name) > 100:
            raise molter.BadArgument(
                "The name is too large for me to use! "
                + "Please use something at or under 100 characters."
            )
        if len(description) > 1900:
            raise molter.BadArgument(
                "The description is too large for me to use! "
                + "Please use something at or under 1900 characters, or consider using"
                " a Google "
                + "Doc to store the text."
            )

        await ctx.channel.trigger_typing()

        possible_duplicate = await models.TruthBullet.exists(
            channel_id=channel.id, name=name
        )
        if possible_duplicate:
            raise molter.BadArgument(f"Truth Bullet `{name}` already exists!")

        await models.TruthBullet.create(
            name=name,
            aliases=set(),
            description=description,
            channel_id=channel.id,
            guild_id=ctx.guild.id,
            found=False,
            finder=0,
        )

        await ctx.message.reply("Added Truth Bullet!")

    @molter.msg_command()
    @utils.bullet_proper_perms()
    async def remove_bullet(
        self,
        ctx: dis_snek.MessageContext,
        channel: dis_snek.GuildText,
        name: str,
    ):
        """Removes a Truth Bullet from the list of Truth Bullets.
        Requires a channel (mentions or IDS work) and the name of the Bullet.
        If the name/trigger is more than one word, put quotes around it.
        Requires being able to Manage Truth Bullets."""

        await ctx.channel.trigger_typing()

        num_deleted = await models.TruthBullet.filter(
            channel_id=channel.id, name=name
        ).delete()

        if num_deleted > 0:
            await ctx.message.reply(f"`{name}` deleted!")
        else:
            raise molter.BadArgument(f"Truth Bullet `{name}` does not exists!")

    @molter.msg_command()
    @utils.bullet_proper_perms()
    async def clear_bullets(self, ctx: dis_snek.MessageContext):
        """Removes all Truth Bullets from the list of Truth Bullets.
        This action is irreversible.
        Requires being able to Manage Truth Bullets."""

        await ctx.channel.trigger_typing()

        num_deleted = await models.TruthBullet.filter(guild_id=ctx.guild.id).delete()

        # just to give a more clear indication to users
        # technically everything's fine without this
        if num_deleted > 0:
            await ctx.message.reply("Cleared all Truth Bullets for this server!")
        else:
            raise utils.CustomCheckFailure(
                "There's no Truth Bullets to delete for this server!"
            )

    @molter.msg_command()
    @utils.bullet_proper_perms()
    async def list_bullets(self, ctx: dis_snek.MessageContext):
        """Lists all Truth Bullets in the server.
        Will also show if the Truth Bullet has been found or not.
        Requires being able to Manage Truth Bullets."""

        await ctx.channel.trigger_typing()

        guild_bullets = await models.TruthBullet.filter(guild_id=ctx.guild.id)
        if not guild_bullets:
            raise utils.CustomCheckFailure("There's no Truth Bullets for this server!")

        bullet_dict = collections.defaultdict(list)
        for bullet in guild_bullets:
            bullet_dict[bullet.channel_id].append(bullet)

        str_builder = collections.deque()

        for channel_id in bullet_dict.keys():
            str_builder.append(f"<#{channel_id}>:")
            for bullet in bullet_dict[channel_id]:
                str_builder.append(
                    f"\t- `{bullet.name}`{'' if not bullet.found else ' (found)'}"
                )

            str_builder.append("")

        chunks = utils.line_split("\n".join(str_builder), split_by=30)
        for chunk in chunks:
            await ctx.message.reply("\n".join(chunk))

    @molter.msg_command(aliases=["bullet_information"])
    @utils.bullet_proper_perms()
    async def bullet_info(
        self,
        ctx: dis_snek.MessageContext,
        channel: dis_snek.GuildText,
        name: str,
    ):
        """Lists all information about a bullet.
        Requires a channel (mentions or IDS work) and the name of the Bullet.
        If the name/trigger is more than one word, put quotes around it.
        Requires being able to Manage Truth Bullets."""

        await ctx.channel.trigger_typing()

        possible_bullet = await models.TruthBullet.get_or_none(
            channel_id=channel.id, name=name
        )

        if possible_bullet is None:
            raise molter.BadArgument(f"Truth Bullet `{name}` does not exist!")

        await ctx.message.reply(
            str(possible_bullet), allowed_mentions=utils.deny_mentions(ctx.author)
        )

    @molter.msg_command()
    @utils.bullet_proper_perms()
    async def edit_bullet(
        self,
        ctx: dis_snek.MessageContext,
        channel: dis_snek.GuildText,
        name: str,
        *,
        description: str,
    ):
        """Edits a Truth Bullet.
        Requires a channel (mentions or IDS work), the name, and a new description of the Bullet itself.
        If the name/trigger has more than one word, put quotes around it.
        The new description must be at or under 1900 characters.
        Requires being able to Manage Truth Bullets."""

        if len(description) > 1900:
            raise molter.BadArgument(
                "The description is too large for me to use! "
                + "Please use something at or under 1900 characters, or consider using"
                " a Google "
                + "Doc to store the text."
            )

        await ctx.channel.trigger_typing()

        possible_bullet = await models.TruthBullet.get_or_none(
            channel_id=channel.id, name=name
        )
        if possible_bullet is None:
            raise molter.BadArgument(f"Truth Bullet `{name}` does not exist!")

        possible_bullet.description = description
        await possible_bullet.save()

        await ctx.message.reply("Edited Truth Bullet!")

    @molter.msg_command()
    @utils.bullet_proper_perms()
    async def unfind_bullet(
        self, ctx: dis_snek.MessageContext, channel: dis_snek.GuildText, name: str
    ):
        """Un-finds a Bullet.
        If someone had found a Bullet you did not want them to find, this will be useful.
        Requires a channel (mentions or IDS work) and the name of the Bullet.
        If the name/trigger is more than one word, put quotes around it.
        Requires being able to Manage Truth Bullets."""

        await ctx.channel.trigger_typing()

        possible_bullet = await models.TruthBullet.get_or_none(
            channel_id=channel.id, name=name
        )

        if possible_bullet is None:
            raise molter.BadArgument(f"Truth Bullet `{name}` does not exist!")
        if not possible_bullet.found:
            raise molter.BadArgument(f"Truth Bullet `{name}` has not been found!")

        possible_bullet.found = False
        possible_bullet.finder = 0
        await possible_bullet.save()

        await ctx.message.reply("Truth Bullet un-found!")

    @molter.msg_command()
    @utils.bullet_proper_perms()
    async def override_bullet(
        self,
        ctx: dis_snek.MessageContext,
        channel: dis_snek.GuildText,
        name: str,
        user: dis_snek.Member,
    ):
        """Overrides who found a Truth Bullet with the person specified.
        Useful if the bot glitched out for some reason.
        Requires a channel (mentions or IDS work), the name of the Bullet, and the user (mentions or IDS work).
        If the name/trigger is more than one word, put quotes around it.
        Requires being able to Manage Truth Bullets."""

        await ctx.channel.trigger_typing()

        possible_bullet = await models.TruthBullet.get_or_none(
            channel_id=channel.id, name=name
        )
        if possible_bullet is None:
            raise molter.BadArgument(f"Truth Bullet `{name}` does not exist!")

        possible_bullet.found = True
        possible_bullet.finder = user.id
        await possible_bullet.save()

        await ctx.message.reply("Truth Bullet overrided and found!")

    @molter.msg_command()
    @utils.bullet_proper_perms()
    async def add_alias(
        self,
        ctx: dis_snek.MessageContext,
        channel: dis_snek.GuildText,
        name: str,
        alias: str,
    ):
        """Adds an alias to the Truth Bullet specified.
        If users trigger an alias, it'll be treated as if they found the actual Truth Bullet.
        Thus, this is useful for when something has multiple words that could be used.
        Requires a channel (mentions or IDS work), the original name of the Bullet, and the alias.
        If the name or alias is more than one word, put quotes around it.
        Aliases need to be less than or at 40 characters, and there can only be 5 aliases.
        Requires being able to Manage Truth Bullets."""

        if len(alias) > 40:
            raise molter.BadArgument(
                "The name is too large for me to use! "
                + "Please use something at or under 40 characters."
            )

        await ctx.channel.trigger_typing()

        possible_bullet = await models.TruthBullet.get_or_none(
            channel_id=channel.id, name=name
        )
        if possible_bullet is None:
            raise molter.BadArgument(f"Truth Bullet `{name}` does not exist!")

        if len(possible_bullet.aliases) >= 5:
            raise utils.CustomCheckFailure(
                "I cannot add more aliases to this Truth Bullet!"
            )

        if alias in possible_bullet.aliases:
            raise molter.BadArgument(
                f"Alias `{alias}` already exists for this Truth Bullet!"
            )

        possible_bullet.aliases.add(alias)
        await possible_bullet.save()

        await ctx.message.reply(f"Alias `{alias}` added to Truth Bullet!")

    @molter.msg_command()
    @utils.bullet_proper_perms()
    async def remove_alias(
        self,
        ctx: dis_snek.MessageContext,
        channel: dis_snek.GuildText,
        name: str,
        alias: str,
    ):
        """Remove an alias to the Truth Bullet specified.
        Requires a channel (mentions or IDS work), the original name of the Bullet, and the alias.
        If the name or alias is more than one word, put quotes around it.
        Requires being able to Manage Truth Bullets."""

        await ctx.channel.trigger_typing()

        possible_bullet = await models.TruthBullet.get_or_none(
            channel_id=channel.id, name=name
        )
        if possible_bullet is None:
            raise molter.BadArgument(f"Truth Bullet `{name}` does not exist!")

        try:
            possible_bullet.aliases.remove(alias)
        except KeyError:
            raise molter.BadArgument(
                f"Alias `{alias}` does not exists for this Truth Bullet!"
            )

        await possible_bullet.save()

        await ctx.message.reply(f"Alias `{alias}` removed from Truth Bullet!")


def setup(bot):
    importlib.reload(utils)
    BulletCMDs(bot)
