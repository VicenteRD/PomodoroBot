import pomodorobot.lib as lib
import logging


class Config:
    """ TODO

    """

    _file_name = ""
    _config_map = {}

    def __init__(self, file_name: str):
        self._file_name = file_name

        self.reload()

    def reload(self):
        """ Reloads the configuration dictionary from the given file. """

        self._config_map = {}

        cfg_file = open(self._file_name, 'r')

        for line in cfg_file:
            if line.startswith('#') or line.startswith('_') or \
               line == "" or line == '\n':
                continue

            if ':' not in line:
                lib.log("Could not read line '" + line.strip() +
                        "'. Wrong format")
            else:
                key_val = line.split(':')
                key = key_val.pop(0).strip()

                key_val[0] = key_val[0].strip()
                value = ':'.join(key_val)

                self._config_map[key] = Config._format_val(value)

                lib.log("Added " + key + ":" + str(self._config_map[key]),
                        level=logging.DEBUG)

        cfg_file.close()

    def get_str(self, key: str):
        """ Returns the value corresponding to the given key.

        :param key: The key to look for.
        :return: The configuration value pertaining to the key.
        """

        if key in self._config_map.keys():
            if self._config_map[key] == "[heavy]":
                return self._load_live(key)

            return self._config_map[key]

        return None

    def get_int(self, key: str):
        """ Returns the value corresponding to the given key.

        :param key: The key to look for.
        :return: The configuration value, parsed to int, or None if the
            key is not valid.
        :raises: TypeError: if the value cannot be parsed to int.
        """

        if key in self._config_map.keys():
            val = self._config_map[key]

            if val.isdigit():
                return int(val)
            else:
                raise TypeError
        else:
            return None

    def get_boolean(self, key: str):
        """ Returns the value corresponding to the given key.

        :param key: The key to look for.
        :return: The configuration value, evaluated as boolean, or None
                 if the key is not a valid configuration key.
        :raises: TypeError: if the value cannot be parsed as boolean.

        .. note::
            The valid values are not just True or False.
            It can be either 'true', 'on', 'yes' or 'y' for True
            or 'false', 'off', 'no' or 'n' for False
            and is not case-sensitive (so something like TruE is valid).
        """

        if key in self._config_map.keys():
            val = self._config_map[key].lower()

            if val in ['true', 'on', 'yes', 'y']:
                return True
            elif val in ['false', 'off', 'no', 'n']:
                return False
            else:
                raise TypeError
        else:
            return None

    def get_list(self, key):
        """

        :param key:
        :return:
        """

        if key in self._config_map.keys():
            val = self._config_map[key]

            if isinstance(val, list):
                return val
            else:
                raise TypeError
        else:
            return None

    def _load_live(self, key):
        cfg_file = open(self._file_name, 'r')

        value = None
        multi = ""
        multiline = False
        for line in cfg_file:
            if multiline and line.startswith('_'):
                line = line.strip()[1:]
                multi += '\n' + line
                if line.endswith('"""') or line == '""""':
                    multi = multi[:-3]
                    break
            elif line.strip().startswith(key):
                aux = line.split(':')
                aux.pop(0)
                value = ':'.join(aux).replace("[heavy]", "")
                if value.strip() == '"""':
                    multiline = True
                else:
                    break

        cfg_file.close()
        return multi if multi != "" else Config._format_val(value)

    @staticmethod
    def _format_val(line):
        # If it's too much to load into RAM
        if line.startswith("[heavy]"):
            return "[heavy]"

        # If it's a list
        if line.startswith('[') and line.endswith(']'):
            line = line[1:-1]
            return list(element.strip() for element in line.split(','))

        # If it's a dictionary
        elif line.startswith('{') and line.endswith('}'):
            line = line[1:-1]
            return dict((k.strip(), v.strip())
                        for k, v in (item.split(':')
                                     for item in line.split(',')))
        else:
            return line
