from enum import Enum

import re

class State(Enum):
	""" Represents the states in which the timer can be. """
	STOPPED = -1
	RUNNING = 1
	PAUSED = 2

class Action(Enum) :
	""" Represents the actions that can affect the timer. """
	NONE = 0
	RUN = 1
	PAUSE = 2
	STOP = 3

class PomodoroTimer :
	""" A class representing a pomodoro timer."""


	# The times for the different periods the timer has been setup with
	pTimes = []
	# The labels or names for each of the set periods
	pNames = []

	# The period the timer is currently at.
	currentPeriod = -1
	# The current time within the period. 
	currentTime = 0

	# The current timer's status
	state = State.STOPPED
	# The action the timer should react to on the next iteration of the loop
	action = Action.NONE

	# Whether the period list should loop or not.
	onRepeat = True

	#idx = -1

	def __init__(self) :
		self.pTimes = []
		self.pNames = []

	def setup(self, pFormat, onRepeat) :
		""" Sets the marinara timer. """

		if len(self.pTimes) > 0 :
			return -1, None

		if self.state == State.RUNNING or self.state == State.PAUSED :
			return -2, None

		rawSections = re.sub(r",(?=[^()]*\))", '.', pFormat).split(',')

		loop = True
		if ':' in pFormat:
			if ',' in pFormat:
				fmtErr = False
			else :
				try :
					attempt = pFormat.split(':')
					self.pNames.append(attempt[0])
					self.pTimes.append(int(attempt[1]))
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

						self.pNames.append(subSections[i % len(subSections)][0].replace('_', ' '))
						self.pTimes.append(int(subSections[i % len(subSections)][1]))
				else :
					splitsB = section.split(':')
					if len(splitsB) != 2 :
						fmtErr = True
						break

					self.pNames.append(splitsB[0].replace('_', ' '))
					self.pTimes.append(int(splitsB[1]))

		if not fmtErr :
			for i in range(0, len(self.pTimes)) :
				if i > 0 :
					concat += ", " + str(self.pTimes[i])
				else :
					concat = str(self.pTimes[0])

			return 0, concat
		
		else :
			return -3, None

	def isStopped(self) :
		""" Checks whether the timer is stopped or not. """
		return self.state == State.STOPPED

	def getNextAction(self) :
		""" Returns the next action to be executed. """
		return self.action

	def start(self) :
		""" Starts the timer.
			Returns True if successful, False if it was already running """

		if self.state == State.RUNNING :
			return False

		self.action = Action.RUN
		return True

	def pause(self) :
		""" Pauses the timer, if it's running. Keeps all settings and current period / time. 
			Returns True if the timer was running and got paused, False otherwise (No need to pause then). """

		if self.state == State.RUNNING :
 			self.action = Action.PAUSE
 			return True
		return False

	def resume(self) :
 		""" Resumes the timer, if it was actually paused. Complains if not.
 			Returns True the timer was actually paused and got resumed successfully, False if it was running/stopped. """

 		if self.state == State.PAUSED :
 			self.start()
 			return True
 		return False

	def stop(self) :
		""" Attempts to stop the timer. It will only succeed if the planets align and Cthulhu is in a good mood. 
			Returns True if the timer was running and got stopped successfully,
			False if the timer was paused or about to be (Timer actually gets stopped, cancelling the pause state/action). """

		if self.state == State.RUNNING :
			self.action = Action.STOP
			return True

		elif self.state == State.PAUSED or self.action == Action.PAUSED :
			self.action = Action.NONE
			self.state = State.STOPPED

			self.currentTime = 0
			self.currentPeriod = -1

			return False

	def goto(self, idx : int) :
		""" Skips to the (n-1)th period. 
			If successful, returns the name of the period that it jumped to. If not, returns None"""

		if idx > 0 and idx <= len(self.pTimes) :
			self.currentPeriod = idx - 1
			self.currentTime = 0
			return self.pNames[self.currentPeriod]
		return None

	def isSet(self) :
		""" Tells whether the timer is already set up or not. Also does a precheck to see if the setup is actually well done. """

		if len(self.pTimes) != len(self.pNames) :
			# should go on a 'reset' function
			self.reset()

		return len(self.pTimes) > 0

	def status(self) :
		""" Tells the user whether the timer is stopped, running or paused. """

		status = "Currently " + ("running" if self.state == State.RUNNING else ("paused" if self.state == State.PAUSED else "stopped"))

		if len(self.pTimes) != len (self.pNames) :
			status += ".\nFound a setup error! Resetting..."
			reset()
		elif len(self.pTimes) == 0 :
			status += " and not properly set up."
		else :
			status += "."

		if not action == Action.NONE :
			status += " Will soon " + ("pause" if self.action == Action.PAUSE else "stop") + "."

		return status

	def time(self, fullInfo = False) :
		""" Generates a string containing the timer's current period and time. 
			If fullInfo is True, then it also shows the complete list of periods. """

		if self.state == State.STOPPED :
			return "Currently not running."
		
		time = "**On " + self.pNames[self.currentPeriod] + " period** (Duration: " + str(self.pTimes[self.currentPeriod]) + (" minute" if self.pTimes[self.currentPeriod] == 1 else " minutes") + ")\n\t"
		
		m, s = divmod((self.pTimes[self.currentPeriod] *60) - self.currentTime, 60)
		h, m = divmod(m, 60)

		time += "%02d:%02d:%02d" % (h, m, s)
		del h,m,s

		if self.state == State.PAUSED :
			time += "\t**(PAUSED)**"

		if fullInfo :
			time += "\n\n**Period list (Loop is " + ("ON" if self.onRepeat else "OFF")  + "):**"
			for i in range(0, len(self.pTimes)) :
				time += "\n" + self.pNames[i] + ": " + str(self.pTimes[i]) + (" minute" if self.pTimes[i] == 1 else " minutes")
				if (i == self.currentPeriod) :
					time += "\t-> _You are here!_"

		return time
