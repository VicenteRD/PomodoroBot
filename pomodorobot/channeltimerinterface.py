import discord

from datetime import datetime, timedelta


class ChannelTimerInterface:
    """ Defines things related to a timer but not part of one, that a bot makes
        use of.
    """

    def __init__(self,channel: discord.Channel):
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

    def restart_inactivity(self):
        """ Checks whether a timer has entered inactivity (no subs)

        :return: True if inactive, False otherwise
        """
        self._inactivity = datetime.now() if len(self.subbed) == 0 else None

        return self._inactivity is not None

    def check_inactivity(self, timer_time: int, user_time: int):
        if self._inactivity is None:
            return self.check_inactive_subs(user_time)

        if self._inactivity + timedelta(minutes=timer_time) <= datetime.now():
            # timer has been inactive for `timer_time` minutes
            self.timer.stop()
            print('success')
            return True

    def check_inactive_subs(self, time: int):
        unsubbed = []
        allowed_time = datetime.now() - timedelta(minutes=time)

        for sub, last_activity in self.subbed.items():
            # print(sub.name + ": " + str(last_activity) + "\n" +
            #       str(allowed_time))
            if last_activity <= allowed_time:
                unsubbed.append(sub)
        for sub in unsubbed:
            del self.subbed[sub]

        if len(self.subbed) == 0:
            self._inactivity = datetime.now()

        return unsubbed
