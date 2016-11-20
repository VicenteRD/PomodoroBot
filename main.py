import sys
import logging
import asyncio

from discord.ext.commands import errors as cmdErr

import pomodoroLib as lib
import timer as Timer
import bot as Bot
import config


USAGE = sys.argv[0] + " <token> [prefix] [admin_id]"

TOKEN = "" # can I delete this
ADMIN_ID = ""
STARTUP_MSG = ""
DEFAULT_TIMER = ""
BOT_ROLE_ID = ""

DESCRIPTION = '''A marinara timer bot that can be configured to your needs.'''

#BOT_FRIEND_ROLE_ID

logger = logging.getLogger()


bot = Bot.PomodoroBot(
	command_prefix = '!',
	description = DESCRIPTION,
	timer_step = 2,
	response_lifespan = 15,
	pm_help = True)

@bot.event
async def on_ready():
	print('Logged in as')
	print(bot.user.name)
	print(bot.user.id)
	print('------')

	await bot._update_status()
	for server in bot.servers :
		await bot.send_message(server, STARTUP_MSG)

@bot.command(pass_context = True)
async def setup(ctx, timerFormat = "default", repeat = "True",
		countback = "True") :
	""" Sets a marinara timer on the channel in which this message was sent.
		repeat		: Indicates whether the timer should start over when it's done with the list
			of periods or simply stop. (Default: True)
		countback 	: Indicates whether the timer should send a TTS message or a normal one whenever
			the period finishes or changes. (Default: False)"""

	if timerFormat == "help" :
		helpStr = "**Example:**\n\t" + COMMAND_PREFIX + "setup " + DEFAULT_TIMER
		await bot.say((helpStr  + 
			"\n\t_This will give you a sequence of 32, 8, 32, 8, 32, 15_"))
		return

	if timerFormat == "default" :
		timerFormat = DEFAULT_TIMER

	channelId = lib.getChannelId(ctx)

	if channelId in bot.pomodoroTimer.keys() :
		result = -1
	else :
		try :
			loop = lib.toBoolean(repeat)
			countdown = lib.toBoolean(countback)

			bot.pomodoroTimer[channelId] = Timer.PomodoroTimer()
			bot.timeMessage[channelId] = None
			bot.listMessage[channelId] = None

			result, times = bot.pomodoroTimer[channelId].setup(timerFormat,
				loop, countdown)
		except cmdErr.BadArgument :
			result = -4

	if result == 0 and times != None :
		settings = ("Correctly set up timer config: " + times + "." +
			"\nLooping is **" + ("ON" if repeat else "OFF") + "**" +
			"\nCountdown is **" + ("ON" if countdown else "OFF") + "**")

		setupPrint = settings
		setupSay = None
		await bot.say(settings, delete_after = bot.response_lifespan * 2)

	elif result == -1 : # len(pTimes) > 0
		setupPrint = ("Rejecting setup command, " +
			"there is a period set already established.")
		setupSay = ("I'm already set and ready to go, please use the reset " +
			"command if you want to change the timer configuration.")
		
	elif result == -2 : # state == RUNNING or PAUSED
		setupPrint = ("Someone tried to modify the timer " +
			"while it was already running.")
		setupSay = "Please stop the timer completely before modifying it."

	elif result == -3 : # format error
		setupPrint = ("Could not set the periods correctly, " +
			"command 'setup' failed.")
		setupSay = "I did not understand what you wanted, please try again!"
	
	elif result == -4 : # repeat or countback (arguments) are not valid booleans
		setupPrint = ("Could not parse boolean arguments '" + repeat +
			"' and '" + countback + "'")
		setupSay = "Invalid arguments received, please try again."

	print("<" + channelId + "> " + setupPrint)
	if setupSay != None :
		await bot.say(setupSay, delete_after = bot.response_lifespan)

