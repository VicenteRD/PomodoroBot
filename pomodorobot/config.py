import yaml
import logging

import pomodorobot.lib as lib


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

        For lists, the format is the same than that of the
        python notation, so it would be:
            list: [element_1, element_2, element_3]
        and a dictionary format is almost the same, but uses ' - ' instead
        of ':', thus a dictionary would be noted as:
            dict: {key_1 - value_1, key_2 - value_2, key_3 - value_3}


        For values too big to be worth holding in memory, you can add a [heavy]
        tag at the beggining of the value. This will make the formatter ignore
        the value until it's called for, at which moment it will load it
        directly from the file. For example, to use with a multi-line string,
        the first line of such value would look like (Again, no backslash):
            heavy-string: [heavy] \"""

        Comments are allowed within the file by starting a line with #.
    """

    _file_name = None
    _config_map = {}

    def __init__(self):
        pass

    def set_file(self, file_name: str):
        self._file_name = file_name

    def is_set(self):
        return self._config_map and self._file_name is not None

    def reload(self):
        """ Reloads the configuration dictionary from the given file.

        :return: Itself to allow easier statement chaining
        """
        file = open(self._file_name, 'r')
        self._config_map = yaml.safe_load(file)
        file.close()

        return self

    def get_section(self, path):
        """ Gets a section of the configuration.
            The path is a list of super-sections, in order, or a string of them
            separated by dots
            Ex.: If a config file has the structure
                server:
                    channel_1:
                        person_A:
                            name: 'John'
                            last: 'Doe"

            You can get person_A's section by using the path
            'server.channel_1.person_A'.

        :param path: The path to the dictionary.
        :type path: str or list

        :return: The configuration section, as a dictionary, or None if it's not
            a dictionary type.
        """
        if isinstance(path, str):
            keys = path.split('.')
        else:
            keys = path

        section = self._config_map
        for key in keys:
            if key in section.keys():
                section = section[key]
                if not isinstance(section, dict):
                    return None
        return section

    def get_element(self, path: str):
        """ Gets the element corresponding to the path.
            See `get_section` to see how paths work.

            One should avoid using this method, as it's not type-safe. Instead,
            use the methods `get_str`, `get_int`, `get_boolean` or `get_list`

        :param path: The path of the element to get.
        :type path: str

        :return: The configuration element.
        """
        keys = path.split('.')
        element_key = keys.pop(-1)

        section = self.get_section(keys)
        return section[element_key] if\
            section is not None and element_key in section.keys() else None

    def get_str(self, path: str):
        """ Returns the string corresponding to the given key, if valid.

        :param path: The key to look for.
        :type path: str

        :return: The configuration value pertaining to the key, or None if there
            is no value associated with the given key.

        :raises: TypeError: if the value cannot be parsed to `str`.
        """

        string = self.get_element(path)
        if isinstance(string, str):
            return string
        raise TypeError("Configuration value {} could not be parsed to `str`"
                        .format(path))

    def get_int(self, path: str):
        """ Returns the value corresponding to the given key.

        :param path: The key to look for.
        :type path: str

        :return: The configuration value, parsed to int, or None if the
            key is not valid.

        :raises: TypeError: if the value cannot be parsed to `int`.
        """

        number = self.get_element(path)
        if isinstance(number, int):
            return number
        raise TypeError("Configuration value {} could not be parsed to `int`"
                        .format(path))

    def get_boolean(self, path: str):
        """ Returns the value corresponding to the given key.

        :param path: The key to look for.
        :type path: str

        :return: The configuration value, evaluated as boolean, or None
            if the key is not a valid configuration key.

        :raises: TypeError: if the value cannot be parsed as boolean.

        .. note::
            The valid values are not just True or False.
            It can be either 'true', 'on', 'yes' or 'y' for True
            or 'false', 'off', 'no' or 'n' for False
            and is not case-sensitive (so something like TruE is valid).
        """

        boolean = self.get_element(path)
        try:
            return None if boolean is None else\
                lib.to_boolean(boolean)
        except TypeError:
            raise TypeError(("Configuration value {} could not be parsed to " +
                            "`boolean`").format(path))

    def get_list(self, path):
        """ Returns the list corresponding to the given key.

        :param path: The key to look for.
        :type path: str

        :return: The list corresponding to the given key, or None if there is
            no value associated to that key.

        :raises: TypeError: if the value is not a list.
        """
        e_list = self.get_element(path)
        if isinstance(e_list, list):
            return e_list
        raise TypeError("Configuration value {} could not be parsed to `list`"
                        .format(path))


_instance = Config()


def load(file_name: str):
    _instance.set_file(file_name)
    _instance.reload()


def get_config():
    if _instance.is_set():
        return _instance
    else:
        lib.log("Configuration instance was asked for before it was set up.",
                level=logging.ERROR)
