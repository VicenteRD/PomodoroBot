import sys
from enum import Enum

import discord
from discord.ext import commands

import asyncio
import re


ADMIN_ID = "87387330037448704"

TOKEN = ""
COMMAND_PREFIX = '!'
DESCRIPTION = '''A marinara timer bot that can be configured to your needs.'''

RESPONSE_LIFESPAN = 15

TIMER_STEP = 1 # in seconds

class TState(Enum):
	""" Represents the states in which the timer can be. """
	STOPPED = -1
	RUNNING = 1
	PAUSED = 2

class TAction(Enum) :
	""" Represents the actions that can affect the timer. """
	NONE = 0
	PAUSE = 1
	STOP = 2

class PomodoroBot(commands.Bot) :
	""" An extension of the Bot class, that contains the necessary attributes and methods to run a Marinara Timer. """
	
	# The times for the different periods the timer has been setup with
	pTimes = []
	# The labels or names for each of the set periods
	pNames = []

	# The period the timer is currently at.
	currentPeriod = -1
	# The current time within the period. 
	currentTime = 0
	
	# Whether the period list should loop or not
	onRepeat = True
	# Whether the bot should send TTS messages on a change of periods
	tts = False

	# The current timer's status
	timerState = TState.STOPPED
	# The action the timer should react to on the next iteration of the loop
	nextAction = TAction.NONE

	# The message that gets pinned, containing the current timer and its status 
	statusMessage = None

	def __init__(self, command_prefix, formatter=None, description=None, pm_help=False, **options):
		super().__init__(command_prefix, formatter, description, pm_help, **options)


	def generateTimeStatus(self, fullInfo = False) :
		""" Generates a string containing the timer's current period and time. 
			If fullInfo is True, then it also shows the complete list of periods. """

		if bot.timerState == TState.STOPPED :
			return "Currently not running."
		
		ret = "**On " + bot.pNames[bot.currentPeriod] + " period** (Duration: " + str(bot.pTimes[bot.currentPeriod]) + (" minute" if bot.pTimes[bot.currentPeriod] == 1 else " minutes") + ")\n\t"
		
		m, s = divmod((bot.pTimes[bot.currentPeriod] * 60) - bot.currentTime, 60)
		h, m = divmod(m, 60)

		ret += "%02d:%02d:%02d" % (h, m, s)
		del h,m,s

		if bot.timerState == TState.PAUSED :
			ret += "\t**(PAUSED)**"

		if fullInfo :
			ret += "\n\n**Period list (Loop is " + ("ON" if bot.onRepeat else "OFF")  + "):**"
			for i in range(0, len(bot.pTimes)) :
				ret += "\n" + bot.pNames[i] + ": " + str(bot.pTimes[i]) + (" minute" if bot.pTimes[i] == 1 else " minutes")
				if (i == bot.currentPeriod) :
					ret += "\t-> _You are here!_"
		return ret

	@asyncio.coroutine
	async def startTimer(self) :
		""" Starts the timer with the recorded setup. If none present, or if it's already running, it simply gives an error message."""

		if len(bot.pTimes) <= 0 :
			print("No sections registered when attempting to start the timer.")
			await bot.say("Timer is not set up. Please use the command 'setup'. Use 'setup help' for further explanation" )
			return

		if bot.timerState == TState.RUNNING :
			print("Someone is trying to start the bot when it was already running.")
			await bot.say("Timer is already running...")
			return

		await bot.wait_until_ready()

		while not bot.is_closed :

			if bot.timerState == TState.RUNNING :
					bot.currentTime += 1

					if bot.currentTime >= bot.pTimes[bot.currentPeriod] * 60 :
						toSay = "@here | '" + bot.pNames[bot.currentPeriod] + "' period over!"

						bot.currentTime = 0
						bot.currentPeriod += 1

						if bot.currentPeriod >= len(bot.pTimes) :
							if bot.onRepeat :
								if len(bot.pTimes) == 1:
									bot.currentPeriod = 0
								else:
									bot.currentPeriod = bot.currentPeriod % len(bot.pTimes)
							else :
								bot.nextAction = TAction.STOP
								toSay += "\n...I have ran out of periods, and looping is off. Time to procrastinate?"
								print(toSay)
								await bot.say(toSay)
								return

						if bot.nextAction == TAction.NONE :
							toSay += " '" + bot.pNames[bot.currentPeriod] + "' period now starting." #TODO also print, all prints to log
						
						print(toSay)
						await bot.say(toSay, tts = bot.tts)

			if bot.nextAction == TAction.STOP :
				bot.nextAction = TAction.NONE
				
				bot.currentPeriod = -1
				bot.currentTime = 0
				bot.timerState = TState.STOPPED

				print("Timer has stopped.")
				await bot.say("Timer has stopped.")

				await bot.unpin_message(bot.statusMessage)
				await bot.delete_message(bot.statusMessage)
				bot.statusMessage = None
				return

			elif bot.nextAction == TAction.PAUSE :
				bot.nextAction = TAction.NONE
				bot.timerState = TState.PAUSED

				print("Timer has paused.")
				await bot.say("Timer has paused.")


			elif not bot.timerState == TState.RUNNING :
				if bot.timerState == TState.STOPPED :
					bot.currentPeriod = 0

				statusAlert = ("Starting!" if bot.timerState == TState.STOPPED else "Restarting!")
				print(statusAlert)
				await bot.say(statusAlert)

				if bot.statusMessage == None :
					bot.statusMessage = await bot.say("Generating status...")
					try :
						await bot.pin_message(bot.statusMessage)
					except discord.Forbidden:
						print("No permission to pin.")
						await bot.say("I tried to pin a message and failed. Can I haz permission to pin messages? https://goo.gl/tYYD7s")

				bot.timerState = TState.RUNNING
				
			await bot.edit_message(bot.statusMessage, bot.generateTimeStatus(True))

			if bot.timerState == TState.RUNNING :
				await asyncio.sleep(TIMER_STEP)
			else :
				return