@bot.command(pass_context = True)
async def starttimer(ctx, periodIdx = 1) :
	""" Starts the timer with the recorded setup. 
		If none present, or if it's already running,
		it simply gives an error message."""
	
	channelId = lib.getChannelId(ctx)

	try :
		if bot.pomodoroTimer[channelId].isSet() :
			if bot.pomodoroTimer[channelId].start() :
				starttimer = None

				if not\
					(1 < periodIdx < len(bot.pomodoroTimer[channelId].pTimes)) :
					periodIdx = 1

				await bot._run_timer(channelId, periodIdx - 1)
			else : 
				starttimer = (lib.getAuthorName(ctx) + 
					" tried to start a timer that was already running.")
				await bot.say("This channel's timer is already running",
					delete_after = bot.response_lifespan)
		else :
			starttimer = (lib.getAuthorName(ctx) +
				" tried to start a timer without set periods.")
			await bot.say(("Timer is not set up. Please use the command " +
				"'setup'. Use 'halp' or 'setup help' for further explanation"),
				delete_after = bot.response_lifespan)

	except KeyError :
		starttimer = (lib.getAuthorName(ctx) 
			+ " tried to start an inexistant timer.")
		await bot.say("No timer found for this channel.",
			delete_after = bot.response_lifespan)

	if starttimer != None :
		print("<" + channelId + "> " + starttimer)


@bot.command(pass_context = True)
async def pause(ctx) :
	""" Pauses the timer, if it's running. Keeps all settings and current 
		period / time. """

	channelId = lib.getChannelId(ctx)

	try :
		if bot.pomodoroTimer[channelId].pause() :
			pause = "Timer will be paused soon."
			await bot.say(pause, delete_after = bot.timer_step)

		else :
			pause = "Could not pause timer, stopped or already running."
			await bot.say("Bruh, I cannot stop something that isn't moving.",
				delete_after = bot.response_lifespan)

	except KeyError :
		pause = lib.getAuthorName(ctx) + " tried to pause an inexistant timer."
		await bot.say("No timer found for this channel.",
			delete_after = bot.response_lifespan)

	print("<" + channelId + "> " + pause)

@bot.command(pass_context = True)
async def stop(ctx) :
	""" Stops the timer, if it's running.
		Resets the current period and time, but keeps the setup. """

	channelId = lib.getChannelId(ctx)

	try :
		if bot.pomodoroTimer[channelId].stop() :
			stop = "Timer will stop soon."
			await bot.say(stop, delete_after = bot.timer_step)

		else :
			stop = "Timer has stopped." 
			await bot.say(stop)

			await bot._delete_messages(channelId)

	except KeyError :
		stop = lib.getAuthorName(ctx) + " tried to stop an inexistant timer."
		await bot.say("No timer found for this channel.",
			delete_after = bot.response_lifespan)

	print("<" + channelId + "> " + stop)

@bot.command(pass_context = True)
async def resume(ctx) :
	""" Resumes a paused timer. """

	channelId = lib.getChannelId(ctx)

	try :
		if bot.pomodoroTimer[channelId].resume() :
			resume = None
			await bot._run_timer(channelId)
		else :
			resume = "Unable to resume timer, stopped or already running."

			if lib.getAuthorId(ctx) == "244720666018840576" :
				await bot.say(("No grumbles for you, " + 
						lib.getAuthorName(ctx, True) + "!"),
					delete_after = bot.response_lifespan)
			else :
				await bot.say(("**grumble grumble.** The timer is stopped or" + 
						" already running, I can't resume that!"),
					delete_after = bot.response_lifespan)

	except KeyError :
		resume = (lib.getAuthorName(ctx) +
			" tried to resume an inexistant timer.")
		await bot.say("No timer found for this channel.",
			delete_after = bot.response_lifespan)
	
	if resume != None :
		print("<" + channelId + "> " + resume)


@bot.command(pass_context = True)
async def goto(ctx, nPeriod : int) :
	""" Skips to the (n-1)th period. """

	channelId = lib.getChannelId(ctx)

	try :
		label = bot.pomodoroTimer[channelId].goto(nPeriod)

		if label != None :
			goto = "Moved to period number " + str(nPeriod) + " (" + label + ")"
			await bot.say(goto)
		else :
			goto = "Invalid period number entered when trying goto command."
			await bot.say("Invalid period number.")

	except KeyError :
		goto = (lib.getAuthorName(ctx) + 
			" tried changing periods in an inexistant timer.")
		await bot.say("No timer found for this channel.",
			delete_after = bot.response_lifespan)
	
	print("<" + channelId + "> " + goto)

