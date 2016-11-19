import sys
import logging
from datetime import datetime

import asyncio

import discord
from discord.enums import Status as discordStatus
from discord import errors as dErr 
from discord.ext import commands
from discord.ext.commands import errors as cmdErr

import pomodoroLib as lib
import timer as Timer

USAGE = sys.argv[0] + " <token> [prefix] [admin_id]"

TOKEN = ""
COMMAND_PREFIX = '!'
ADMIN_ID = "87387330037448704"

STARTUP_MSG = "Beep boop. I'm back online, ready to ~~take over the world~~ help your productivity!"

DESCRIPTION = '''A marinara timer bot that can be configured to your needs.'''

DEFAULT_TIMER = "(2xStudy:32,Break:8),Study:32,Long_Break:15"
RESPONSE_LIFESPAN = 15 # seconds
TIMER_STEP = 1 # seconds

logger = logging.getLogger()


class PomodoroBot(commands.Bot) :
	""" An extension of the Bot class, that contains the necessary attributes and methods 
		to run a Marinara Timer. """
	
	# The timers currently running. There can be one per channel. (Indexed by the channel's ID)
	pomodoroTimer = {}
	newTimer = {}
	# The messages that gets pinned, containing the current timer and its status 
	# (1 of each per channel, indexed by the channel's ID)
	timeMessage = {}
	listMessage= {}

	# Whether the bot should send TTS messages on a change of periods.
	tts = False

	# Whether the bot is ticking, thus making all timers run.
	ticking = False
	# The amount of timers running.
	timersRunning = 0

	def __init__(self, command_prefix, formatter=None, description=None, pm_help=False, **options) :
		super().__init__(command_prefix, formatter, description, pm_help, **options)

	@asyncio.coroutine
	async def updateStatus(self) :
		if bot.timersRunning == 0 :
			await bot.change_presence(game = None, status = discordStatus.idle)
		else :
			game = discord.Game()
			game.name = " on " + lib.pluralize(bot.timersRunning, "channel", append = "s")
			await bot.change_presence(game = game, status = discordStatus.online)

	@asyncio.coroutine
	async def deleteMessagesFor(self, channelId : str) :
		""" Deletes the time and periods list messages in the channel with the ID given
			channelId : The ID of the channel in which the messages should be deleted. """

		try :
			if channelId in bot.timeMessage.keys() and bot.timeMessage[channelId] != None :
				await bot.delete_message(bot.timeMessage[channelId])
			if channelId in bot.listMessage.keys() and bot.listMessage[channelId] != None :
				await bot.delete_message(bot.listMessage[channelId])
		except dErr.NotFound :
			pass


	@asyncio.coroutine
	async def runTimer(self, channelId, startIdx = 0) :
		""" Makes a timer run. """

		timer = bot.pomodoroTimer[channelId]

		await bot.wait_until_ready()

		bot.timersRunning += 1
		await bot.updateStatus()

		while not bot.is_closed :
			iterStart = datetime.now()
			iterStartMicro = iterStart.second * 1000000 + iterStart.microsecond

			if timer.state == Timer.State.RUNNING :
				timer.currentTime += 1

				if timer.currentTime >= timer.pTimes[timer.currentPeriod] * 60 :
					toSay = "@here | '" + timer.pNames[timer.currentPeriod] + "' period over!"

					timer.currentTime = 0
					timer.currentPeriod += 1

					if timer.currentPeriod >= len(timer.pTimes) :
						if timer.onRepeat :
							if len(timer.pTimes) == 1:
								timer.currentPeriod = 0
							else:
								timer.currentPeriod = timer.currentPeriod % len(timer.pTimes)
						else :
							timer.action = Timer.Action.STOP
							toSay += "\n...I have ran out of periods, and looping is off."
							print("<" + channelId + "> " + toSay)
							await bot.send_message(lib.asObject(channelId), toSay, tts = bot.tts)
	
							bot.timersRunning -= 1
							await bot.updateStatus()
							return

					if timer.action == Timer.Action.NONE :
						toSay += " '" + timer.pNames[timer.currentPeriod] + "' period now starting "
						toSay += "(" + lib.pluralize(timer.pTimes[timer.currentPeriod], "minute", append = "s") + ")."
						
					print("<" + channelId + "> " + toSay)
					await bot.send_message(lib.asObject(channelId), toSay, tts = bot.tts)

					await bot.edit_message(bot.listMessage[channelId], timer.periodList())

			if timer.action == Timer.Action.STOP :
				timer.action = Timer.Action.NONE
				
				timer.currentPeriod = -1
				timer.currentTime = 0
				timer.state = Timer.State.STOPPED

				print("<" + channelId + "> Timer has stopped.")
				await bot.send_message(lib.asObject(channelId), "Timer has stopped.")

				await bot.deleteMessagesFor(channelId)

				bot.timeMessage[channelId] = None
				bot.listMessage[channelId] = None

			elif timer.action == Timer.Action.PAUSE :
				timer.action = Timer.Action.NONE
				timer.state = Timer.State.PAUSED

				print("<" + channelId + "> Timer has paused.")
				await bot.send_message(lib.asObject(channelId),"Timer has paused.")


			elif timer.action == Timer.Action.RUN :
				timer.action = Timer.Action.NONE

				if timer.state == Timer.State.STOPPED :
					timer.currentPeriod = startIdx

				statusAlert = ("Starting..." if timer.state == Timer.State.STOPPED else "Resuming")
				if startIdx != 0 :
					statusAlert += "(from period n." + str(startIdx + 1) + ")"

				statusAlert += "..."
				print("<" + channelId + "> " + statusAlert )
				await bot.send_message(lib.asObject(channelId), statusAlert)

				if bot.timeMessage[channelId] == None :
					bot.timeMessage[channelId] = await bot.send_message(lib.asObject(channelId), "Generating status...")
					bot.listMessage[channelId] = await bot.send_message(lib.asObject(channelId), timer.periodList())
					try :
						# The last message pinned ends up in the top, so the time status goes 2nd
						await bot.pin_message(bot.listMessage[channelId])
						await bot.pin_message(bot.timeMessage[channelId])
					except discord.Forbidden:
						print("<" + channelId + "> No permission to pin.")
						kitty = "I tried to pin a message and failed. Can I haz permission to pin messages? https://goo.gl/tYYD7s" #shorten
						await bot.send_message(lib.asObject(channelId), kitty) 
				timer.state = Timer.State.RUNNING
			
			try :
				if bot.timeMessage[channelId] != None :
					await bot.edit_message(bot.timeMessage[channelId], timer.time())
			except dErr.NotFound :
				pass

			if timer.state == Timer.State.RUNNING :
				iterEnd = datetime.now()
				iterEndMicro = iterEnd.second * 1000000 + iterEnd.microsecond
				sleepTime = ((TIMER_STEP * 1000000.0)-((iterEndMicro - iterStartMicro) % 1000000.0))
				sleepTime /= 1000000.0

				await asyncio.sleep(sleepTime)
			else :
				bot.timersRunning -= 1
				await bot.updateStatus()
				return

				
