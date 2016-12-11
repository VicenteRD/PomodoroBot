import re
from enum import Enum

import pomodorobot.lib as lib
import pomodorobot.config as config
from pomodorobot.channeltimerinterface import ChannelTimerInterface


class State(Enum):
    """ Represents the states in which a pomdoro timer can be.
    """

    STOPPED = -1
    RUNNING = 1
    PAUSED = 2

    @staticmethod
    def to_string(state):
        if state == State.RUNNING:
            return "RUNNING"
        elif state == State.PAUSED:
            return "PAUSED"
        elif state == State.STOPPED:
            return "STOPPED"
        return None


class Action(Enum):
    """ Represents the actions that a pomodoro timer can do.
    """

    NONE = 0
    RUN = 1
    PAUSE = 2
    STOP = 3


class TimerEvent:
    """ Represents a timer-related event.
    """

    # The methods that listen to these events and react accordingly.
    # See `add_listener` to see restrictions.
    listeners = []

    def __init__(self, timer):
        self.timer = timer

    def dispatch(self):
        """ Dispatches the event, thus making the listeners react to it.
        """

        for listener in TimerStateEvent.listeners:
            listener(self)

    @classmethod
    def add_listener(cls, listener):
        """ Adds a listener to the list.
            Listeners must be valid, callable functions (not messages),
            and should only take 1 argument (aside from self if it's a method).

        :param listener: The listener function.
        :type listener: function
        """
        cls.listeners.append(listener)


class TimerStateEvent(TimerEvent):
    """ A timer event that represents a change on its state.
        It holds the state from which it's changing and the one it has changed
        to.
    """

    def __init__(self, timer, old_state, new_state):
        super().__init__(timer)

        self.old_state = old_state
        self.new_state = new_state


class TimerPeriodEvent(TimerEvent):
    """ A timer event that represents a change on its period.
        It has a reference to the old period as well as the new one.
    """

    def __init__(self, timer, old_period, new_period):
        super().__init__(timer)

        self.old_period = old_period
        self.new_period = new_period


class Period:
    """ Represents a Pomodoro Timer period.
        It has a name and a duration, in minutes.
    """

    def __init__(self, name, time):
        self.name = name
        self.time = time


