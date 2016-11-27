import pomodorobot.lib as lib
import logging


class Config:
    """ Represents a configuration loader, that loads configurations from
        a file into a dictionary

        The file must have its values stored with the format 'key: value'
        Current supported values are strings (including multi-line ones),
        booleans, integers, lists and dictionaries.

        Integers and booleans are also saved as strings if a tag is not
        specified, but are converted to the correct type when get_int or
        get_boolean are used.
        Valid tags are [i] for integers and [b] for booleans, so for example:
            key_1: [i] 1
            key_2: [b] True
        Will load correct integer and boolean values, correspondingly.
        Valid boolean values are specified in the documentation for get_boolean.

        For multi-line strings, the first line must be such that the first line
        is just three double quotes ("), and each new line must start with an
        underscore (_), and either the last line must end with the same three
        double quotes or the last line itself must be the double quotes.
            For example (ignore the back-slash next to the quotes):
            multi-line: \"""
            _This is the first line of a multi-line string configuration value
            _and this is the second.
            _It now ends
            _\"""

        For dictionaries and lists, the format is the same than that of the
        python notation, so a list would be:
            list: [element_1, element_2, element_3]
        and a dictionary would be:
            dict: {key_1: value_1, key_2: value_2, key_3: value_3}


        For values too big to be worth holding in memory, you can add a [heavy]
        tag at the beggining of the value. This will make the formatter ignore
        the value until it's called for, at which moment it will load it
        directly from the file. For example, to use with a multi-line string,
        the first line of such value would look like (Again, no backslash):
            heavy-string: [heavy] \"""

        Comments are allowed within the file by starting a line with #.
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
        :type key: str

        :return: The configuration value pertaining to the key, or None if there
            is no value associated with the given key
        """

        if key in self._config_map.keys():
            if self._config_map[key] == "[heavy]":
                return self._load_live(key)

            return self._config_map[key]

        return None

    def get_int(self, key: str):
        """ Returns the value corresponding to the given key.

        :param key: The key to look for.
        :type key: str

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
        :type key: str

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
            return lib.to_boolean(self._config_map[key].lower())
        else:
            return None

    def get_list(self, key):
        """ Returns the list corresponding to the given key.

        :param key: The key to look for.
        :type key: str

        :return: The list corresponding to the given key, or None if there is
            no value associated to that key.

        :raises: TypeError: if the value is not a list.
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

        if line.startswith("[i]"):
            line.replace("[i]", "")
            return int(line)
        elif line.startswith("[b]"):
            line.replace("[b]", "")
            return lib.to_boolean(line)
        # If it's a list
        elif line.startswith('[') and line.endswith(']'):
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