bot = PomodoroBot(command_prefix = COMMAND_PREFIX, description = DESCRIPTION, pm_help = True)

@bot.event
async def on_ready():
	print('Logged in as')
	print(bot.user.name)
	print(bot.user.id)
	print('------')

	await bot.updateStatus()
	for server in bot.servers :
		await bot.send_message(server, STARTUP_MSG)

@bot.command(pass_context = True)
async def setup(ctx, timerFormat = "default", repeat = "True", countback = "True") :
	""" Sets a marinara timer on the channel in which this message was sent.
		repeat		: Indicates whether the timer should start over when it's done with the list
			of periods or simply stop. (Default: True)
		countback 	: Indicates whether the timer should send a TTS message or a normal one whenever
			the period finishes or changes. (Default: False)"""

	if timerFormat == "help" :
		helpStr = "**Example:**\n\t" + COMMAND_PREFIX + "setup" + DEFAULT_TIMER
		await bot.say(helpStr  + "\n\t_This will give you a sequence of 32, 8, 32, 8, 32, 15_")
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

			result, times = bot.pomodoroTimer[channelId].setup(timerFormat, loop, countdown)
		except cmdErr.BadArgument :
			result = -4

	if result == 0 and times != None :
		settings = "Correctly set up timer config: " + times + "."
		settings += "\nLooping is **" + ("ON" if repeat else "OFF") + "**"
		settings += "\nCountdown is **" + ("ON" if countdown else "OFF") + "**"

		setupPrint = settings
		await bot.say(settings, delete_after = RESPONSE_LIFESPAN * 2)

	elif result == -1 : # len(pTimes) > 0
		setupPrint = "Rejecting setup command, there is a period set already established."
		setupSay = "I'm already set and ready to go, please use the reset command "
		setupSay += "if you want to change the timer configuration."
		
	elif result == -2 : # state == RUNNING or PAUSED
		setupPrint = "Someone tried to modify the timer while it was already running."
		setupSay = "Please stop the timer completely before modifying it."

	elif result == -3 : # format error
		setupPrint = "Could not set the periods correctly, command 'setup' failed."
		setupSay = "I did not understand what you wanted, please try again!"
	
	elif result == -4 : # repeat or countback (given arguments) are not valid booleans
		setupPrint = "Could not parse boolean arguments '" + repeat + "' and '" + countback + "'"
		setupSay = "Invalid arguments received, please try again."

	await bot.say(setupSay, delete_after = RESPONSE_LIFESPAN)
	print("<" + channelId + "> " + setupPrint)

