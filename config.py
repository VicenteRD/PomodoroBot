

class Config :

	_config_map = {}

	def __init__(self, fileName : str) :

		file = open(fileName, 'r')

		for line in file :
			if line.startswith('#') :
				continue

			if not ':' in line :
				print("Could not read line '" + line + "'. Wrong format")
			else :
				key_val = line.split(':')
				key = key_val.pop(0).strip()

				key_val[0] = key_val[0].strip()
				val = ':'.join(key_val)

				_config_map[key_val.pop(0).strip()] = val

				#TODO list/dictionary support and multiline support

	def get_str(self, key : str) :
		""" Returns the value corresponding to the given key. """

		return _config_map[key]

	def get_int(self, key : str) :
		""" Returns the value corresponding to the given key. """

		val = _config_map[key]
		if val.isdigit() :
			return int(val)
		else :
			raise TypeError

	def to_boolean(self, key : str) :
		""" Returns the value corresponding to the given key. """

		val = _config_map[key].lower()

		if val in ['true', 'on', 'yes', 'y'] :
			return True
		elif val in ['false', 'off', 'no', 'n'] :
			return False
		else :
			raise TypeError
