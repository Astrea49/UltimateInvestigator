import asyncio
import collections
import importlib
import typing

import naff

import common.models as models
import common.utils as utils


class BulletCheck(utils.Extension):
    """The cog that checks for the Truth Bullets."""

    bot: utils.UIBase

    def __init__(self, bot: utils.UIBase):
        self.bot = bot

    async def check_for_finish(
        self,
        guild: naff.Guild,
        bullet_chan: naff.GuildText,
        guild_config: models.Config,
    ):
        do_not_find = await models.TruthBullet.filter(guild_id=guild.id, found=False)
        if do_not_find:
            return

        counter = collections.Counter()

        async for bullet in models.TruthBullet.filter(guild_id=guild.id):
            counter[bullet.finder] += 1

        most_found = counter.most_common(None)
        most_found_num = most_found[0][
            1
        ]  # number of truth bullets found by highest person
        # the next is just fancy code to check for ties and make a list for the top people
        most_found_people = tuple(p[0] for p in most_found if p[1] == most_found_num)

        if guild_config.ult_detective_role > 0:  # if the role had been specified
            if ult_detect_role_obj := guild.get_role(guild_config.ult_detective_role):
                for person_id in most_found_people:
                    try:  # use an internal method to save on an http request
                        # we get to skip out on asking for the member, which was... well
                        # who cares, anyways?
                        # but dont do this unless you're me

                        await self.bot.http.add_guild_member_role(
                            guild.id, person_id, ult_detect_role_obj.id
                        )
                        await asyncio.sleep(1)  # we don't want to trigger ratelimits
                    except naff.errors.HTTPException:
                        continue

        str_builder = collections.deque()
        str_builder.append("**All Truth Bullets have been found.**")
        str_builder.append("")
        str_builder.append(f"Best Detective(s) (found {most_found_num} Truth Bullets):")
        str_builder.extend(f"<@{person_id}>" for person_id in most_found_people)

        await bullet_chan.send("\n".join(str_builder))

        guild_config.bullets_enabled = False
        await guild_config.save()

    @naff.listen("message_create")
    async def on_message(self, event: naff.events.MessageCreate):
        message = event.message

        # if the message is from a bot, from discord, not from a guild, not a default message or a reply, or is empty
        if (
            message.author.bot
            or message.author.system
            or not message.guild
            or message.type != naff.enums.MessageTypes.DEFAULT
            or message.content == ""
        ):
            return

        guild_config = self.bot.cached_configs.get(
            message.id
        ) or await utils.create_or_get(message.guild.id)
        self.bot.cached_configs[message.id] = guild_config

        if not (
            guild_config.bullets_enabled
            and guild_config.player_role
            # internal list that has list of ids, faster than using roles property
            and message.author.has_role(guild_config.player_role)
        ):
            return

        bullet_found: typing.Optional[models.TruthBullet] = None

        channel_id = (
            message.channel.parent_channel.id
            if isinstance(message.channel, naff.ThreadChannel)
            else message.channel.id
        )

        async for bullet in models.TruthBullet.filter(channel_id=channel_id):
            if (
                bullet.name.lower() in message.content.lower()
                or any(a.lower() in message.content.lower() for a in bullet.aliases)
            ) and not bullet.found:
                bullet_found = bullet
                break

        if not bullet_found or bullet_found.found:
            return

        embed = bullet_found.found_embed(str(message.author))

        bullet_chan: naff.GuildText = self.bot.get_channel(guild_config.bullet_chan_id)
        if not bullet_chan:
            raise utils.CustomCheckFailure(
                "For some reason, I tried getting a channel I can't see. The owner of"
                " the bot should be able to fix this soon."
            )

        bullet_found.found = True
        bullet_found.finder = message.author.id
        await bullet_found.save()

        await message.reply(embed=embed)
        await bullet_chan.send(embed=embed)

        await self.check_for_finish(message.guild, bullet_chan, guild_config)


def setup(bot):
    importlib.reload(utils)
    BulletCheck(bot)