@bot.command(pass_context = True)
async def starttimer(ctx, periodIdx = 1) :
	""" Starts the timer with the recorded setup. 
		If none present, or if it's already running, it simply gives an error message."""
	
	channelId = lib.getChannelId(ctx)

	try :
		if bot.pomodoroTimer[channelId].isSet() :
			if bot.pomodoroTimer[channelId].start() :
				starttimer = None

				if periodIdx < 1 or periodIdx > len(bot.pomodoroTimer[channelId].pTimes) :
					periodIdx = 1

				await bot.runTimer(channelId, periodIdx - 1)
			else : 
				starttimer = getAuthorName(ctx) + " tried to start a timer that was already running."
				await bot.say("This channel's timer is already running", delete_after = RESPONSE_LIFESPAN)
		else :
			starttimer = getAuthorName(ctx) + " tried to start a timer without set periods."
			await bot.say("Timer is not set up. Please use the command 'setup'. Use 'halp' or 'setup help' for further explanation", delete_after = RESPONSE_LIFESPAN) #shorten

	except KeyError :
		starttimer = getAuthorName(ctx) + " tried to start an inexistant timer."
		await bot.say("No timer found for this channel.", delete_after = RESPONSE_LIFESPAN)

	if starttimer != None :
		print("<" + channelId + "> " + starttimer)


@bot.command(pass_context = True)
async def pause(ctx) :
	""" Pauses the timer, if it's running. Keeps all settings and current period / time. """

	channelId = lib.getChannelId(ctx)

	try :
		if bot.pomodoroTimer[channelId].pause() :
			pause = "Timer will be paused soon."
			await bot.say(pause, delete_after = 1)

		else :
			pause = "Could not pause timer, stopped or already running."
			await bot.say("Bruh, I cannot stop something that isn't moving.", delete_after = RESPONSE_LIFESPAN)

	except KeyError :
		pause = getAuthorName(ctx) + " tried to pause an inexistant timer."
		await bot.say("No timer found for this channel.", delete_after = RESPONSE_LIFESPAN)

	print("<" + channelId + "> " + pause)

