import asyncio
from datetime import datetime

import discord

from discord import errors as d_err
from discord.enums import Status
from discord.ext import commands

import pomodorobot.lib as lib

from pomodorobot.config import Config
from pomodorobot.timer import State, Action
from pomodorobot.channeltimerinterface import ChannelTimerInterface


class PomodoroBot(commands.Bot):
    """ An extension of the Bot class, that contains the necessary attributes
        and methods to run Pomodoro Timers on a series of channels.
    """

    def __init__(self, command_prefix, formatter=None, description=None,
                 pm_help=False, response_lifespan=15, **options):

        super().__init__(command_prefix, formatter,
                         description, pm_help, **options)

        # The timers currently running. There can be one per channel.
        # (Indexed by the channel's ID)
        self._interfaces = {}

        # The amount of timers running.
        self.timers_running = 0

        # The time after which most command responses get deleted
        self.ans_lifespan = 15

        # The file in which the attendance is saved
        self.attendance_file = "attendance.yml"
        # The ID of the administrator of the bot
        self.admin_id = ""
        # The ID of the role with permissions over the bot
        self.role_id = ""

        self.ans_lifespan = response_lifespan

        # So people can still see commands in help.
        self.formatter.show_check_failure = True

    def get_interface(self, channel: discord.Channel):
        """ Retrieves a channel interface. If none found for the channel, a new
            one is created with its default values.

        :param channel: The channel the interface belongs to.
        :type channel: discord.Channel

        :return: The interface belonging to the channel, new or old.
        """

        if channel not in self._interfaces:
            self._interfaces[channel] = ChannelTimerInterface(channel)
        return self._interfaces[channel]

    def reload_config(self, cfg: Config):
        """ Reloads the configurable values within the bot.

        :param cfg: The configuration object, holding all the loaded
            configurations
        :type cfg: pomodorobot.config.Config
        """

        bot_section = cfg.get_section('bot')

        self.command_prefix = bot_section['command_prefix']

        self.ans_lifespan = bot_section['response_lifespan']

        self.admin_id = bot_section['bot_admin_id']
        self.role_id = bot_section['bot_role_id']

        for channel, timer in self.valid_timers().items():
            timer.step = cfg.get_int('timer.time_step')

    @asyncio.coroutine
    async def safe_send(self, dest, content: str, **kwargs):
        """ Sends a message and then deletes it after a certain time has passed.

        :param dest: Where the message will be sent.
        :param content: The content of the message to send.
        """
        tts = kwargs.pop('tts', False)
        delete_after = kwargs.pop('delete_after', 0)

        message = await self.send_message(
            lib.as_object(dest) if isinstance(dest, str) else dest,
            content, tts=tts)

        if message and delete_after > 0:
            @asyncio.coroutine
            def delete():
                yield from asyncio.sleep(delete_after)
                yield from self.delete_message(message)
            asyncio.ensure_future(delete(), loop=self.loop)

    def is_admin(self, member: discord.Member) -> bool:
        """ Checks if a member is the administrator of the bot or not.

        :param member: The member to check for.
        :type member: discord.Member

        :return: True if the member's ID matches the recorded admin ID, False
            otherwise.
        """

        return member.id == self.admin_id

    def has_permission(self, member: discord.Member) -> bool:
        """ Checks if a member has elevated permissions on bot operations.
            This can be true if they are the administrator, or if they have
            the correct role.

        :param member: The member to check for.
        :type member: discord.Member

        :return: True if the member has permission, False otherwise.
        """

        return self.is_admin(member) or lib.has_role(member, self.role_id)

    def is_locked(self, channel: discord.Channel) -> bool:
        """ Checks if a certain channel is locked for normal users or not.

        :param channel: The channel to check.
        :type channel: discord.Channel

        :return: True if the channel is locked, false otherwise.
        """

        return self.get_interface(channel).locked

    def spoof(self, member: discord.Member, channel: discord.Channel):
        """ Spoofs a channel ID if there's a set channel to spoof from
            the one where the command was executed. Also checks for the
            author's permissions to see if they can spoof commands.

        :param member: The member trying to spoof the command.
        :type member: discord.Member

        :param channel: The channel from which the command to spoof was sent.
        :type channel: discord.Channel

        :return: If there's a registered ID to spoof and the author has elevated
            permissions, returns the spoofed ID. If not, returns the same ID
            as channel_id
        """

        if self.has_permission(member) and \
           self.get_interface(channel).spoofed is not None:
            return self._interfaces[channel].spoofed
        return channel

    async def update_status(self):
        """ Updates the status of the bot user to display the amount of
            timers running, if any, or show the bot as idle if none are.
        """

        if self.timers_running == 0:
            await self.change_presence(game=None, status=Status.idle)

        else:
            game = discord.Game()
            channels = lib.pluralize(self.timers_running, "channel", append="s")
            game.name = ("on " + channels)

            await self.change_presence(game=game, status=Status.online)

    async def _generate_messages(self, channel: discord.Channel):
        """ Generates and pins the messages for the given channel.

        :param channel: The channel in which the messages will be
            generated and pinned.
        :type channel: discord.Channel

        :raises: discord.errors.Forbidden: if the client doesn't have
            permissions to pin messages.
        """

        interface = self.get_interface(channel)
        if interface.timer is None:
            return

        interface.time_message = await self.send_message(
            channel, "Generating status...")

        interface.list_message = await self.send_message(
            channel, interface.timer.list_periods())

        # The last message pinned ends up in the top
        await self.pin_message(interface.time_message)
        await self.pin_message(interface.list_message)

    async def remove_messages(self, channel: discord.Channel):
        """ Deletes the time and periods list messages
            in the channel given.

        :param channel: The channel for which the messages will be
            deleted.
        :type channel: discord.Channel
        """

        interface = self.get_interface(channel)
        try:
            if interface.time_message is not None:
                await self.delete_message(interface.time_message)

            if interface.list_message is not None:
                await self.delete_message(interface.list_message)

        except d_err.NotFound:
            interface.time_message = None
            interface.list_message = None

    def valid_timers(self):
        """ Gives a list of all instantiated timers and the channels they
            belong to.

        :return: The list of (channel, timer) pairs.
        """

        return dict((c, i.timer) for c, i in self._interfaces.items() if
                    i.timer is not None)

    async def run_timer(self, channel: discord.Channel, start_idx=0):
        """ Makes a timer run.

        :param channel: The channel where the timer that is being ran is.
        :type channel: discord.Channel

        :param start_idx: The index of the period from which the timer should
            start from. Defaults to 0, or is 0 if it's outside the valid range.
        :type start_idx: int; 0 < start_idx <= len(timer.periods)
        """

        interface = self.get_interface(channel)
        timer = interface.timer
        if timer is None:
            lib.log("Tried to start a timer, but none found.",
                    channel_id=channel.id)
            return

        await self.wait_until_ready()

        self.timers_running += 1
        await self.update_status()

        while not self.is_closed:
            iter_start = datetime.now()
            start_micro = iter_start.second * 1000000 + iter_start.microsecond

            if timer.get_state() == State.RUNNING and \
               timer.curr_time >= timer.periods[timer.get_period()].time * 60:

                say = "'{}' period over!"\
                    .format(timer.periods[timer.get_period()].name)

                timer.curr_time = 0

                if timer.get_period() + 1 >= len(timer.periods) and \
                   not timer.repeat:

                    say += "\nI have ran out of periods, and looping is off."
                    lib.log(say, channel_id=channel.id)
                    await self.safe_send(channel, say, tts=interface.tts)

                    break

                timer.set_period((timer.get_period() + 1) % len(timer.periods))

                if timer.action == Action.NONE:
                    say += " '{}' period now starting ({})."\
                        .format(timer.periods[timer.get_period()].name,
                                lib.pluralize(
                                    timer.periods[timer.get_period()].time,
                                    "minute", append="s"))

                lib.log(say, channel_id=channel.id)
                await self.safe_send(channel, say, tts=interface.tts)

                await self.edit_message(interface.list_message,
                                        timer.list_periods())

            if timer.action == Action.STOP:
                timer.action = Action.NONE

                lib.log("Timer has stopped.", channel_id=channel.id)
                await self.safe_send(channel, "Timer has stopped.")

                break

            elif timer.action == Action.PAUSE:
                timer.action = Action.NONE
                timer.set_state(State.PAUSED)

                lib.log("Timer has paused.", channel_id=channel.id)
                await self.safe_send(channel, "Timer has paused.")

            elif timer.action == Action.RUN:
                timer.action = Action.NONE

                prev_state = timer.get_state()
                timer.set_state(State.RUNNING)

                if prev_state == State.STOPPED:
                    timer.set_period(start_idx)
                    say_action = "Starting"
                else:
                    say_action = "Resuming"

                if start_idx != 0:
                    say_action += " (from period n." + str(start_idx + 1) + ")"

                lib.log(say_action, channel_id=channel.id)
                await self.safe_send(channel, say_action)

                if interface.time_message is None:
                    try:
                        await self._generate_messages(channel)
                    except discord.Forbidden:
                        lib.log("No permission to pin.", channel_id=channel.id)
                        kitty = ("I tried to pin a message and failed." +
                                 " Can I haz permission to pin messages?" +
                                 " https://goo.gl/tYYD7s")
                        await self.safe_send(channel, kitty)

            try:
                if interface.time_message is not None:
                    await self.edit_message(interface.time_message,
                                            timer.time())
            except d_err.NotFound:
                pass

            if timer.get_state() == State.RUNNING:
                iter_end = datetime.now()
                end_micro = iter_end.second * 1000000 + iter_end.microsecond

                end_micro -= start_micro
                end_micro %= 1000000.0
                sleep_time = ((timer.step * 1000000.0) - end_micro)

                await asyncio.sleep(sleep_time / 1000000.0)
                timer.curr_time += timer.step
            else:
                break

        if timer.get_state() != State.PAUSED:
            timer.curr_time = 0
            timer.set_period(-1)
            timer.set_state(State.STOPPED)

            await self.remove_messages(channel)

            interface.time_message = None
            interface.list_message = None

        self.timers_running -= 1
        await self.update_status()
