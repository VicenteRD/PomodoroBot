from discord.ext import commands
from discord.ext.commands import errors as cmd_err

from pomodorobot.bot import PomodoroBot
from pomodorobot.timer import PomodoroTimer, State

import pomodorobot.ext.checks as checks
import pomodorobot.lib as lib


class TimerCommands:
    """ Represents all the possible commands that influence a timer.
    """

    def __init__(self, bot: PomodoroBot):
        self.bot = bot

    @commands.group(name="timer", pass_context=True)
    @commands.check(checks.whitelisted)
    async def timer(self, ctx):
        """ Controls the channel's timer.
            None of the sub-commands will really work without using `setup`
            first.
        """

        if ctx.invoked_subcommand is None:
            sect = ctx.message.content.split(' ')
            if len(sect) < 2 or sect[1] is None:
                log = "{} invoked an incomplete timer command."

                send = "Timers are allowed here. Now what?"
            else:
                log = "{} invoked an invalid timer command."
                send = "Invalid timer sub-command."
        else:
            return

        lib.log(log.format(lib.get_author_name(ctx)),
                channel_id=lib.get_channel_id(ctx))
        await self.bot.say(send, delete_after=self.bot.ans_lifespan)

    @timer.command(name="setup", pass_context=True)
    @commands.check(checks.whitelisted)
    @commands.check(checks.unlocked_or_allowed)
    async def setup(self, ctx: commands.Context, timer_format="default",
                    repeat="True", count_back="True"):
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

        channel_id = lib.get_channel_id(ctx)

        if timer_format == "help":
            send = "**Example:**\n\t {}setup {}"\
                .format(self.bot.command_prefix, self.bot.default_setup['in'])

            send += "\n\t_This will give you a sequence of {}_"\
                .format(self.bot.default_setup['out'])
            await self.bot.say(send, delete_after=self.bot.ans_lifespan * 2)
            return

        if timer_format == "default":
            timer_format = self.bot.default_setup['in']

        result = -1
        if channel_id not in self.bot.timers.keys():
            try:
                loop = lib.to_boolean(repeat)
                countdown = lib.to_boolean(count_back)

                self.bot.timers[channel_id] = PomodoroTimer()
                self.bot.time_messages[channel_id] = None
                self.bot.list_messages[channel_id] = None

                result, times = self.bot.timers[channel_id]\
                    .setup(timer_format, loop, countdown)

                if result == 0 and times is not None:
                    settings = (
                        "Correctly set up timer config: " + times + "." +
                        "\nLooping is **" + ("ON" if repeat else "OFF") +
                        "**\nCountdown is **" +
                        ("ON" if countdown else "OFF") + "**")

                    lib.log(settings, channel_id=channel_id)
                    await self.bot.say(settings,
                                       delete_after=self.bot.ans_lifespan * 2)
                else:
                    del self.bot.timers[channel_id]
                    del self.bot.time_messages[channel_id]
                    del self.bot.list_messages[channel_id]

            except cmd_err.BadArgument:
                result = -4

        if result == -1:  # channel_id is in p_timers.keys() or len(times) > 0
            log = ("Rejecting setup command, there is a period set already " +
                   "established.")
            send = ("I'm already set and ready to go, please use the reset " +
                    "command if you want to change the timer configuration.")

        elif result == -2:  # state == RUNNING or PAUSED
            log = ("Someone tried to modify the timer while it was already " +
                   "running.")
            send = "Please stop the timer completely before modifying it."

        elif result == -3:  # format error
            log = ("Could not set the periods correctly, command 'setup' " +
                   "failed.")
            send = "I did not understand what you wanted, please try again!"

        elif result == -4:  # repeat or count_back are not valid booleans
            log = "Could not parse boolean arguments '{}' and '{}'"\
                .format(repeat, count_back)
            send = "Invalid arguments received, please try again."
        else:
            return

        lib.log(log, channel_id=channel_id)
        await self.bot.say(send, delete_after=self.bot.ans_lifespan)

    @timer.command(name="start", pass_context=True)
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_start(self, ctx: commands.Context, period_idx=1):
        """ Starts the timer with the recorded setup. The timer must be
            correctly set up and not running for it to work.

        :param period_idx: The index of the period to start from, from 1 to n.
        :type period_idx: int; 1 <= period_idx <= amount of periods
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))

        if self.bot.timers[channel_id].start():
            if not 0 < period_idx <= len(self.bot.timers[channel_id].times):
                period_idx = 1

            await self.bot.run_timer(channel_id, period_idx - 1)
        else:
            lib.log(lib.get_author_name(ctx) +
                    " tried to start a timer that was already running.",
                    channel_id=channel_id)
            await self.bot.say("This channel's timer is already running",
                               delete_after=self.bot.ans_lifespan)

    @timer.command(name="resume", pass_context=True)
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_resume(self, ctx: commands.Context):
        """ Resumes a paused timer.
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))

        if self.bot.timers[channel_id].resume():
            await self.bot.run_timer(channel_id)
        else:
            lib.log("Unable to resume timer, stopped or already running.",
                    channel_id=channel_id)
            await self.bot.say("**grumble grumble.** The timer is " +
                               "stopped or already running, I can't " +
                               "resume that!",
                               delete_after=self.bot.ans_lifespan)

    @timer.command(name="pause", pass_context=True)
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_pause(self, ctx: commands.Context):
        """ Pauses the timer, if it's running. Keeps all settings and current
            period and time.
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))

        if self.bot.timers[channel_id].pause():
            log = "Timer will be paused soon."
            await self.bot.say(log, delete_after=self.bot.timer_step)

        else:
            log = "Could not pause timer, stopped or already running."
            await self.bot.say("I cannot stop something that isn't moving.",
                               delete_after=self.bot.ans_lifespan)

        lib.log(log, channel_id=channel_id)

    @timer.command(name="stop", pass_context=True)
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_stop(self, ctx: commands.Context):
        """ Stops the timer, if it's running.
            Resets the current period and time, but keeps the setup.
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))

        if self.bot.timers[channel_id].stop():
            send = "Timer will stop soon."
            await self.bot.say(send, delete_after=self.bot.timer_step)

        else:
            await self.bot.remove_messages(channel_id)
            send = "Timer has stopped."
            await self.bot.say(send, tts=self.bot.tts)

        lib.log(send, channel_id=channel_id)

    @timer.command(name="goto", pass_context=True)
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_goto(self, ctx: commands.Context, period_idx: int):
        """ Skips to the n-th period, assuming the periods' indexes go
            from 1 to the amount of them.

        :param period_idx: The index of the period to start from, from 1 to n.
        :type period_idx: int; 1 <= period_idx <= amount of periods
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))

        label = self.bot.timers[channel_id].goto(period_idx)

        if label is not None:
            log = "Moved to period number {!s} ({})".format(period_idx, label)
            send = log

            await self.bot.edit_message(
                self.bot.list_messages[channel_id],
                self.bot.timers[channel_id].list_periods()
            )

            if self.bot.timers[channel_id].state == State.PAUSED:
                await self.bot.edit_message(
                    self.bot.time_messages[channel_id],
                    self.bot.timers[channel_id].time()
                )
        else:
            log = "Invalid period number entered when trying goto command."
            send = "Invalid period number."

        lib.log(log, channel_id=channel_id)
        await self.bot.say(send, delete_after=self.bot.ans_lifespan)

    @timer.command(name="reset", pass_context=True)
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_reset(self, ctx: commands.Context):
        """ Resets the timer setup.
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))

        if self.bot.timers[channel_id].state == State.STOPPED:
            del self.bot.timers[channel_id]

            del self.bot.time_messages[channel_id]
            del self.bot.list_messages[channel_id]

            log = lib.get_author_name(ctx) + " reset the timer."
            send = "Successfully reset session configuration."
        else:
            log = (lib.get_author_name(ctx) + " tried resetting a timer that " +
                   "was running or paused.")
            send = "Cannot do that while the timer is not stopped."

        lib.log(log, channel_id=channel_id)
        await self.bot.say(send, delete_after=self.bot.ans_lifespan)

    @timer.command(name="force reset", pass_context=True, hidden=True)
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.has_permission)
    async def timer_forcereset(self, ctx: commands.Context):
        """ Ignores all conditions and resets the channel's timer.
            Requires elevated permissions.
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))

        if self.bot.timers[channel_id].state == State.RUNNING:
            self.bot.timers_running -= 1
            await self.bot.update_status()

        await self.bot.remove_messages(channel_id)

        del self.bot.time_messages[channel_id]
        del self.bot.list_messages[channel_id]

        del self.bot.timers[channel_id]

        lib.log("Successfully forced a reset on this channel's timer.",
                channel_id=channel_id)
        await self.bot.say("Timer has been force-reset",
                           delete_after=self.bot.ans_lifespan)

    @timer.command(name="time", pass_context=True)
    @commands.check(checks.channel_has_timer)
    async def timer_time(self, ctx: commands.Context):
        """ Gives the user the current period and time of the timer.
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))

        send = self.bot.timers[channel_id].time(True)

        lib.log(send, channel_id=channel_id)
        await self.bot.say(send, delete_after=self.bot.ans_lifespan * 2)

    @timer.command(name="status", pass_context=True)
    @commands.check(checks.channel_has_timer)
    async def timer_status(self, ctx: commands.Context):
        """ Tells whether the timer is stopped, running or paused,
            if it's correctly set up and if it will soon stop or pause.
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))

        send = self.bot.timers[channel_id].status()

        lib.log(send, channel_id=channel_id)
        await self.bot.say(send, delete_after=self.bot.ans_lifespan * 2)

    @timer.command(name="tts", pass_context=True)
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def tts(self, ctx: commands.Context, toggle: str):
        """ Sets the TTS option on or off for the channel.

        :param toggle: Whether to turn on or off the TTS option
        :type toggle: str
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))

        try:
            timer = self.bot.timers[channel_id]
            timer.tts = lib.to_boolean(toggle)
            say = ("on" if timer.tts else "off")

            log = "TTS now " + say + " for this channel."
            send = "Text-to-speech now " + say + " for this channel."

        except cmd_err.BadArgument:
            log = "TTS command failed, bad argument."
            send = "I could not understand if you wanted to turn TTS on or off."

        lib.log(log, channel_id=channel_id)
        await self.bot.say(send, tts=self.bot.tts,
                           delete_after=self.bot.ans_lifespan)


def setup(bot: PomodoroBot):
    bot.add_cog(TimerCommands(bot))
