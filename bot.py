import logging
from datetime import datetime

import asyncio

import discord
from discord import errors as dErr 
from discord.enums import Status

import pomodoroLib as lib
import timer as Timer


class PomodoroBot(discord.ext.commands.Bot) :
	""" An extension of the Bot class, that contains the necessary attributes 
		and methods to run a Marinara Timer. """
	
	# The timers currently running. There can be one per channel. 
	# (Indexed by the channel's ID)
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

	timer_step = 1
	response_lifespan = 15

	def __init__(self, command_prefix, formatter = None, description = None,
		pm_help = False, response_lifespan = 15, timer_step = 2,  **options) :
		super().__init__(command_prefix, formatter, 
			description, pm_help, **options)

		self.timer_step = timer_step
		self.response_lifespan = response_lifespan

	@asyncio.coroutine
	async def send_msg(self, channelId : str, message : str, tts = False) :
		await self.send_message(lib.asObject(channelId), message, tts = tts)

	@asyncio.coroutine
	async def _update_status(self) :
		if self.timersRunning == 0 :
			await self.change_presence(game = None, status = Status.idle)
		else :
			game = discord.Game()
			game.name = (" on " + 
				lib.pluralize(self.timersRunning, "channel", append = "s"))

			await self.change_presence(game = game,
				status = Status.online)

	@asyncio.coroutine
	async def _generate_messages(self, channelId: str) :
		""" Deletes the messages for the given channel. """

		self.timeMessage[channelId] = await self.send_message(
			lib.asObject(channelId), 
			"Generating status...")

		self.listMessage[channelId] = await self.send_message(
			lib.asObject(channelId), 
			self.pomodoroTimer[channelId].periodList())

		# The last message pinned ends up in the top
		await self.pin_message(self.listMessage[channelId])
		await self.pin_message(self.timeMessage[channelId])

	
	@asyncio.coroutine
	async def _delete_messages(self, channelId : str) :
		""" Deletes the time and periods list messages 
			in the channel with the ID given
			
			Args:
				channelId : The ID of the channel in which the messages
					should be deleted.
		"""

		try :
			if channelId in self.timeMessage.keys() and \
					self.timeMessage[channelId] != None :
				await self.delete_message(self.timeMessage[channelId])

			if channelId in self.listMessage.keys() and \
					self.listMessage[channelId] != None :
				await self.delete_message(self.listMessage[channelId])

		except dErr.NotFound :
			pass


	@asyncio.coroutine
	async def _run_timer(self, channelId, startIdx = 0) :
		""" Makes a timer run. """

		timer = self.pomodoroTimer[channelId]

		await self.wait_until_ready()

		self.timersRunning += 1
		await self._update_status()

		while not self.is_closed :
			iterStart = datetime.now()
			iterStartMicro = iterStart.second * 1000000 + iterStart.microsecond

			if timer.state == Timer.State.RUNNING and\
					timer.currentTime >= timer.pTimes[timer.currentPeriod] * 60 :
				toSay = "@here | '" + timer.pNames[timer.currentPeriod]
				toSay += "' period over!"

				timer.currentTime = 0
				timer.currentPeriod += 1

				if timer.currentPeriod >= len(timer.pTimes) and\
						not timer.onRepeat :

					timer.action = Timer.Action.STOP
					toSay += "\nI have ran out of periods, and looping is off."
					print("<" + channelId + "> " + toSay)
					await self.send_msg(channelId, toSay, tts = self.tts)

					self.timersRunning -= 1
					await self._update_status()
					return
				
				timer.currentPeriod %= len(timer.pTimes)

				if timer.action == Timer.Action.NONE :
					toSay += (" '" + timer.pNames[timer.currentPeriod] +
					 	"' period now starting (" +
					 	lib.pluralize(timer.pTimes[timer.currentPeriod],
					 		"minute", append = "s")
					 	+ ").")
					
				print("<" + channelId + "> " + toSay)
				await self.send_msg(channelId, toSay, tts = self.tts)

				await self.edit_message(self.listMessage[channelId],
					timer.periodList())

			if timer.action == Timer.Action.STOP :
				timer.action = Timer.Action.NONE
				
				timer.currentPeriod = -1
				timer.currentTime = 0
				timer.state = Timer.State.STOPPED

				print("<" + channelId + "> Timer has stopped.")
				await self.send_msg(channelId, "Timer has stopped.")

				await self._delete_messages(channelId)

				self.timeMessage[channelId] = None
				self.listMessage[channelId] = None

			elif timer.action == Timer.Action.PAUSE :
				timer.action = Timer.Action.NONE
				timer.state = Timer.State.PAUSED

				print("<" + channelId + "> Timer has paused.")
				await self.send_msg(channelId,"Timer has paused.")


			elif timer.action == Timer.Action.RUN :
				timer.action = Timer.Action.NONE

				if timer.state == Timer.State.STOPPED :
					timer.currentPeriod = startIdx
					statusAlert = "Starting"
				else :
					statusAlert = "Resuming"

				if startIdx != 0 :
					statusAlert += " (from period n." + str(startIdx + 1) + ")"

				print("<" + channelId + "> " + statusAlert )
				await self.send_msg(channelId, statusAlert)

				if self.timeMessage[channelId] == None :
					try :
						await self._generate_messages(channelId)
					except discord.Forbidden:
						print("<" + channelId + "> No permission to pin.")
						kitty = ("I tried to pin a message and failed." +
							" Can I haz permission to pin messages?" +
							" https://goo.gl/tYYD7s")
						await self.send_msg(channelId, kitty)

				timer.state = Timer.State.RUNNING
			
			try :
				if self.timeMessage[channelId] != None :
					await self.edit_message(self.timeMessage[channelId],
						timer.time())
			except dErr.NotFound :
				pass

			if timer.state == Timer.State.RUNNING :
				iterEnd = datetime.now()
				iterEndMicro = iterEnd.second * 1000000 + iterEnd.microsecond

				iterEndMicro -= iterStartMicro
				iterEndMicro %= 1000000.0
				sleepTime = ((self.timer_step * 1000000.0) - iterEndMicro)
				sleepTime /= 1000000.0

				timer.currentTime += self.timer_step
				await asyncio.sleep(sleepTime)
			else :
				self.timersRunning -= 1
				await self._update_status()
				return