bot = PomodoroBot(command_prefix = COMMAND_PREFIX, description = DESCRIPTION, pm_help = True)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.command()
async def setup(timerFormat : str, repeat = True, tts = False):
	""" Sets the marinara timer.
		repeat	: Indicates whether the timer should start over when it's done with the list of periods or simply stop. (Default: True)
		tts 	: Indicates whether the timer should send a TTS message or a normal one whenever the period finishes or changes. (Default: False)"""

	if bot.timerState == TState.RUNNING or bot.timerState == TState.PAUSED :
		print("Someone tried to modify the timer while it was already running!")
		await bot.say("Please stop the timer completely before modifying it.")
		return

	if len(bot.pTimes) > 0 :
		print("Rejecting setup command, there is a period set already established")
		await bot.say("I'm already set and ready to go, please use the reset command if you want to change the timer configuration.")
		return

	if timerFormat == "help" :
		await bot.say("**Example:**\n\t" + COMMAND_PREFIX + "setup (2xStudy:32,Break:8),Study:32,Long_Break:15\n\t_This will give you a sequence of 32, 8, 32, 8, 32, 15_")
		return

	if timerFormat == "default" :
		timerFormat = "(2xStudy:32,Break:8),Study:32,Long_Break:15"

	bot.onRepeat = repeat

	rawSections = re.sub(r",(?=[^()]*\))", '.', timerFormat).split(',')

	loop = True
	if ':' in timerFormat:
		if ',' in timerFormat:
			fmtErr = False
		else :
			try :
				attempt = timerFormat.split(':')
				bot.pNames.append(attempt[0])
				bot.pTimes.append(int(attempt[1]))
				fmtErr = False
				loop = False
			except ValueError :
				fmtErr = True
	else :
		fmtErr = True

	if not fmtErr and loop:
		for section in rawSections :
			if section.startswith('(') and section.endswith(')') :

				section = section.replace('(', '').replace(')', '')
				splits = section.split('x')

				subSections = []

				for s in splits[1].strip().split('.') :
					subSections.append(s.split(':'))
					if len(subSections[len(subSections) - 1]) != 2 :
						fmtErr = True
						break
				if fmtErr :
					break

				for i in range(0, int(splits[0]) * len(subSections)) :
					idx = i % len(subSections)
					print("Adding period '" + subSections[idx][0] + "' of length " + str(subSections[idx][1]) + " at position " + str(len(bot.pTimes)))

					bot.pNames.append(subSections[i % len(subSections)][0].replace('_', ' '))
					bot.pTimes.append(int(subSections[i % len(subSections)][1]))
			else :
				splitsB = section.split(':')
				if len(splitsB) != 2 :
					fmtErr = True
					break
				bot.pNames.append(splitsB[0].replace('_', ' '))
				bot.pTimes.append(int(splitsB[1]))

	if not fmtErr :

		for i in range(0, len(bot.pTimes)) :
			print("Period n." + str(i) + " (" + bot.pNames[i] + "):\t" + str(bot.pTimes[i]) + (" minute" if bot.pTimes == 1 else " minutes"))
			if i > 0 :
				concat += ", " + str(bot.pTimes[i])
			else :
				concat = str(bot.pTimes[0])

		await bot.say("Correctly set up timer config: " + concat, delete_after = 15)
	else :
		print("Could not set the periods correctly, command 'setup' failed")
		await bot.say("I did not understand what you wanted, please try again!") 


