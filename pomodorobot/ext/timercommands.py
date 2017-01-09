import yaml
import datetime
import logging
import discord.errors

from discord.ext import commands

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
        """

        if timer_format == "help":
            send = "**Example:**\n\t {}setup {}" \
                .format(self.bot.command_prefix, SAFE_DEFAULT_FMT)

            send += "\n\t_This will give you a sequence of {}_" \
                .format(PomodoroTimer.parse_format(SAFE_DEFAULT_FMT))
            await self.bot.say(send, delete_after=self.bot.ans_lifespan * 2)
            return

        channel = self.bot.spoof(ctx.message.author, lib.get_channel(ctx))

        # Load default if the option was opted for.
        if timer_format == "default":

            channel_default = config.get_config().get_str(
                'timer.channel_whitelist.' +
                lib.get_server_id(ctx) + '.' + channel.id)

            if channel_default is not None:
                timer_format = channel_default
            else:
                lib.log("No setup configured for this channel. Using the " +
                        "safe default option", channel_id=channel.id)
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
                    .format(repeat, count_back), channel_id=channel.id)
            await self.bot.say("Invalid arguments received, please try again.",
                               delete_after=self.bot.ans_lifespan)
            return

        interface = self.bot.get_interface(channel)
        if interface.timer is None:
            interface.timer = PomodoroTimer(interface)

            times = interface.timer.setup(timer_format, loop, countdown)

            if times is not None:
                send = log = (
                    "Correctly set up timer config: " + times + "." +
                    "\nLooping is **" + ("ON" if loop else "OFF") +
                    "**\nCountdown is **" +
                    ("ON" if countdown else "OFF") + "**")
            else:
                interface.timer = None

                log = ("Could not set the periods correctly, " +
                       "command 'setup' failed.")
                send = ("I did not understand what you wanted, " +
                        "please try again!")

        else:  # channel_id is in p_timers.keys()
            log = ("Rejecting setup command, there is a period set already " +
                   "established.")
            send = ("I'm already set and ready to go, please use the reset " +
                    "command if you want to change the timer configuration.")

        lib.log(log, channel_id=channel.id)
        await self.bot.say(send, delete_after=self.bot.ans_lifespan)

    @timer.command(name="sub", pass_context=True)
    @commands.check(checks.whitelisted)
    async def timer_sub(self, ctx: commands.Context):
        """ Adds you to the list of people currently using the timer.
            If you're in this list, you will receive a private message if the
            timer's period changes or if it starts/pauses/stops.
        """

        author = ctx.message.author
        channel = self.bot.spoof(author, lib.get_channel(ctx))

        interface = self.bot.get_interface(channel)
        if author not in interface.subbed:
            interface.subbed.append(author)

            self._add_attendance(ctx,)

            log = (lib.get_author_name(ctx, True) +
                   " has subscribed to this timer.")
            send = "You've successfully subscribed to this timer, {}!"\
                .format(lib.get_author_name(ctx, True))
        else:
            log = (lib.get_author_name(ctx, True) + " tried to subscribe to " +
                   "this timer, but he was already added")
            send = ("You're already subscribed. " +
                    "I'll let you know of any changes!")

        lib.log(log, channel_id=channel.id)
        await self.bot.say(send, delete_after=self.bot.ans_lifespan)

    @timer.command(name="unsub", pass_context=True)
    @commands.check(checks.whitelisted)
    async def timer_unsub(self, ctx: commands.Context):
        """ Removes you from the list of people currently using the timer.
        """

        channel = self.bot.spoof(ctx.message.author, lib.get_channel(ctx))
        author = ctx.message.author

        interface = self.bot.get_interface(channel)
        if author in interface.subbed:
            interface.subbed.remove(author)

            log = (lib.get_author_name(ctx, True) +
                   " has un-subscribed to this timer.")
            send = "You've successfully un-subscribed to this timer, {}!"\
                .format(lib.get_author_name(ctx, True))
        else:
            log = (lib.get_author_name(ctx, True) + " tried to un-subscribe " +
                   "to this timer, but he was not in the list")
            send = "You're not subscribed to this timer... "

        lib.log(log, channel_id=channel.id)
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

        channel = self.bot.spoof(ctx.message.author, lib.get_channel(ctx))

        timer = self.bot.get_interface(channel).timer
        if timer.start():
            if not 0 < period_idx <= len(timer.periods):
                period_idx = 1

            try:
                await self.bot.run_timer(channel, period_idx - 1)
            except discord.errors.HTTPException:
                await self.bot.say("@here\n"
                                   "Connection interrupted, please resume! (1)")
                self.bot.get_interface(channel).timer.pause()
        else:
            lib.log(lib.get_author_name(ctx) +
                    " tried to start a timer that was already running.",
                    channel_id=channel.id)
            await self.bot.say("This channel's timer is already running",
                               delete_after=self.bot.ans_lifespan)

    @timer.command(name="resume", pass_context=True)
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_resume(self, ctx: commands.Context):
        """ Resumes a paused timer.
        """

        channel = self.bot.spoof(ctx.message.author, lib.get_channel(ctx))

        if self.bot.get_interface(channel).timer.resume():
            await self.bot.run_timer(channel)
        else:
            lib.log("Unable to resume timer, stopped or already running.",
                    channel_id=channel.id)
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

        channel = self.bot.spoof(ctx.message.author, lib.get_channel(ctx))

        interface = self.bot.get_interface(channel)
        if interface.timer.pause():
            log = "Timer will be paused soon."
            await self.bot.say(log, delete_after=interface.timer.step)

        else:
            log = "Could not pause timer, stopped or already running."
            await self.bot.say("I cannot stop something that isn't moving.",
                               delete_after=self.bot.ans_lifespan)

        lib.log(log, channel_id=channel.id)

    @timer.command(name="stop", pass_context=True)
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_stop(self, ctx: commands.Context):
        """ Stops the timer, if it's running.
            Resets the current period and time, but keeps the setup.
        """

        channel = self.bot.spoof(ctx.message.author, lib.get_channel(ctx))

        interface = self.bot.get_interface(channel)
        if interface.timer.stop():
            send = "Timer will stop soon."
            await self.bot.say(send, delete_after=interface.timer.step)

        else:
            await self.bot.remove_messages(channel)

            interface.time_message = None
            interface.list_message = None

            send = "Timer has stopped."
            await self.bot.say(send, tts=interface.tts)

        lib.log(send, channel_id=channel.id)

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

        channel = self.bot.spoof(ctx.message.author, lib.get_channel(ctx))

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

            await self.bot.edit_message(interface.list_message,
                                        interface.timer.list_periods())

            if interface.timer.get_state() == State.PAUSED:
                await self.bot.edit_message(interface.time_message,
                                            interface.timer.time())
        else:
            log = "Invalid period number entered when trying goto command."
            send = "Invalid period number."

        lib.log(log, channel_id=channel.id)
        await self.bot.say(send, delete_after=self.bot.ans_lifespan)

    @timer.command(name="reset", pass_context=True)
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_reset(self, ctx: commands.Context):
        """ Resets the timer setup.
        """

        channel = self.bot.spoof(ctx.message.author, lib.get_channel(ctx))

        interface = self.bot.get_interface(channel)
        if interface.timer.get_state() == State.STOPPED:
            interface.timer.set_state(None)

            interface.timer = None
            interface.time_message = None
            interface.list_message = None

            log = lib.get_author_name(ctx) + " reset the timer."
            send = "Successfully reset session configuration."
        else:
            log = (lib.get_author_name(ctx) + " tried resetting a timer that " +
                   "was running or paused.")
            send = "Cannot do that while the timer is not stopped."

        lib.log(log, channel_id=channel.id)
        await self.bot.say(send, delete_after=self.bot.ans_lifespan)

    @timer.command(name="superreset", pass_context=True)
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.has_permission)
    async def timer_superreset(self, ctx: commands.Context):
        """ Ignores all conditions and resets the channel's timer.
            Requires elevated permissions.
        """

        channel = self.bot.spoof(ctx.message.author, lib.get_channel(ctx))

        interface = self.bot.get_interface(channel)
        if interface.timer.get_state() == State.RUNNING:
            self.bot.timers_running -= 1
            await self.bot.update_status()

        await self.bot.remove_messages(channel)

        interface.timer = None
        interface.time_message = None
        interface.list_message = None

        lib.log("Successfully forced a reset on this channel's timer.",
                channel_id=channel.id)
        await self.bot.say("Timer has been force-reset",
                           delete_after=self.bot.ans_lifespan)

    @timer.command(name="time", pass_context=True)
    @commands.check(checks.channel_has_timer)
    async def timer_time(self, ctx: commands.Context):
        """ Gives the user the current period and time of the timer.
        """

        channel = self.bot.spoof(ctx.message.author, lib.get_channel(ctx))

        send = self.bot.get_interface(channel).timer.time(True)

        lib.log(send, channel_id=channel.id)
        await self.bot.say(send, delete_after=self.bot.ans_lifespan * 2)

    @timer.command(name="status", pass_context=True)
    @commands.check(checks.channel_has_timer)
    async def timer_status(self, ctx: commands.Context):
        """ Tells whether the timer is stopped, running or paused,
            if it's correctly set up and if it will soon stop or pause.
        """

        channel = self.bot.spoof(ctx.message.author, lib.get_channel(ctx))

        send = self.bot.get_interface(channel).timer.status()

        lib.log(send, channel_id=channel.id)
        await self.bot.say(send, delete_after=self.bot.ans_lifespan * 2)

    @timer.command(name="tts", pass_context=True)
    @commands.check(checks.channel_has_timer)
    @commands.check(checks.unlocked_or_allowed)
    async def timer_tts(self, ctx: commands.Context, toggle: str = None):
        """ Sets the TTS option on or off for the channel.

        :param toggle: Whether to turn on or off the TTS option. If no option
            is provided, it will toggle it
        :type toggle: str
        """

        channel = self.bot.spoof(ctx.message.author, lib.get_channel(ctx))
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
        await self.bot.say(send, tts=interface.tts and toggle is not None,
                           delete_after=self.bot.ans_lifespan)

    @commands.command(name="timers", pass_context=True)
    async def timers_list(self):
        """ Shows a list of all active timers.
        """

        t_list = ""
        for channel, timer in self.bot.valid_timers().items():
            # Channel name
            t_list += channel.mention + ":\n```"

            # Current timer setup
            t_list += "\n  Setup       || " + timer.list_periods(True)
            t_list += ("\n\t Looping  : " +
                       ("On" if timer.repeat else "Off"))
            t_list += ("\n\t Countdown: " +
                       ("On" if timer.countdown else "Off"))

            # Current status
            t_list += "\n  Status      || "
            t_list += "\n\t\t\t\t ".join(l for l in timer.time().split('\n'))

            # Users subscribed
            t_list += "\n  Subscribed  || "
            t_list += ", ".join(lib.get_name(m, True)
                                for m in timer.get_users_subscribed())
            t_list += "." if len(timer.get_users_subscribed()) > 0 else ""

            t_list += "\n```\n"

        if t_list != "":
            await self.bot.say(t_list, delete_after=self.bot.ans_lifespan * 3)
        else:
            await self.bot.say("No timers set up.",
                               delete_after=self.bot.ans_lifespan)

    def _add_attendance(self, ctx):
        try:
            file = open(self.bot.attendance_file, 'r')
            attendance_info = yaml.load(file)
            file.close()

            if attendance_info is None or \
               not isinstance(attendance_info, dict) or \
               not attendance_info:
                attendance_info = {}

            server_id = lib.get_server_id(ctx)

            if server_id not in attendance_info.keys():
                attendance_info[server_id] = {}

            attendance_info[server_id][lib.get_author_name(ctx)] = \
                "\"{} UTC\""\
                .format(str(datetime.datetime.utcnow()).split('.')[0])

            file = open(self.bot.attendance_file, 'w')
            file.write(yaml.dump(attendance_info, default_flow_style=False))
            file.close()

        except IOError:
            lib.log("Failed to write attendance.")


def setup(bot: PomodoroBot):
    bot.add_cog(TimerCommands(bot))
