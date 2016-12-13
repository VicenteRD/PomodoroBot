import sys
import io

import pomodorobot.config as config
import pomodorobot.lib as lib

from pomodorobot.bot import PomodoroBot


USAGE = sys.argv[0] + " <token>"
DESCRIPTION = '''A marinara timer bot that can be configured to your needs.'''

bot = PomodoroBot(
    command_prefix='!',
    description=DESCRIPTION,
    timer_step=2,
    response_lifespan=15,
    pm_help=True
)

if __name__ == '__main__':

    TOKEN = ""
    if len(sys.argv) < 2:
        print("Not enough arguments received!\nUsage: " + sys.argv[0] +
              " <token>")
        exit(-1)

    elif len(sys.argv) == 2:
        TOKEN = sys.argv[1]

    else:
        exit(-2)

    # Config

    config.load('bot.yml')

    # Logging

    sys.stdout = sys.__stdout__ = io.TextIOWrapper(sys.stdout.detach(),
                                                   encoding='utf8',
                                                   errors='backslashreplace',
                                                   line_buffering=True)
    lib.init_logger()

    # Bot init

    bot.reload_config(config.get_config())
    bot.load_extension('pomodorobot.ext.timercommands')
    bot.load_extension('pomodorobot.ext.events')
    bot.load_extension('pomodorobot.ext.other')

    bot.run(TOKEN)