@bot.command()
async def starttimer() :
	""" Starts the timer with the recorded setup. If none present, or if it's already running, it simply gives an error message."""
	await bot.startTimer()


@bot.command()
async def pause() :
	""" Pauses the timer, if it's running. Keeps all settings and current period / time. """

	if not bot.timerState == TState.RUNNING :
		await bot.say("Bruh, I cannot stop something that isn't moving.")
		return

	bot.nextAction = TAction.PAUSE

	alert = "Timer will be paused soon."
	print(alert)
	await bot.say(alert, delete_after = 1)

@bot.command()
async def stop() :
	""" Stops the timer, if it's running, resetting the current period and time, but keeping the setup. """

	if bot.timerState == TState.RUNNING :
		bot.nextAction = TAction.STOP

		alert = "Timer will stop soon."
		print(alert)
		await bot.say(alert, delete_after = 1)
	elif bot.timerState == TState.PAUSED or bot.nextAction == TAction.PAUSE :
		bot.nextAction = TAction.NONE
				
		bot.currentPeriod = -1
		bot.currentTime = 0
		bot.timerState = TState.STOPPED

		print("Timer has stopped.")
		await bot.say("Timer has stopped.")

		await bot.unpin_message(bot.statusMessage)
		await bot.delete_message(bot.statusMessage)

@bot.command(pass_context = True)
async def resume(ctx) :
	""" Resumes a paused timer. """

	if not bot.timerState == TState.PAUSED:
		if ctx.message.author.id == "244720666018840576" :
			await bot.say("No grumbles for you, " + (ctx.message.author.nick if ctx.message.author.nick != None else ctx.message.author.name ) + "!")
		else :
			await bot.say("**grumble grumble.** The timer is " + ("stopped, use 'starttimer' instead..." if bot.timerState == TState.STOPPED else "already running..."))
	else :
		await bot.startTimer()

@bot.command()
async def goto(nPeriod : int) :
	""" Skips to the (n-1)th period. """

	if nPeriod < 1 or nPeriod > len(bot.pTimes) :
		print("Invalid period number entered when trying goto command")
		await bot.say("Invalid period number.")
	else :
		bot.currentTime = 0
		bot.currentPeriod = nPeriod - 1

		gotoSuccess = "Moved to period number " + str(nPeriod) + " (" + bot.pNames[bot.currentPeriod] + ")"
		print(gotoSuccess)
		await bot.say(gotoSuccess)