@bot.command(pass_context = True)
async def stop(ctx) :
	""" Stops the timer, if it's running.
		Resets the current period and time, but keeps the setup. """

	channelId = lib.getChannelId(ctx)

	try :
		if bot.pomodoroTimer[channelId].stop() :
			stop = "Timer will stop soon."
			await bot.say(stop, delete_after = 1)

		else :
			stop = "Timer has stopped." 
			await bot.say(stop)

			await bot.deleteMessagesFor(channelId)

	except KeyError :
		stop = getAuthorName(ctx) + " tried to stop an inexistant timer."
		await bot.say("No timer found for this channel.", delete_after = RESPONSE_LIFESPAN)

	print("<" + channelId + "> " + stop)

@bot.command(pass_context = True)
async def resume(ctx) :
	""" Resumes a paused timer. """

	channelId = lib.getChannelId(ctx)

	try :
		if bot.pomodoroTimer[channelId].resume() :
			resume = None
			await bot.runTimer(channelId)
		else :
			resume = "Unable to resume timer, stopped or already running."

			if lib.getAuthorId(ctx) == "244720666018840576" :
				await bot.say("No grumbles for you, " + getAuthorName(ctx, True) + "!", delete_after=RESPONSE_LIFESPAN)
			else :
				await bot.say("**grumble grumble.** The timer is stopped or already running, I can't resume that!", delete_after = RESPONSE_LIFESPAN) #shorten

	except KeyError :
		resume = getAuthorName(ctx) + " tried to resume an inexistant timer."
		await bot.say("No timer found for this channel.", delete_after = RESPONSE_LIFESPAN)
	
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
		goto = getAuthorName(ctx) + " tried changing periods in an inexistant timer."
		await bot.say("No timer found for this channel.", delete_after = RESPONSE_LIFESPAN)
	
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

			reset = getAuthorName(ctx) + " reset the timer."
			await bot.say("Succesfully reset session configuration.", delete_after = RESPONSE_LIFESPAN)
		else :
			reset = getAuthorName(ctx) + " tried resetting a timer that was running or paused."
			await bot.say("Cannot do that while the timer is not stopped.", delete_after = RESPONSE_LIFESPAN)

	except KeyError :
		reset = getAuthorName(ctx) + " tried resetting an inexistant timer setup."
		await bot.say("No timer found for this channel.", delete_after = RESPONSE_LIFESPAN)

	print("<" + channelId + "> " + reset)

@bot.command(pass_context = True)
async def superreset(ctx) :
	""" Ignores all conditions and resets the channel's timer.	"""

	if lib.getAuthorId(ctx) != ADMIN_ID :
		print(getAuthorName(ctx) + "attempted to stop the bot and failed (No permission to shut down).")
		await bot.say("You're not my real dad!")
		return

	channelId = lib.getChannelId(ctx)

	try :
		if bot.pomodoroTimer[channelId].state == State.RUNNING :
			bot.timersRunning -= 1

		deleteMessagesFor(channelId)

		del bot.timeMessage[channelId]
		del bot.listMessage[channelId]

		del bot.pomodoroTimer[channelId]

		superreset = "Successfully forced a reset on this channel's timer."
		await bot.say("Timer has been force-reset", delete_after = RESPONSE_LIFESPAN)
	except KeyError :
		superreset = getAuthorName(ctx) + " tried to force-reset the timer, but no timer was found."
		await bot.say("No timer found for this channel.", delete_after = RESPONSE_LIFESPAN)

	print("<" + channelId + "> " + reset)

@bot.command(pass_context = True)
async def time(ctx) :
	""" Gives the user the current period and time of the timer. """

	channelId = lib.getChannelId(ctx)

	try :
		time = bot.pomodoroTimer[channelId].time(True)

		await bot.say(time, delete_after = RESPONSE_LIFESPAN * 2)

	except KeyError :
		time = getAuthorName(ctx) + " tried to get the current time of an inexistant timer."
		await bot.say("No timer found for this channel.", delete_after = RESPONSE_LIFESPAN)

	print("<" + channelId + "> " + time)