@bot.command(pass_context = True)
async def reset(ctx) :
	""" Resets the timer setup. """

	channelId = lib.getChannelId(ctx)

	try :
		if bot.pomodoroTimer[channelId].isStopped() :
			del bot.pomodoroTimer[channelId]

			del bot.timeMessage[channelId]
			del bot.listMessage[channelId]

			reset = lib.getAuthorName(ctx) + " reset the timer."
			await bot.say("Succesfully reset session configuration.",
				delete_after = bot.response_lifespan)
		else :
			reset = (lib.getAuthorName(ctx) + 
				" tried resetting a timer that was running or paused.")
			await bot.say("Cannot do that while the timer is not stopped.",
				delete_after = bot.response_lifespan)

	except KeyError :
		reset = (lib.getAuthorName(ctx) + 
			" tried resetting an inexistant timer setup.")
		await bot.say("No timer found for this channel.", bot.response_lifespan)

	print("<" + channelId + "> " + reset)

@bot.command(pass_context = True)
async def superreset(ctx) :
	""" Ignores all conditions and resets the channel's timer.	"""

	if lib.getAuthorId(ctx) != ADMIN_ID :
		superreset = (lib.getAuthorName(ctx) + 
			"attempted to superreset the bot and failed (No permission).")
		await bot.say("You're not my real dad!")

	else :
		channelId = lib.getChannelId(ctx)

		try :
			if bot.pomodoroTimer[channelId].state == Timer.State.RUNNING :
				bot.timersRunning -= 1
				await bot._update_status()

			await bot._delete_messages(channelId)

			del bot.timeMessage[channelId]
			del bot.listMessage[channelId]

			del bot.pomodoroTimer[channelId]

			superreset = "Successfully forced a reset on this channel's timer."
			await bot.say("Timer has been force-reset",
				delete_after = bot.response_lifespan)
		except KeyError :
			superreset = (lib.getAuthorName(ctx) +
				" tried to force-reset the timer, but no timer was found.")
			await bot.say("No timer found for this channel.",
				delete_after = bot.response_lifespan)

	print("<" + channelId + "> " + superreset)

@bot.command(pass_context = True)
async def time(ctx) :
	""" Gives the user the current period and time of the timer. """

	channelId = lib.getChannelId(ctx)

	try :
		time = bot.pomodoroTimer[channelId].time(True)

		await bot.say(time, delete_after = bot.response_lifespan * 2)

	except KeyError :
		time = (lib.getAuthorName(ctx) + 
			" tried to get the current time of an inexistant timer.")
		await bot.say("No timer found for this channel.",
			delete_after = bot.response_lifespan)

	print("<" + channelId + "> " + time)

@bot.command(pass_context = True)
async def status(ctx) :
	""" Tells the user whether the timer is stopped, running or paused. """

	channelId = lib.getChannelId(ctx)

	try :
		status = bot.pomodoroTimer[channelId].status()
		await bot.say(status, delete_after = bot.response_lifespan * 2)

	except KeyError :
		status = (lib.getAuthorName(ctx) +
			" tried to check the status of an inexistant timer.")
		await bot.say("No timer found for this channel.",
			delete_after = bot.response_lifespan)
	
	print("<" + channelId + "> " + status)

@bot.command()
async def tts(toggle : str) :
	""" Sets the tts option on or off. """

	try :
		bot.tts = lib.toBoolean(toggle)
		ttsStatus = ("on." if bot.tts else "off.")

		print("<------Global------> TTS now " + ttsStatus)
		await bot.say("Text-to-speech now " + ttsStatus, tts = bot.tts,
			delete_after = bot.response_lifespan)

	except cmdErr.BadArgument :
		print("<------Global------> TTS command failed, bad argument.")
		await bot.say("I could not understand if you wanted to turn TTS" + 
			" on or off, sorry.")

