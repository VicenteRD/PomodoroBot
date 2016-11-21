

class Config :

	_file_name = ""
	_config_map = {}

	def __init__(self, file_name : str) :
		self._file_name = file_name

		self.reload()
	
	def reload(self) :
		_config_map = {}

		cfg_file = open(self._file_name, 'r')

		for line in cfg_file :
			if line.startswith('#') or line == "" or line == "\n" :
				continue

			if not ':' in line :
				print("Could not read line '" + line + "'. Wrong format")
			else :
				key_val = line.split(':')
				key = key_val.pop(0).strip()

				key_val[0] = key_val[0].strip()
				val = ':'.join(key_val)

				# If it's a list
				if val.startswith('[') and val.endswith(']') :
					val = val[1:-1]
					self._config_map[key] = val.split(',')

				# If it's a dictionary
				elif val.startswith('{') and val. endswith('}') :
					val = val[1:-1]
					self._config_map[key] = dict((k.strip(), v.strip()) \
						for k,v in (item.split(':') for item in val.split(',')))

				else :
					self._config_map[key] = val

		cfg_file.close()

		#TODO list/dictionary support and multiline support

	def get_str(self, key : str) :
		""" Returns the value corresponding to the given key. """

		return self._config_map[key] if key in self._config_map.keys() else None

	def get_int(self, key : str) :
		""" Returns the value corresponding to the given key. """

		if key in self._config_map.keys() :
			val = self._config_map[key]
			
			if val.isdigit() :
				return int(val)
			else :
				raise TypeError
		else :
			return None

	def to_boolean(self, key : str) :
		""" Returns the value corresponding to the given key. """

		if key in self._config_map.keys() :
			val = self._config_map[key].lower()

			if val in ['true', 'on', 'yes', 'y'] :
				return True
			elif val in ['false', 'off', 'no', 'n'] :
				return False
			else :
				raise TypeError
		else :
			return None
