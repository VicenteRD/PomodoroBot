import yaml
from datetime import datetime
import logging
import discord.errors

from discord.ext import commands

import pomodorobot.ext.checks as checks
import pomodorobot.config as config
import pomodorobot.lib as lib

from pomodorobot.bot import PomodoroBot
from pomodorobot.timer import PomodoroTimer, State

SAFE_DEFAULT_FMT = "(2xStudy/Work:32,Break:8),Study/Work:32,Long_Break:15"


class TimerCommands:
    """ Represents all the possible commands that influence a timer.
    """

    def __init__(self, bot: PomodoroBot):
        self.bot = bot

    @commands.group(name="timer")
    @commands.check(checks.whitelisted)
    async def timer(self, ctx: commands.Context):
        """ Controls the channel's timer. Do '!help timer' for sub-commands.
            None of the sub-commands will really work without using `setup`
            first.
        """

        if ctx.invoked_subcommand is not None:
            return

        sect = ctx.message.content.split(' ')
        if len(sect) < 2 or sect[1] is None:
            log = "{} invoked an incomplete timer command."

            send = "Timers are allowed here. Now what?"
        else:
            log = "{} invoked an invalid timer command."
            send = "Invalid timer sub-command."

        lib.log(log.format(ctx.author.display_name),
                channel_id=ctx.channel.id)
        await ctx.send(send, delete_after=self.bot.ans_lifespan)

    @timer.command(name="setup")
    @commands.check(checks.whitelisted)
    @commands.check(checks.unlocked_or_allowed)
    async def setup(self, ctx: commands.Context, timer_format="default",
                    repeat=None, count_back=None):
        """ Sets up a timer for the channel in which this command was executed.
            Only allows timers in white-listed channels (Specified in the
            configuration).

            :param timer_format: The string containing the periods and
                their names, in a format similar to that of a dictionary.
                Ex.: PeriodA:10,PeriodB:5,PeriodC:15
                     This will create 3 periods of 10, 5 and 15 minutes.

                It also accepts segments with the format (nxName1:t1,Name2:t2),
                which creates n iterations of Name1:t1,Name2:t2 periods (Where
                Name1 and Name2 are the period names and t1, t2 the respective
                times).
                Ex.: (3xPeriodA:10,PeriodB:5),PeriodC:15
                    This will create 7 periods of times 10,5,10,5,10,5 and 15.
            :type timer_format: str

            :param repeat: (boolean) Whether the timer should go back to
                period 1 after going through the complete list (True)
                or not (False). Defaults to True.

            :param count_back: (boolean) Whether the timer should show
                remaining (True) or elapsed (False) time. Defaults to True.
        """

        await self._setup(ctx, timer_format, repeat, count_back)

    @timer.command(name="pomodoro")
    @commands.check(checks.whitelisted)
    @commands.check(checks.unlocked_or_allowed)
    async def pomodoro(self, ctx: commands.Context,
                       x: float, y: float, z: float):
        """ Sets the timer up with a typical Pomodoro Timer configuration
            consisting of x minutes of productivity, y minutes of break,
            and a long break of z minutes

        :param x: The length of productivity periods, in minutes.
        :type x: numerical (int or float)

        :param y: The length of break periods, in minutes.
        :type y: numerical (int or float)

        :param z: The length of long break periods, in minutes.
        :type z: numerical (int or float)

        .. see:: setup
        """

        if x is None or x <= 0 or y is None or y <= 0 or z is None or z <= 0:
            ctx.send("One of the values provided is invalid",
                     delete_after=self.bot.ans_lifespan)
            lib.log("Invalid pomodoro command was given.",
                    channel_id=ctx.channel.id)

        await self._setup(ctx, _pomodoro_config(x, y, z), True, True)

    @timer.command(name="add")
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def add_timer_period(self, ctx: commands.Context, period_info: str,
                               index='n'):
        """ Adds a period with the given information after the given index.

        :param period_info: The information of the period(s) you want to add,
            that must follow the same rules that the setup command requires.
            For example: `Study:30` will add a 30-minute period with the name
            Study.
        :type period_info: str

        :param index: The index at which the period should be added,
            counting from `0` to `n`, where `n` is the current number of periods
            available. If the index given is negative, it will count backwards.
            Thus, if 0 is given, it will be added as the first period,
            and with `n` it will be added as the last one (using `-n` is
            the same as using 0).
            If a literal `n` is given, it will translate to whatever the amount
            of periods is currently.
        :type index: int || 'n'
        """

        interface = self.bot.get_interface(
            self.bot.spoof(ctx.author, ctx.channel))
        timer = interface.timer

        amount = timer.add_periods(index, period_info)
        if amount == 0:
            await ctx.send(
                "Could not add the period(s)."
                " Failed to parse the given information",
                delete_after=self.bot.ans_lifespan)
            return

        period_str = 'period' if amount == 1 else 'periods'

        if interface.timer.get_state() != State.STOPPED:
            await interface.list_message.edit(content=timer.list_periods())

        await ctx.send("Successfully added the new {}!".format(period_str),
                       delete_after=self.bot.ans_lifespan)

    @timer.command(name="remove")
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def remove_timer_period(self, ctx: commands.Context, index: int,
                                  amount=1):
        """ Removes the period(s) from the given index

        :param index: The index to remove from, counting from `1` to `n`.
        :param amount: The amount of periods to remove.
        """

        interface = self.bot.get_interface(
            self.bot.spoof(ctx.author, ctx.channel))
        timer = interface.timer

        if index > len(timer.periods) or index <= 0:
            await ctx.send(
                "Unable to remove the specified period(s)",
                delete_after=self.bot.ans_lifespan)
            return

        if timer.remove_periods(index - 1, amount):
            period_str = 'period' if amount == 1 else 'periods'

            if timer.get_state() != State.STOPPED:
                await interface.list_message.edit(content=timer.list_periods())

            await ctx.send("Successfully removed the {}!"
                           .format(period_str),
                           delete_after=self.bot.ans_lifespan)
        else:
            await ctx.send(("If you want to remove all periods,"
                            " use the reset command!"),
                           delete_after=self.bot.ans_lifespan)

    @timer.command(name="repeat")
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def toggle_repeat(self, ctx: commands.Context, toggle=None):
        """ Turns the timer's looping setting on or off. If no state is
            specified, it will toggle it

        :param toggle: True, yes or on to turn the setting on. False, no or off
            to turn the setting off. If not specified, or None is given,
             it will toggle the setting.
        :type toggle: bool || None
        """
        interface = self.bot.get_interface(
            self.bot.spoof(ctx.author, ctx.channel))
        timer = interface.timer

        toggle = lib.to_boolean(toggle)
        if timer.repeat == toggle:
            return  # No need to edit it if it's the same.
        timer.toggle_looping(toggle)

        await interface.list_message.edit(content=timer.list_periods())
        await ctx.send("Successfully toggled the looping setting {}!"
                       .format("on" if timer.repeat else "off"),
                       delete_after=self.bot.ans_lifespan)

    @timer.command(name="countdown")
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def toggle_countdown(self, ctx: commands.Context, toggle=None):
        """ Turns the timer's countdown setting on or off. If no state is
            specified, it will toggle it

        :param toggle: True, yes or on to turn the setting on. False, no or off
            to turn the setting off. If not specified, or None is given,
             it will toggle the setting.
        :type toggle: bool || None
        """

        interface = self.bot.get_interface(
            self.bot.spoof(ctx.author, ctx.channel))
        timer = interface.timer

        toggle = lib.to_boolean(toggle)
        if timer.countdown == toggle:
            return  # No need to edit it if it's the same.
        timer.toggle_countdown(toggle)

        await interface.time_message.edit(content=timer.time())
        await ctx.send("Successfully toggled the countdown setting {}!"
                       .format("on" if timer.countdown else "off"),
                       delete_after=self.bot.ans_lifespan)

    @timer.command(name="sub")
    @commands.check(checks.whitelisted)
    async def timer_sub(self, ctx: commands.Context):
        """ Adds you to the list of people currently using the timer.
            If you're in this list, you will receive a private message if the
            timer's period changes or if it starts/pauses/stops.
        """

        channel = self.bot.spoof(ctx.author, ctx.channel)

        interface = self.bot.get_interface(channel)
        if ctx.author not in interface.subbed:
            interface.add_sub(ctx.author, datetime.utcnow())

            interface.restart_inactivity()

            log = (ctx.author.display_name + " has subscribed.")
            send = "You've successfully subscribed to this timer, {}!" \
                .format(ctx.author.display_name)
        else:
            log = (ctx.author.display_name + " tried to subscribe to " +
                   "this timer, but he was already added")
            send = ("You're already subscribed. " +
                    "I'll let you know of any changes!")

        lib.log(log, channel_id=channel.id)
        await ctx.send(send, delete_after=self.bot.ans_lifespan)

    @timer.command(name="unsub")
    @commands.check(checks.whitelisted)
    async def timer_unsub(self, ctx: commands.Context):
        """ Removes you from the list of people currently using the timer.
        """

        channel = self.bot.spoof(ctx.author, ctx.channel)

        result = 0

        interface = self.bot.get_interface(channel)
        if ctx.author in interface.subbed:
            result = interface.remove_sub(ctx.author)

            log = (ctx.author.display_name + " has un-subscribed.")
            send = "You've successfully un-subscribed to this timer, {}!" \
                .format(ctx.author.display_name)
        else:
            log = (ctx.author.display_name + " tried to un-subscribe "
                                             "to this timer, but he was not in the list")
            send = "You're not subscribed to this timer... "

        lib.log(log, channel_id=channel.id)
        await ctx.send(send, delete_after=self.bot.ans_lifespan)
        if result == -1:
            await ctx.send("Timer now has no subs. Will stop after {} "
                           "minutes unless someone subscribes!"
                           .format(self.bot.timer_inactivity_allowed),
                           delete_after=self.bot.ans_lifespan)
        elif result == -2:
            await self.bot.remove_messages(channel)

            await ctx.send("Timer has stopped since it was paused and "
                           "everyone un-subscribed")

    @timer.command(name="start")
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_start(self, ctx: commands.Context, period_idx=1):
        """ Starts the timer with the recorded setup. The timer must be
            correctly set up and not running for it to work.

        :param period_idx: The index of the period to start from, from 1 to n.
        :type period_idx: int; 1 <= period_idx <= amount of periods
        """

        channel = self.bot.spoof(ctx.author, ctx.channel)

        interface = self.bot.get_interface(channel)
        timer = interface.timer
        if timer.start():
            if not 0 < period_idx <= len(timer.periods):
                period_idx = 1

            try:
                if interface.restart_inactivity():
                    await ctx.send("Timer has no subs. Will stop after"
                                   " {} minutes unless someone subscribes!"
                                   .format(self.bot.timer_inactivity_allowed),
                                   delete_after=self.bot.ans_lifespan)

                await self.bot.run_timer(channel, period_idx - 1)
            except discord.errors.HTTPException:
                await ctx.send("@here\n"
                               "Connection interrupted, please resume! (1)")
                timer.pause()
        else:
            lib.log(ctx.author +
                    " tried to start a timer that was already running.",
                    channel_id=channel.id)
            await ctx.send("This channel's timer is already running",
                           delete_after=self.bot.ans_lifespan)

    @timer.command(name="resume")
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_resume(self, ctx: commands.Context):
        """ Resumes a paused timer.
        """

        channel = self.bot.spoof(ctx.author, ctx.channel)

        if self.bot.get_interface(channel).timer.resume():
            await self.bot.run_timer(channel)
        else:
            lib.log("Unable to resume timer, stopped or already running.",
                    channel_id=channel.id)
            await ctx.send("**grumble grumble.** The timer is " +
                           "stopped or already running, I can't " +
                           "resume that!",
                           delete_after=self.bot.ans_lifespan)

    @timer.command(name="pause")
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_pause(self, ctx: commands.Context):
        """ Pauses the timer, if it's running. Keeps all settings and current
            period and time.
        """

        channel = self.bot.spoof(ctx.author, ctx.channel)

        interface = self.bot.get_interface(channel)
        if len(interface.subbed) == 0:
            if interface.timer.stop():
                send = "No subs detected, timer will instead stop soon."
                await ctx.send(send, delete_after=interface.timer.step)
            else:
                await self.bot.remove_messages(channel)

                send = "No subs detected, timer has stopped instead."
                await ctx.send(send, tts=interface.tts)
            log = ("Attempted to pause the timer, but due to the lack of subs, "
                   "it will be stopped instead")
        elif interface.timer.pause():
            log = "Timer will be paused soon."
            await ctx.send(log, delete_after=interface.timer.step)

        else:
            log = "Could not pause timer, stopped or already running."
            await ctx.send("I cannot stop something that isn't moving.",
                           delete_after=self.bot.ans_lifespan)

        lib.log(log, channel_id=channel.id)

    @timer.command(name="stop")
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_stop(self, ctx: commands.Context):
        """ Stops the timer, if it's running.
            Resets the current period and time, but keeps the setup.
        """

        channel = self.bot.spoof(ctx.author, ctx.channel)

        interface = self.bot.get_interface(channel)
        if interface.timer.stop():
            send = "Timer will stop soon."
            await ctx.send(send, delete_after=interface.timer.step)

        else:
            await self.bot.remove_messages(channel)

            send = "Timer has stopped."
            await ctx.send(send, tts=interface.tts)

        lib.log(send, channel_id=channel.id)

    @timer.command(name="goto")
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_goto(self, ctx: commands.Context, period_idx):
        """ Skips to the n-th period, assuming the periods' indexes go
            from 1 to the amount of them.

        :param period_idx: The index of the period to start from, from 1 to n.
        :type period_idx: 'next' or int such that 1 <= period_idx <= n,
            n being the amount of periods set.
        """

        channel = self.bot.spoof(ctx.author, ctx.channel)
        interface = self.bot.get_interface(channel)

        if period_idx == "next":
            idx = interface.timer.get_period(True) + 1
        else:
            try:
                idx = int(period_idx)
            except TypeError:
                raise commands.BadArgument

        label = interface.timer.goto(idx)

        if label is not None:
            log = send = "Moved to period number {!s} ({})".format(idx, label)

            if interface.timer.get_state() != State.STOPPED:
                await interface.list_message.edit(content=interface.timer
                                                  .list_periods())

                if interface.timer.get_state() == State.PAUSED:
                    await interface.time_message.edit(content=interface.timer
                                                      .time())
        else:
            log = "Invalid period number entered when trying goto command."
            send = "Invalid period number."

        lib.log(log, channel_id=channel.id)
        await ctx.send(send, delete_after=self.bot.ans_lifespan)

    @timer.command(name="reset")
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_reset(self, ctx: commands.Context):
        """ Resets the timer setup.
        """

        channel = self.bot.spoof(ctx.message.author, ctx.channel)

        interface = self.bot.get_interface(channel)
        if interface.timer.get_state() == State.STOPPED:
            interface.timer.set_state(None)

            interface.timer = None
            interface.time_message = None
            interface.list_message = None

            log = ctx.author.display_name + " reset the timer."
            send = "Successfully reset session configuration."
        else:
            log = (ctx.author.display_name + " tried resetting a timer that "
                                             "was running or paused.")
            send = "Cannot do that while the timer is not stopped."

        lib.log(log, channel_id=channel.id)
        await ctx.send(send, delete_after=self.bot.ans_lifespan)

    @timer.command(name="superreset")
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.has_permission)
    async def timer_superreset(self, ctx: commands.Context):
        """ Ignores all conditions and resets the channel's timer.
            Requires elevated permissions.
        """

        channel = self.bot.spoof(ctx.author, ctx.channel)

        interface = self.bot.get_interface(channel)
        if interface.timer.get_state() == State.RUNNING:
            self.bot.timers_running -= 1
            await self.bot.update_status()

        await self.bot.remove_messages(channel)

        interface.timer = None

        lib.log("Successfully forced a reset on this channel's timer.",
                channel_id=channel.id)
        await ctx.send("Timer has been force-reset",
                       delete_after=self.bot.ans_lifespan)

    @timer.command(name="time")
    @commands.check(checks.channel_has_timer)
    async def timer_time(self, ctx: commands.Context):
        """ Gives the user the current period and time of the timer.
        """

        channel = self.bot.spoof(ctx.author, ctx.channel)

        send = self.bot.get_interface(channel).timer.time(True)

        lib.log(send, channel_id=channel.id)
        await ctx.send(send, delete_after=self.bot.ans_lifespan * 2)

    @timer.command(name="status")
    @commands.check(checks.channel_has_timer)
    async def timer_status(self, ctx: commands.Context):
        """ Tells whether the timer is stopped, running or paused,
            if it's correctly set up and if it will soon stop or pause.
        """

        channel = self.bot.spoof(ctx.author, ctx.channel)

        send = self.bot.get_interface(channel).timer.show_status()

        lib.log(send, channel_id=channel.id)
        await ctx.send(send, delete_after=self.bot.ans_lifespan * 2)

    @timer.command(name="tts")
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_tts(self, ctx: commands.Context, toggle: str = None):
        """ Sets the TTS option on or off for the channel.

        :param toggle: Whether to turn on or off the TTS option. If no option
            is provided, it will toggle it
        :type toggle: str
        """

        channel = self.bot.spoof(ctx.author, ctx.channel)
        interface = self.bot.get_interface(channel)

        log = send = None

        if toggle is None:
            interface.tts = not interface.tts
            toggle = "ok"
        else:
            try:
                interface.tts = lib.to_boolean(toggle)

            except TypeError:
                toggle = None
                log = "TTS command failed, bad argument."
                send = ("I could not understand if you wanted to " +
                        "turn TTS on or off.")

        if toggle is not None:
            status = ("on" if interface.tts else "off")
            log = "TTS now " + status + " for this channel."
            send = "Text-to-speech now " + status + " for this channel."

        lib.log(log, channel_id=channel.id,
                level=logging.WARN if toggle is None else logging.INFO)
        await ctx.send(send, tts=interface.tts and toggle is not None,
                       delete_after=self.bot.ans_lifespan)

    @commands.command(name="timers")
    async def timers_list(self, ctx: commands.Context):
        """ Shows a list of all active timers.
        """

        t_list = ""
        for channel, timer in self.bot.valid_timers().items():
            # Channel name
            t_list += channel.mention + ":\n" + timer.show_status() + "\n"

        if t_list != "":
            await ctx.send(t_list, delete_after=self.bot.ans_lifespan * 3)
        else:
            await ctx.send("No timers set up.",
                           delete_after=self.bot.ans_lifespan)

    async def _setup(self, ctx, timer_format, repeat, count_back):

        channel = self.bot.spoof(ctx.author, ctx.channel)

        timer_format = await self._translate_keyword(timer_format,
                                                     ctx.guild.id,
                                                     channel.id, ctx)
        if timer_format is None:
            return

        # Parse the countdown and looping arguments with the custom function.
        try:
            loop = config.get_config().get_boolean('timer.looping_default') if \
                repeat is None else lib.to_boolean(repeat)

            countdown = config.get_config() \
                .get_boolean('timer.countdown_default') if count_back is None \
                else lib.to_boolean(count_back)

        except TypeError:
            lib.log("Could not parse boolean arguments '{!s}' and '{!s}'"
                    .format(repeat, count_back), channel_id=channel.id)
            await ctx.send("Invalid arguments received, please try again.",
                           delete_after=self.bot.ans_lifespan)
            return

        interface = self.bot.get_interface(channel)
        if interface.timer is None:
            interface.timer = PomodoroTimer(interface)
            times = interface.timer.setup(timer_format, loop, countdown)

            if times is not None:
                log = ("Correctly set up timer config: {}."
                       "\nLooping is **{}**\nCountdown is **{}**") \
                    .format(times, "ON" if loop else "OFF",
                            "ON" if countdown else "OFF")
                send = log
            else:
                interface.timer = None
                log = ("Could not set the periods correctly, "
                       "command 'setup' failed.")
                send = ("I did not understand what you wanted, "
                        "please try again!")

        else:  # channel_id is in p_timers.keys()
            log = ("Rejecting setup command, there is a period set already "
                   "established.")
            send = ("I'm already set and ready to go, please use the reset "
                    "command if you want to change the timer configuration.")

        lib.log(log, channel_id=channel.id)
        await ctx.send(send, delete_after=self.bot.ans_lifespan)

    async def _translate_keyword(self, keyword: str, server_id: int,
                                 channel_id: int, ctx):
        if keyword == "help":
            example_periods = ', '.join(str(period.time) for period in
                                        PomodoroTimer
                                        .parse_format(SAFE_DEFAULT_FMT))
            await ctx.send(("**Example:**\n\t {}setup {}\n\t"
                            "_This will give you a sequence of {}_")
                           .format(self.bot.command_prefix,
                                   SAFE_DEFAULT_FMT,
                                   example_periods),
                           delete_after=self.bot.ans_lifespan * 2)

            return None

        if keyword == 'default':
            # fetch default setup string from config,
            # or fallback to "Safe Default"
            translation = config.get_config().get_str(
                'timer.channel_whitelist.{}.{}'
                    .format(str(server_id), str(channel_id)))
            if translation is None:
                lib.log("No setup configured for this channel. Using the "
                        "safe default option", channel_id=channel_id)
                translation = SAFE_DEFAULT_FMT

            return translation
        if keyword == 'blank':
            pass

        keys = keyword.split(':', 1)
        if len(keys) < 2:
            return keyword
        if keys[0] == 'pomodoro':
            durations = keys[1].split(',', 2)
            return _pomodoro_config(durations[0], durations[1], durations[2])

        if keys[0] == 'saved':
            translation = config.get_config().get_str(
                'timer.saved_formats.' + keys[1])
            return translation
        return keyword


def _pomodoro_config(productivity_t, break_t, long_break_t):
    return "(2xStudy/Work:{x},Break:{y}),Study/Work:{x},Long_Break:{z}" \
        .format(x=productivity_t, y=break_t, z=long_break_t)


def setup(bot: PomodoroBot):
    bot.add_cog(TimerCommands(bot))
