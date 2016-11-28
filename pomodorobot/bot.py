import asyncio
from datetime import datetime

import discord
from discord import errors as d_err
from discord.enums import Status
from discord.ext import commands

import pomodorobot.lib as lib
from pomodorobot.timer import State, Action


class PomodoroBot(commands.Bot):
    """ An extension of the Bot class, that contains the necessary attributes
        and methods to run Pomodoro Timers on a series of channels.
    """

    # The timers currently running. There can be one per channel.
    # (Indexed by the channel's ID)
    timers = {}

    # The messages that gets pinned, containing the current timer and its status
    # (1 of each per channel, indexed by the channel's ID)
    time_messages = {}
    list_messages = {}

    # A list of channels locked, meaning only people with permissions can
    # change them somehow
    locked = []
    # A list of spoofed channels, meaning any commands ran on channel 'key'
    # will actually affect timers on channel 'value'
    spoofed = {}

    # The amount of timers running.
    timers_running = 0

    # The time between each timer update
    timer_step = 2
    # The time after which most command responses get deleted
    response_lifespan = 15

    # The ID of the administrator of the bot
    admin_id = ""
    # The ID of the role with permissions over the bot
    role_id = ""

    def __init__(self, command_prefix, formatter=None, description=None,
                 pm_help=False, response_lifespan=15, timer_step=2, **options):
        super().__init__(command_prefix, formatter,
                         description, pm_help, **options)

        self.timer_step = timer_step
        self.response_lifespan = response_lifespan

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

    def is_locked(self, channel_id: str) -> bool:
        """ Checks if a certain channel is locked for normal users or not.

        :param channel_id: The ID of the channel to check.
        :type channel_id: str

        :return: True if the channel is locked, false otherwise.
        """

        return channel_id in self.locked

    @asyncio.coroutine
    async def send_msg(self, channel_id: str, message: str, tts=False):
        """ Wrap-around for the send_message method that allows string-based
            destinations (i.e. the ID of a channel instead of the channel
            itself).

            (see discord.Client's send_message method)

        :param channel_id: The ID of the channel (or user) to send the
            message to.
        :type channel_id: str

        :param message: The message being sent.
        :type message: str

        :param tts: Whether the message should be a TTS one or not.
            Defaults to False
        :type tts: bool
        """
        await self.send_message(lib.as_object(channel_id), message, tts=tts)

    @asyncio.coroutine
    async def update_status(self):
        """ Updates the status of the bot user to display the amount of
            timers running, if any, or show the bot as idle if none are.
        """

        if self.timers_running == 0:
            await self.change_presence(game=None, status=Status.idle)

        else:
            game = discord.Game()
            channels = lib.pluralize(self.timers_running, "channel", append="s")
            game.name = (" on " + channels)

            await self.change_presence(game=game, status=Status.online)

    @asyncio.coroutine
    async def _generate_messages(self, channel_id: str):
        """ Generates and pins the messages for the given channel.

        :param channel_id: The channel in which the messages will be
            generated and pinned.
        :type channel_id: str

        :raises: discord.errors.Forbidden: if the client doesn't have
            permissions to pin messages.
        """

        self.time_messages[channel_id] = await self.send_message(
            lib.as_object(channel_id),
            "Generating status...")

        self.list_messages[channel_id] = await self.send_message(
            lib.as_object(channel_id),
            self.timers[channel_id].list_periods())

        # The last message pinned ends up in the top
        await self.pin_message(self.list_messages[channel_id])
        await self.pin_message(self.time_messages[channel_id])

    @asyncio.coroutine
    async def remove_messages(self, channel_id: str):
        """ Deletes the time and periods list messages
            in the channel with the ID given.

        :param channel_id: The channel's ID in which the messages will be
            deleted.
        :type channel_id: str
        """

        try:
            if channel_id in self.time_messages.keys() and\
               self.time_messages[channel_id] is not None:
                await self.delete_message(self.time_messages[channel_id])

            if channel_id in self.list_messages.keys() and\
               self.list_messages[channel_id] is not None:
                await self.delete_message(self.list_messages[channel_id])

        except d_err.NotFound:
            pass

    @asyncio.coroutine
    async def run_timer(self, channel_id, start_idx=0):
        """ Makes a timer run.

        :param channel_id: The ID of the channel's timer that is being ran.
        :type channel_id: str

        :param start_idx: The index of the period from which the timer should
            start from. Defaults to 0, or is 0 if it's outside the valid range.
        :type start_idx: int; 0 < start_idx < len(timer.times)
        """

        timer = self.timers[channel_id]

        await self.wait_until_ready()

        self.timers_running += 1
        await self.update_status()

        while not self.is_closed:
            iter_start = datetime.now()
            start_micro = iter_start.second * 1000000 + iter_start.microsecond

            if timer.state == State.RUNNING and \
               timer.curr_time >= timer.times[timer.curr_period] * 60:

                say = "@here | '" + timer.names[timer.curr_period]
                say += "' period over!"

                timer.curr_time = 0
                timer.curr_period += 1

                if timer.curr_period >= len(timer.times) and \
                   not timer.repeat:
                    timer.action = Action.STOP
                    say += "\nI have ran out of periods, and looping is off."
                    lib.log(say, channel_id=channel_id)
                    await self.send_msg(channel_id, say, tts=timer.tts)

                    self.timers_running -= 1
                    await self.update_status()
                    return

                timer.curr_period %= len(timer.times)

                if timer.action == Action.NONE:
                    say += (" '" + timer.names[timer.curr_period] +
                            "' period now starting (" +
                            lib.pluralize(timer.times[timer.curr_period],
                                          "minute", append="s") + ").")

                lib.log(say, channel_id=channel_id)
                await self.send_msg(channel_id, say, tts=timer.tts)

                await self.edit_message(self.list_messages[channel_id],
                                        timer.list_periods())

            if timer.action == Action.STOP:
                timer.action = Action.NONE

                timer.curr_period = -1
                timer.curr_time = 0

                timer.state = State.STOPPED

                lib.log("Timer has stopped.", channel_id=channel_id)
                await self.send_msg(channel_id, "Timer has stopped.")

                await self.remove_messages(channel_id)

                self.time_messages[channel_id] = None
                self.list_messages[channel_id] = None

            elif timer.action == Action.PAUSE:
                timer.action = Action.NONE
                timer.state = State.PAUSED

                lib.log("Timer has paused.", channel_id=channel_id)
                await self.send_msg(channel_id, "Timer has paused.")

            elif timer.action == Action.RUN:
                timer.action = Action.NONE

                if timer.state == State.STOPPED:
                    timer.curr_period = start_idx
                    say_action = "Starting"
                else:
                    say_action = "Resuming"

                if start_idx != 0:
                    say_action += " (from period n." + str(start_idx + 1) + ")"

                lib.log(say_action, channel_id=channel_id)
                await self.send_msg(channel_id, say_action)

                if self.time_messages[channel_id] is None:
                    try:
                        await self._generate_messages(channel_id)
                    except discord.Forbidden:
                        lib.log("No permission to pin.", channel_id=channel_id)
                        kitty = ("I tried to pin a message and failed." +
                                 " Can I haz permission to pin messages?" +
                                 " https://goo.gl/tYYD7s")
                        await self.send_msg(channel_id, kitty)

                timer.state = State.RUNNING

            try:
                if self.time_messages[channel_id] is not None:
                    await self.edit_message(self.time_messages[channel_id],
                                            timer.time())
            except d_err.NotFound:
                pass

            if timer.state == State.RUNNING:
                iter_end = datetime.now()
                end_micro = iter_end.second * 1000000 + iter_end.microsecond

                end_micro -= start_micro
                end_micro %= 1000000.0
                sleep_time = ((self.timer_step * 1000000.0) - end_micro)

                await asyncio.sleep(sleep_time / 1000000.0)
                timer.curr_time += self.timer_step
            else:
                self.timers_running -= 1
                await self.update_status()
                return