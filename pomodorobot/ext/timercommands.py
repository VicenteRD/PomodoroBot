import logging

from discord.ext import commands
from discord.ext.commands import errors as cmd_err

import pomodorobot.ext.checks as checks
import pomodorobot.config as config
import pomodorobot.lib as lib

from pomodorobot.bot import PomodoroBot
from pomodorobot.timer import PomodoroTimer, State

SAFE_DEFAULT_FMT = "(2xStudy:32,Break:8),Study:32,Long_Break:15"


class TimerCommands:
    """ Represents all the possible commands that influence a timer.
    """

    def __init__(self, bot: PomodoroBot):
        self.bot = bot

    @commands.group(name="timer", pass_context=True)
    @commands.check(checks.whitelisted)
    async def timer(self, ctx):
        """ Controls the channel's timer. Do '!help timer' for sub-commands
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
        """  # TODO. Use the new whitelist config

        if timer_format == "help":
            send = "**Example:**\n\t {}setup {}" \
                .format(self.bot.command_prefix, SAFE_DEFAULT_FMT)

            send += "\n\t_This will give you a sequence of {}_" \
                .format(PomodoroTimer.parse_format(SAFE_DEFAULT_FMT))
            await self.bot.say(send, delete_after=self.bot.ans_lifespan * 2)
            return

        channel_id = lib.get_channel_id(ctx)

        # Load default if the option was opted for.
        if timer_format == "default":

            channel_default = config.get_config().get_str(
                'timer.channel_whitelist.' +
                lib.get_server_id(ctx) + '.' + channel_id)

            if channel_default is not None:
                timer_format = channel_default
            else:
                lib.log("No setup configured for this channel. Using the " +
                        "safe default option", channel_id=channel_id)
                timer_format = SAFE_DEFAULT_FMT

        # Parse the countdown and looping arguments with the custom function.
        try:
            if repeat is None:
                loop = config.get_config().get_boolean('timer.looping_default')
            else:
                loop = lib.to_boolean(repeat)

            if count_back is None:
                countdown = config.get_config() \
                    .get_boolean('timer.countdown_default')
            else:
                countdown = lib.to_boolean(count_back)

        except TypeError:
            lib.log("Could not parse boolean arguments '{!s}' and '{!s}'"
                    .format(repeat, count_back), channel_id=channel_id)
            await self.bot.say("Invalid arguments received, please try again.",
                               delete_after=self.bot.ans_lifespan)
            return

        if channel_id not in self.bot.timers.keys():
            self.bot.timers[channel_id] = PomodoroTimer()

            times = self.bot.timers[channel_id] \
                .setup(timer_format, loop, countdown)

            if times is not None:
                # Initialize the messages if the timer was correctly setup.
                self.bot.time_messages[channel_id] = None
                self.bot.list_messages[channel_id] = None

                send = log = (
                    "Correctly set up timer config: " + times + "." +
                    "\nLooping is **" + ("ON" if loop else "OFF") +
                    "**\nCountdown is **" +
                    ("ON" if countdown else "OFF") + "**")
            else:
                del self.bot.timers[channel_id]

                log = ("Could not set the periods correctly, " +
                       "command 'setup' failed.")
                send = ("I did not understand what you wanted, " +
                        "please try again!")

        else:  # channel_id is in p_timers.keys()
            log = ("Rejecting setup command, there is a period set already " +
                   "established.")
            send = ("I'm already set and ready to go, please use the reset " +
                    "command if you want to change the timer configuration.")

        lib.log(log, channel_id=channel_id)
        await self.bot.say(send, delete_after=self.bot.ans_lifespan)

    @timer.command(name="sub", pass_context=True)
    @commands.check(checks.channel_has_timer)
    async def timer_sub(self, ctx: commands.Context):
        """

        :param ctx:
        :return:
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))
        author = ctx.message.author

        if author not in self.bot.timers[channel_id].subbed:
            # TODO: check if he's subbed to another timer.
            self.bot.timers[channel_id].subbed.append(author)
            log = author.id + " has subscribed to this timer."
            send = "You've successfully subscribed to this timer, {}!"\
                .format(lib.get_author_name(ctx, True))
        else:
            log = (author.id + " tried to subscribe to this timer, but he " +
                   "was already added")
            send = ("You're already subscribed. " +
                    "I'll let you know of any changes!")

        lib.log(log, channel_id=channel_id)
        await self.bot.say(send, delete_after=self.bot.ans_lifespan)

    @timer.command(name="unsub", pass_context=True)
    @commands.check(checks.channel_has_timer)
    async def timer_unsub(self, ctx: commands.Context):
        """

        :param ctx:
        :return:
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))
        author = ctx.message.author

        if author in self.bot.timers[channel_id].subbed:
            self.bot.timers[channel_id].subbed.append(author)
            log = author.id + " has un-subscribed to this timer."
            send = "You've successfully un-subscribed to this timer, {}!"\
                .format(lib.get_author_name(ctx, True))
        else:
            log = (author.id + " tried to un-subscribe to this timer, but he " +
                   "was not in the list")
            send = "You're not subscribed to this timer... "

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
            if not 0 < period_idx <= len(self.bot.timers[channel_id].periods):
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
    async def timer_goto(self, ctx: commands.Context, period_idx):
        """ Skips to the n-th period, assuming the periods' indexes go
            from 1 to the amount of them.

        :param period_idx: The index of the period to start from, from 1 to n.
        :type period_idx: 'next' or int such that 1 <= period_idx <= n,
            n being the amount of periods set.
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))

        if period_idx == "next":
            idx = self.bot.timers[channel_id].curr_period + 1
        else:
            try:
                idx = int(period_idx)
            except TypeError:
                raise commands.BadArgument

        label = self.bot.timers[channel_id].goto(idx)

        if label is not None:
            log = "Moved to period number {!s} ({})".format(idx, label)
            send = log

            await self.bot.edit_message(
                self.bot.list_messages[channel_id],
                self.bot.timers[channel_id].list_periods()
            )

            if self.bot.timers[channel_id].get_state() == State.PAUSED:
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

        if self.bot.timers[channel_id].get_state() == State.STOPPED:
            self.bot.timers[channel_id].set_state(None)
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

    @timer.command(name="superreset", pass_context=True)
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.has_permission)
    async def timer_forcereset(self, ctx: commands.Context):
        """ Ignores all conditions and resets the channel's timer.
            Requires elevated permissions.
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))

        if self.bot.timers[channel_id].get_state() == State.RUNNING:
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
    async def tts(self, ctx: commands.Context, toggle: str = None):
        """ Sets the TTS option on or off for the channel.

        :param toggle: Whether to turn on or off the TTS option. If no option
            is provided, it will toggle it
        :type toggle: str
        """

        channel_id = self.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))
        timer = self.bot.timers[channel_id]

        log = send = None
        fail = False
        if toggle is None:
            timer.tts = not timer.tts
        else:
            try:
                timer.tts = lib.to_boolean(toggle)

            except cmd_err.BadArgument:
                fail = True
                log = "TTS command failed, bad argument."
                send = ("I could not understand if you wanted to " +
                        "turn TTS on or off.")

        if log is None or send is None:
            status = ("on" if timer.tts else "off")
            log = "TTS now " + status + " for this channel."
            send = "Text-to-speech now " + status + " for this channel."

        lib.log(log, channel_id=channel_id,
                level=logging.WARN if fail else logging.INFO)
        await self.bot.say(send, tts=timer.tts and not fail,
                           delete_after=self.bot.ans_lifespan)

    @commands.command(name="timers", pass_context=True)
    async def timers_list(self, ctx: commands.Context):
        server = ctx.message.server
        if server is None:
            await self.bot.say("Timers are not allowed in private messages.",
                               delete_after=self.bot.ans_lifespan)
            return

        t_list = ""
        for c_id, timer in self.bot.timers.items():
            t_list += server.get_channel(c_id).mention + ": "
            t_list += timer.list_periods(True) + "\n\n"
            t_list += "\n".join('\t' + l for l in timer.time().split('\n'))
            t_list += "\n\n"

        await self.bot.say(t_list, delete_after=self.bot.ans_lifespan * 3)


def setup(bot: PomodoroBot):
    bot.add_cog(TimerCommands(bot))