@bot.command(pass_context = True)
async def halp(ctx) :
	""" Tells the user how to use the bot. """

	await bot.send_message(ctx.message.author, content = """
**!setup _<format> [loop tts]_**
\tSets the marinara timer up.
\t\tformat    : The periods format. Each period is a set of <name>:<time>, \
where time is in minutes,
\t\t\tand periods are separated by commas. 
\t\trepeat    : Indicates whether the timer should start over when it's done
\t\t\twith the list of periods or simply stop. ('True' or 'False', \
defaults to True)
\t\ttts       : Indicates whether the timer should say period changes \
out loud.
\t\t\t('True' or 'False', defaults to False)
**!starttimer**
\tStarts the timer (must be set up previously).
**!pause**
\tPauses the timer, keeping the current period and time intact.
**!stop**
\tStops the timer, resetting it to the first period and the time to 0
**!resume**
\tRestarts a paused timer.
**!goto _<period-index>_**
\tSkips to the indicated period (Resets the time to 0 within the period).
**!tts _<on|off>_**
\tTurns text-to-speech on or off.
**!time**
\tIf the timer is running, it will show how much time of the current period \
has passed.
**!status**
\tShows whether the timer is stopped, running or paused.
**!halp**
\tShows this message.""")

@bot.command(pass_context = True)
async def shutdown(ctx) :
	""" Exits the program. """

	if lib.getAuthorId(ctx) == ADMIN_ID or authorHasRole(ctx, BOT_ROLE_ID):
		print("Shutting down...")
		await bot.say("Hope I did well, bye!")

		# debug
		for role in ctx.message.author.roles :
			try :
				print (role.id + ":" + role.name)
			except UnicodeEncodeError :
				pass

		for channelId, pinnedMessage in bot.timeMessage.items() :
			try :
				if bot.pomodoroTimer[channelId].state != Timer.State.STOPPED :
					bot.pomodoroTimer[channelId].stop()
					if lib.getChannelId(ctx) != channelId :
						await bot.send_msg(channelId,
							"I'm sorry, I have to go. See you later!")
				if pinnedMessage != None :
					await bot._delete_messages(channelId)
			except (KeyError, dErr.NotFound) as fail :
				pass

		#await asyncio.sleep(bot.timer_step * 2)

		await bot.logout()
	else :
		print(lib.getAuthorName(ctx) +
			"attempted to stop the bot and failed (No permission to shut down)")

# Helper functions

if __name__ == '__main__':


	if len(sys.argv) < 2 :
		print("Not enough arguments received!\nUsage: " + sys.argv[0] +
			" <token>")
		exit(-1)

	elif len(sys.argv) == 2 :
		TOKEN = sys.argv[1]

	x = input()
	# config

	config = config.Config("bot.cfg")
	
	command_prefix = config.get_str('command_prefix')
	if command_prefix == None :
		print("Could not find a valid command prefix in the config," +
			" using default")
		command_prefix = '!'

	bot.command_prefix = command_prefix
	ADMIN_ID = config.get_str('admin_id')
	STARTUP_MSG = config.get_str('startup_msg')
	DEFAULT_TIMER = config.get_str('default_timer')
	BOT_ROLE_ID = config.get_str('bot_friend_role_id')

	# Logging stuff

	logging.basicConfig(level = logging.INFO)

	logger = logging.getLogger()

	logFmt = logging.Formatter(fmt = '[%(asctime)s] [%(levelname)s] %(message)s',
		datefmt = '%m/%d | %H:%M:%S')

	fileHandler = logging.FileHandler(filename = 'pomodorobot.log',
		encoding = 'utf8', mode = 'w')
	termHandler = logging.StreamHandler(sys.stderr)
	fileHandler.setFormatter(logFmt)
	termHandler.setFormatter(logFmt)
	logger.addHandler(fileHandler)
	logger.addHandler(termHandler)

	# config

	# Bot init

	bot.response_lifespan = config.get_int('response_lifespan')
	bot.timer_step = config.get_int('timer_step')
	bot.run(TOKEN)