class PomodoroTimer:
    """ A class representing a pomodoro timer.
    """

    def __init__(self, interface: ChannelTimerInterface):

        # The interface that connects this timer to the channel where it's
        # running
        self._interface = interface

        # The
        self.step = config.get_config().get_int('timer.time_step')

        # The different periods the timer has been setup with.
        self.periods = []

        # The period the timer is currently at.
        self._current_period = -1
        # The current time within the period.
        self.curr_time = 0

        # The current timer's status. This should not be edited directly,
        # as it is intended that with each change, an event is triggered.
        # See `get_state` and `set_state`
        self._state = None
        self.set_state(State.STOPPED)
        # The action the timer should react to on the next iteration of the loop
        self.action = Action.NONE

        # Whether the period list should loop or not.
        self.repeat = True
        # Whether the timer should count from 0 and show the "elapsed" time,
        # or count back from the period's time and show the remaining time.
        self._countdown = True

    def setup(self, periods_format: str, on_repeat: bool, reverse: bool):
        """ Sets the pomodoro timer up with its periods, periods' names and
            extra options

        :param periods_format: The string to get the periods from. See
            `PomodoroTimer.parse_format` for an in-depth explanation.
        :type periods_format: str

        :param on_repeat: Whether the timer should go back to period 0 after
            going through the complete list (True) or not (False).
        :type on_repeat: bool

        :param reverse: Whether the timer should show remaining (True) or
            elapsed (False) time.
        :type reverse: bool

        :return: Returns a string with the periods'
            times, separated by commas, if successful. Else, returns None.
            If the result is None, this timer will be useless until the method
            is ran successfully
        """

        self.repeat = on_repeat
        self._countdown = reverse

        self.periods = PomodoroTimer.parse_format(periods_format)

        return ", ".join(str(period.time) for period in self.periods) if \
            self.periods is not None else None

    def start(self) -> bool:
        """ Starts the timer.

        :return: True if successful, False if it was already running.
        """

        if self._state == State.RUNNING:
            return False

        self.action = Action.RUN
        return True

    def pause(self) -> bool:
        """ Pauses the timer, if it's running. Keeps all settings and
            current period and elapsed (or remaining) time.

        :return: True if the timer was running and got paused, False otherwise
            (No need to pause then).
        """

        if self._state == State.RUNNING:
            self.action = Action.PAUSE
            return True
        return False

    def resume(self) -> bool:
        """ Resumes the timer, if it was actually paused. Complains if not.

        :return: True the timer was actually paused and got resumed
            successfully, False if it was running or stopped.
        """

        if self._state == State.PAUSED:
            self.start()
            return True
        return False

    def stop(self) -> bool:
        """ Attempts to stop the timer.

        :return: True if the timer was running and got stopped successfully,
            False if the timer was paused or about to be (Timer actually
            gets stopped, cancelling the pause state/action).

        """

        if self._state == State.RUNNING:
            self.action = Action.STOP
            return True

        elif self._state == State.PAUSED or self.action == Action.PAUSED:
            self.action = Action.NONE
            self.set_state(State.STOPPED)

            self.curr_time = 0
            self._current_period = -1

            return False

    def goto(self, idx: int):
        """ Skips to the n-th period, assuming the periods are counted 1 -> n
            (Thus it actually jumps to [idx-1]).

        :param idx: The index of the period to jump to.
        :return: If successful, returns the name of the new current period.
            If not, returns None.
        """

        if 0 < idx <= len(self.periods):
            self.set_period(idx - 1)
            self.curr_time = 0
            return self.periods[self._current_period].name
        return None

    def is_set(self) -> bool:
        """ Tells whether the timer is already set up or not.

        :return: True if the timer is set and ready to go, False otherwise.
        """

        return len(self.periods) > 0

    def status(self) -> str:
        """ Tells whether the timer is stopped, running or paused, as well as
            the next timer's action.

        :return: A string stating the current status, whether it's correctly set
            up or not, and the next action it's going to take.
        """

        status = "Currently " + State.to_string(self._state).lower()

        if len(self.periods) == 0:
            status += " and not properly set up."
        else:
            status += "."

        if not self.action == Action.NONE:
            status += " Will soon "
            if self.action == Action.RUN:
                status += "start running."
            elif self.action == Action.PAUSE:
                status += "pause."
            elif self.action == Action.STOP:
                status += "stop."

        return status

    def time(self, extended=False) -> str:
        """ Generates a string containing the timer's current period and time.

        :param extended: Whether it should display extra information (True)
            or keep it simple (False).
        :return: The string with the current period and the remaining or elapsed
            time (Depending on the value of _countdown, see PomodoroTimer.setup)
        """

        if self._state == State.STOPPED:
            return "Currently not running."

        time = "**On " + self.periods[self._current_period].name + " period** "

        if extended:
            time += "(Duration: " + lib.pluralize(
                self.periods[self._current_period].time,
                "minute", append='s') + ")"

        if self._countdown:
            time += "\nRemaining:\t"
            m, s = divmod(
                (self.periods[self._current_period].time * 60) - self.curr_time,
                60)
        else:
            time += "\nElapsed:\t"
            m, s = divmod(self.curr_time, 60)

        h, m = divmod(m, 60)

        time += "%02d:%02d:%02d" % (h, m, s)
        del h, m, s

        if self._state == State.PAUSED:
            time += "\t**(PAUSED)**"

        return time

    def list_periods(self, compact=False):
        """ Generates a list of the periods as a string, flagging the
            current one.
        :return: The list of periods, specifying which one is the current one.
        """

        if compact:
            return ', '.join(str(period.time) for period in self.periods)

        p_list = "**Period list (Loop is " + (
                 "ON" if self.repeat else "OFF") + "):**"
        for i in range(0, len(self.periods)):
            period = self.periods[i]
            p_list += ("\n" + period.name + ": " +
                       lib.pluralize(period.time, "minute", append='s'))

            if i == self._current_period:
                p_list += "\t-> _You are here!_"

        return p_list

    def get_period(self):
        """ Gives the period index of the period the timer is currently in.

        :return: The index.
        """
        return self._current_period

    def get_state(self):
        """ Gives the state the timer is currently in.

        :return: The state. See `State`.
        """
        return self._state

    def set_period(self, idx: int):
        """ Sets the current period to the index specified.
            It also triggers a TimerPeriodEvent.

        :param idx: The new current period index.
        :type idx: int. Must be 0 <= idx < len(periods) or -1.
        """

        if not (idx == -1 or 0 <= idx < len(self.periods)):
            return

        old_period = self.periods[self._current_period] if \
            0 <= self._current_period < len(self.periods) else None
        new_period = self.periods[idx] if \
            0 <= idx < len(self.periods) else None

        TimerPeriodEvent(self, old_period, new_period).dispatch()

        self._current_period = idx

    def set_state(self, new_state: State):
        """ Sets the timer to a certain state.
            Also triggers a TimerStateEvent

        :param new_state: The state to set the timer to.
        :type new_state: State
        """
        if self._state != new_state:
            TimerStateEvent(self, self._state, new_state).dispatch()

            self._state = new_state

    def get_server_name(self):
        """ Gets the name of the server in which this timer is running.

        :return: The server's name.
        """
        return self._interface.get_server_name()

    def get_channel_name(self):
        """ Gets the name of the channel in which this timer is running.

        :return: The channel's name.
        """
        return self._interface.get_channel_name()

    def get_users_subscribed(self):
        """ Gets a list of users (discord.Member) subscribed or using this
            timer.

        :return: The list of members.
        """
        return self._interface.subbed

    @staticmethod
    def parse_format(periods_format: str):
        """ Parses a string into the corresponding periods.

        :param periods_format:  The string containing the periods and
            their names, in a format similar to that of a dictionary.
            Ex.: PeriodA:10,PeriodB:5,PeriodC:15
                 This will create 3 periods of 10, 5 and 15 minutes each.

            It also accepts segments with the format (nxName1:t1,Name2:t2),
            which creates n iterations of Name1:t1,Name2:t2 periods (Where
            Name1 and Name2 are the period names and t1, t2 the respective
            times).
            Ex.: (3xPeriodA:10,PeriodB:5),PeriodC:15
                This will create 7 periods of times 10,5,10,5,10,5 and 15 each.
        :type periods_format: str
        """
        if periods_format is None or ':' not in periods_format:
            return None

        periods = []
        if ',' not in periods_format:
            try:
                attempt = periods_format.split(':')
                periods.append(Period(attempt[0], int(attempt[1])))

                return periods
            except ValueError:
                return None

        sections = re.sub(r",(?=[^()]*\))", '.', periods_format).split(',')

        for section in sections:
            if section.startswith('(') and section.endswith(')'):

                section = section.replace('(', '').replace(')', '')
                splits = section.split('x')

                sub_sections = []

                for s in splits[1].strip().split('.'):
                    sub_sections.append(s.split(':'))
                    if len(sub_sections[len(sub_sections) - 1]) != 2:
                        return None

                for i in range(0, int(splits[0]) * len(sub_sections)):
                    idx = i % len(sub_sections)

                    time = int(sub_sections[idx][1])
                    if time == 0:
                        continue
                    periods.append(
                        Period(sub_sections[idx][0].replace('_', ' '),
                               int(time)))
            else:
                splits_b = section.split(':')
                if len(splits_b) != 2:
                    return None

                time = int(splits_b[1])
                if time == 0:
                    continue
                periods.append(Period(splits_b[0].replace('_', ' '), int(time)))
        return periods
