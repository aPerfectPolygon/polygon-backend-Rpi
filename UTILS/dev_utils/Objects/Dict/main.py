import typing as ty


class Popper:
	def __init__(self, data: dict):
		self.data = data
		self.pop_items = []

	def add(self, item):
		if item not in self.pop_items:
			self.pop_items.append(item)
		return self

	def flush(self):
		self.pop_items = []
		return self

	def pop(self, pop_items: ty.Union[str, list, tuple] = None):
		if pop_items is not None:
			pop_items = pop_items if type(pop_items) in (list, tuple) else [pop_items]
			for item in pop_items:
				try:
					self.data.pop(item)
				except:
					pass

		for item in self.pop_items:
			try:
				self.data.pop(item)
			except:
				pass
		self.flush()
		return self


def multiselect(data: dict, selection: ty.Union[list, tuple], on_error: ty.Any = 'drop') -> dict:
	output = {}
	if on_error == 'drop':
		for item in selection:
			try:
				output.update({item: data[item]})
			except:
				pass
	else:
		for item in selection:
			output.update({item: data.get(item, on_error)})
	return output