@bot.command()
async def reset() :
	""" Resets the timer setup. """

	if not bot.timerState == TState.STOPPED :
		print("Someone tried to reset the timer configuration while running or paused, denying")
		await bot.say("Cannot do that while the timer is " + ("running" if bot.timerState == TState.RUNNING else "paused") + ". Please stop it first") # TODO
	else :
		bot.pNames = []
		bot.pTimes = []

		bot.currentPeriod = -1
		bot.currentTime = 0

		await bot.say("Succesfully reset session configuration.")

@bot.command()
async def tts(toggle : str) :
	""" Sets the tts option on or off. """

	toggle = toggle.lower()

	if toggle == "on" or toggle == "true" or toggle == "yes" or toggle == "y" :
		bot.tts = True
		print("TTS now on.")
		await bot.say("Text-to-speech now on.", tts = True, delete_after = 8)
	else :
		bot.tts = False 
		print("TTS now off.")
		await bot.say("Text-to-speech now off.", delete_after = 8)


@bot.command()
async def time() :
	""" Gives the user the current period and time of the timer. """

	tmpString = bot.generateTimeStatus()
	
	print(tmpString)
	await bot.say(tmpString)

@bot.command()
async def status() :
	""" Tells the user whether the timer is stopped, running or paused. """

	statusReport = "Currently " + ("running" if bot.timerState == TState.RUNNING else ("paused" if bot.timerState == TState.PAUSED else "stopped"))

	if len(bot.pTimes) != len (bot.pNames) :
		statusReport += ".\nFound a setup error! Resetting..."
		reset()
	elif len(bot.pTimes) == 0 :
		statusReport += " and not properly set up."
	else :
		statusReport += "."

	if not bot.nextAction == TAction.NONE :
		statusReport += " Will soon " + ("pause" if bot.nextAction == TAction.PAUSE else "stop") + "."

	print(statusReport)
	await bot.say(statusReport)

@bot.command(pass_context = True)
async def halp(ctx) :
	""" Tells the user how to use the bot. """

	helpStr ="""
**!setup _<format> [loop tts]_**
\tSets the marinara timer up.
\t\tformat    : The periods format. Each period is a set of <name>:<time>, where time is in minutes, and periods are separated by commas. 
\t\trepeat    : Indicates whether the timer should start over when it's done with the list of periods or simply stop. ('True' or 'False', defaults to True)
\t\ttts           : Indicates whether the timer should say period changes out loud. ('True' or 'False', defaults to False)
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
\tShows this message."""

	await bot.send_message(ctx.message.author, content = helpStr)

@bot.command(pass_context = True)
async def shutdown(ctx) :
	""" Exits the program. """

	caller = ctx.message.author
	print(caller.id)
	if caller.id == ADMIN_ID : # caller.roles
		print("Shutting down...")
		await bot.say("Hope I did well, bye!")
		
		if bot.statusMessage != None :
			await bot.unpin_message(bot.statusMessage)
			await bot.delete_message(bot.statusMessage)
		await bot.logout()
	else :
		print("No perms to shut down")

if __name__ == '__main__':

	if len(sys.argv) < 2 :
		print("Not enough arguments received!\nUsage: " + sys.argv[0] + " <token> [prefix] [admin_id]")
		exit(0)

	elif len(sys.argv) == 2 :
		TOKEN = sys.argv[1]

	elif len(sys.argv) == 3 and (len(sys.argv[2]) == 1 and not (sys.argv[2][0] > 'A' and sys.argv[2][0] < 'z')) :
		print("Command prefix set to " + sys.argv[2] +"\n")
		COMMAND_PREFIX = sys.argv[2]

	elif len(sys.argv) == 4 :
		print("Admin set to ID: " + sys.argv[3])
		ADMIN_ID = sys.argv[3]

	bot.command_prefix = COMMAND_PREFIX

	#TODO : logging

	bot.run(TOKEN)
