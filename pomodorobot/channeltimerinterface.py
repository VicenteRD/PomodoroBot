import discord


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
        self.subbed = []

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

    def get_server_name(self) -> str:
        return self._channel.server.name

    def get_channel_name(self) -> str:
        return self._channel.name
