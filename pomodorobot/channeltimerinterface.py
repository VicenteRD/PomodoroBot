import discord

from pomodorobot.dbmanager import db_manager

from datetime import datetime, timedelta


class ChannelTimerInterface:
    """ Defines things related to a timer but not part of one, that a bot makes
        use of.
    """

    def __init__(self, channel: discord.Channel):
        # The channel this interface is linked to.
        self._channel = channel

        # The timer this interface wraps.
        self.timer = None

        # The list of people subscribed to this timer.
        self.subbed = {}

        # Whether this timer is locked or not.
        self.locked = False
        # The channel to redirect to, or None if spoofing is off on this
        # channel.
        self.spoofed = None

        # The message linked to the timer that holds the time information.
        self.time_message = None
        # The message linked to the timer that holds the periods information.
        self.list_message = None

        # Whether the bot should speak this timer's changes out loud.
        self.tts = False

        # The timer has been inactive (no subs) for
        self._inactivity = None

    def get_server_name(self) -> str:
        return self._channel.server.name

    def get_channel_name(self) -> str:
        return self._channel.name

    def add_sub(self, user, time, refresh=False):
        """ Adds a user to the subscribed list, with a timestamp.

        :param user: The user to add to the list.
        :param time: The time at which the user subscribed at.
        :param refresh: Whether the user should be
            un-subscribed and re-subscribed if he's already subscribed.
        """
        if user in self.subbed:
            if not refresh:
                return None
            self.remove_sub(user)

        self.subbed[user] = {}
        self.subbed[user]['start'] = time
        self.subbed[user]['last'] = time
        self.subbed[user]['time'] = 0

        db_manager.set_user_attendance(user, time)

    def remove_sub(self, user):
        """ Removes a user from the subscribed list, with a timestamp.
            Returns the status of the timer

        :param user: The user to remove from the list.
        :return: 0 if the timer is active, -1 if it's inactive, -2 if it was
            stopped due to inactivity or -3 if there's no timer
        """
        from pomodorobot.timer import State  # Just for my IDE to be happy...
        if user not in self.subbed:
            return

        db_manager.set_user_last_session(user, self.subbed[user]['time'])
        del self.subbed[user]

        if self.timer is None:
            return -3
        if len(self.subbed) != 0:
            return 0

        if self.timer.get_state() == State.PAUSED:
            self.timer.stop()
            return -2
        elif self.timer.get_state() == State.RUNNING:
            return -1 if self.restart_inactivity() else 0

    def add_sub_time(self, time):
        """ Adds time to all subscribed people's counter.

        :param time: The time to add to people's counters
        """
        for user, records in self.subbed.items():
            records['time'] += time

    def restart_inactivity(self):
        """ Checks whether a timer has entered inactivity (no subs)

        :return: True if inactive, False otherwise
        """
        self._inactivity = datetime.now() if len(self.subbed) == 0 else None

        return self._inactivity is not None

    def check_inactivity(self, timer_time: int, user_time: int):
        """ Checks whether the timer or subscribed users are inactive.

        :param timer_time: The time the timer is allowed to be inactive for.
        :param user_time: The time users are allowed to be inactive for while
            subscribed.
        :return: True if the timer is inactive, else gives a list of people that
            have been removed due to inactivity (can be empty).
        """
        if self._inactivity is None:
            return self.check_inactive_subs(user_time)

        if self._inactivity + timedelta(minutes=timer_time) <= datetime.now():
            # timer has been inactive for `timer_time` minutes
            self.timer.stop()
            print('success')
            return True

    def check_inactive_subs(self, time: int):
        """ Checks for subscribed users that might be inactive.

        :param time: The time users are allowed to be inactive for while
            subscribed.
        :return: A list of users that have been forcibly un-subscribed due to
            inactivity (can be empty).
        """
        unsubbed = []
        allowed_time = datetime.now() - timedelta(minutes=time)

        for sub, times in self.subbed.items():
            # print(sub.name + ": " + str(last_activity) + "\n" +
            #       str(allowed_time))
            if times['last'] <= allowed_time:
                unsubbed.append(sub)
        for sub in unsubbed:
            self.remove_sub(sub)

        if len(self.subbed) == 0:
            self._inactivity = datetime.now()

        return unsubbed