@bot.command(pass_context = True)
async def status(ctx) :
	""" Tells the user whether the timer is stopped, running or paused. """

	channelId = lib.getChannelId(ctx)

	try :
		status = bot.pomodoroTimer[channelId].status()
		await bot.say(status, delete_after = RESPONSE_LIFESPAN * 2)

	except KeyError :
		status = getAuthorName(ctx) + " tried to check the status of an inexistant timer."
		await bot.say("No timer found for this channel.", delete_after = RESPONSE_LIFESPAN)
	
	print("<" + channelId + "> " + status)

@bot.command()
async def tts(toggle : str) :
	""" Sets the tts option on or off. """

	try :
		bot.tts = lib.toBoolean(toggle)
		ttsStatus = ("on." if bot.tts else "off.")

		print("<------Global------> TTS now " + ttsStatus)
		await bot.say("Text-to-speech now " + ttsStatus, tts = bot.tts, delete_after = RESPONSE_LIFESPAN)

	except cmdErr.BadArgument :
		print("<------Global------> TTS command failed, bad argument.")
		await bot.say("I could not understand if you wanted to turn TTS on or off, sorry.")

@bot.command(pass_context = True)
async def halp(ctx) :
	""" Tells the user how to use the bot. """

	await bot.send_message(ctx.message.author, content = """
**!setup _<format> [loop tts]_**
\tSets the marinara timer up.
\t\tformat    : The periods format. Each period is a set of <name>:<time>, where time is in minutes,
\t\t\tand periods are separated by commas. 
\t\trepeat    : Indicates whether the timer should start over when it's done
\t\t\twith the list of periods or simply stop. ('True' or 'False', defaults to True)
\t\ttts           : Indicates whether the timer should say period changes out loud.
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
\tIf the timer is running, it will show how much time of the current period has passed.
**!status**
\tShows whether the timer is stopped, running or paused.
**!halp**
\tShows this message.""")

@bot.command(pass_context = True)
async def shutdown(ctx) :
	""" Exits the program. """

	if lib.getAuthorId(ctx) == ADMIN_ID :
		print("Shutting down...")
		await bot.say("Hope I did well, bye!")

		for channelId, pinnedMessage in bot.timeMessage.items() :
			try :
				if bot.pomodoroTimer[channelId].state != Timer.State.STOPPED :
					bot.pomodoroTimer[channelId].stop()
					if lib.getChannelId(ctx) != channelId :
						await bot.send_message(lib.asObject(channelId), "I'm sorry, I have to go. See you later!")

				if pinnedMessage != None :
					await bot.deleteMessagesFor(channelId)
			except (KeyError, dErr.NotFound) as wht :
				pass

		await bot.logout()
	else :
		print(getAuthorName(ctx) + "attempted to stop the bot and failed (No permission to shut down).")

# Helper functions

if __name__ == '__main__':

	if len(sys.argv) < 2 :
		print("Not enough arguments received!\nUsage: " + USAGE)
		exit(-1)

	elif len(sys.argv) == 2 :
		TOKEN = sys.argv[1]

	elif len(sys.argv) == 3 and (len(sys.argv[2]) == 1 and not sys.argv[2][0].isAlpha()) :
		print("Command prefix set to " + sys.argv[2] +"\n")
		COMMAND_PREFIX = sys.argv[2]

	elif len(sys.argv) == 4 :
		print("Admin set to ID: " + sys.argv[3])
		ADMIN_ID = sys.argv[3]

	bot.command_prefix = COMMAND_PREFIX

	# Logging stuff

	logging.basicConfig(level = logging.INFO)

	logger = logging.getLogger()

	logFmt = logging.Formatter(fmt = '[%(asctime)s] [%(levelname)s] %(message)s', datefmt = '%m/%d | %H:%M:%S')

	fileHandler = logging.FileHandler(filename = 'pomodorobot.log', encoding = 'utf8', mode = 'w')
	termHandler = logging.StreamHandler(sys.stderr)
	fileHandler.setFormatter(logFmt)
	termHandler.setFormatter(logFmt)
	logger.addHandler(fileHandler)
	logger.addHandler(termHandler)

	bot.run(TOKEN)
