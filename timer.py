

class Timer :
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
	timerState = TState.STOPPED
	# The action the timer should react to on the next iteration of the loop
	nextAction = TAction.NONE

	# Whether the period list should loop or not.
	onRepeat = True

	def setup(self, pFormat) :
	""" Sets the marinara timer. """

		if self.timerState == TState.RUNNING or self.timerState == TState.PAUSED :
			print("Someone tried to modify the timer while it was already running!")
			##await bot.say("Please stop the timer completely before modifying it.")
			return False, -1

		if len(bot.pTimes) > 0 :
			print("Rejecting setup command, there is a period set already established")
			##await bot.say("I'm already set and ready to go, please use the reset command if you want to change the timer configuration.")
			return False, -2

		#if timerFormat == "help" :
		#	await bot.say("**Example:**\n\t" + COMMAND_PREFIX + "setup (2xStudy:32,Break:8),Study:32,Long_Break:15\n\t_This will give you a sequence of 32, 8, 32, 8, 32, 15_")
		#	return False, "this one is staying on the bot's method"

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

			#await bot.say("Correctly set up timer config: " + concat, delete_after = 15)
			return True
		else :
			#print("Could not set the periods correctly, command 'setup' failed")
			#await bot.say("I did not understand what you wanted, please try again!")
			return False


	def generateTimeStatus(self, fullInfo = False) :
		""" Generates a string containing the timer's current period and time. 
			If fullInfo is True, then it also shows the complete list of periods. """

		if bot.timerState == TState.STOPPED :
			return "Currently not running."
		
		ret = "**On " + bot.pNames[bot.currentPeriod] + " period** (Duration: " + str(bot.pTimes[bot.currentPeriod]) + (" minute" if bot.pTimes[bot.currentPeriod] == 1 else " minutes") + ")\n\t"
		
		m, s = divmod(bot.currentTime, 60)
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

	def isSet(self) :
		""" Tells whether the timer is already set up or not. Also does a precheck to see if the setup is actually well done. """

		if len(pTimes) != len(pNames) :
			# should go on a 'reset' function
			pTimes = []
			pNames = []

			currentPeriod = -1
			current time = 0

		return len(pTimes) > 0