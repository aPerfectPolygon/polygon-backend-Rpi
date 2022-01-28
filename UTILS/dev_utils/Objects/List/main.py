import math
import pandas as pd
import typing as ty

from UTILS.dev_utils import Log


class Popper:
	def __init__(self, data: ty.Union[list, tuple]):
		self.data = data
		self.pop_items = []
	
	def add(self, item):
		self.pop_items.append(item)
		return self
	
	def pop(self, pop_items: ty.Union[str, list, tuple] = None):
		if pop_items is not None:
			pop_items = pop_items if type(pop_items) in (list, tuple) else [pop_items]
			for item in pop_items:
				try:
					self.data.remove(item)
				except:
					pass
		
		for item in self.pop_items:
			try:
				self.data.remove(item)
			except:
				pass
		return self


def has_duplicates(data: ty.Union[list, tuple]) -> bool:
	return pd.Index(data).has_duplicates


def drop_duplicates(data: ty.Union[list, tuple], keep='first') -> ty.Union[list, tuple]:
	return type(data)(pd.Index(data).drop_duplicates(keep=keep).values)


def drop_selected(data: ty.Union[list, tuple], to_drop: ty.Union[list, tuple]) -> ty.Union[list, tuple]:
	res = pd.Series(data)
	return type(data)(res.loc[~res.isin(to_drop)])


def split(data: ty.Union[list, tuple], **kwargs) -> ty.List[list]:
	"""
	split list to list of lists with specified length

	kwargs -> (count_per_item: int, items_count: int)

	count_per_item  (old splits)
		specify maximum length of each item of output
		[1, 2, 3, 4, 5, 6, 7], count_per_item = 2  ->  [[1, 2], [3, 4], [5, 6], [7]]

	items_count  (old outputs)
		specify maximum length of output
		[1, 2, 3, 4, 5, 6, 7] items_count = 2  ->  [[1, 2, 3, 4], [5, 6, 7]]

	"""
	if not data:
		return [[]]
	count_per_item = kwargs.pop('count_per_item', None)
	items_count = kwargs.pop('items_count', None)
	
	if not any((count_per_item, items_count,)):
		raise Exception('at least one of ["count_per_item", "items_count"] must be specified')
	
	_len = len(data)
	if items_count:
		count_per_item = math.ceil(_len / items_count)
	
	return [data[i:i + count_per_item] for i in range(0, _len, count_per_item)]


def join(data: ty.Union[list, tuple], splitter: str) -> str:
	"""
	join everything in 'data' with splitter

	[1, 'a', ['x', 'd']], splitter=','  ->  '1,a,x,d'
	"""
	return splitter.join(pd.Series(data).explode().astype('str').values)


def get_diff(x1: ty.Union[list, pd.Series], x2: ty.Union[list, pd.Series], force_as: str = None) -> list:
	"""returns item where are in x1 that are not in x2"""
	if force_as == 'series' or (isinstance(x1, pd.Series) and isinstance(x2, pd.Series)):
		return list(x1[~x1.isin(x2)].values)
	if force_as == 'list' or (isinstance(x1, list) and isinstance(x2, list)):
		return list(set(x1) - set(x2))
	raise ValueError(f'(Series, Series) or (list, list) -> got ({type(x1)}, {type(x2)})')


def move2end(in_list: list, item):
	if item in in_list and in_list[-1] != item:
		in_list.remove(item)
		in_list.append(item)  # add to end


def contains(l1: list, l2: list, **kwargs) -> bool:
	"""
	** return False if `l1` has duplicates

	if l2 contains l1

	|	l2		l1	|
	|	*			|
	|	*		*	|	-> True
	|	*		*	|
	|	*		*	|


	|	l2		l1	|
	|			*	|
	|	*		*	|	-> False
	|	*		*	|
	|	*		*	|

	**
	l1 -> to check
	l2 -> standard one
	**

	kwargs:
		check_max_length -> return False if length `l1` is more than length `l2` and do not go to loop
		check_duplicates -> return False `l1` has duplicates
		to_log -> enable logging for errors

	"""
	check_max_length = kwargs.pop('check_max_length', True)
	check_duplicates = kwargs.pop('check_duplicates', True)
	check_type = kwargs.pop('check_type', True)
	to_log = kwargs.pop('to_log', True)
	
	if check_duplicates and has_duplicates(l1):
		if to_log:
			Log.log(f'`l1` contains duplicates')
		return False
	
	if type(l1) not in [list, tuple, set]:
		if to_log:
			Log.log(f'`l1` ({type(l1)}) is not iterable')
		return False
	if type(l2) not in [list, tuple, set]:
		if to_log:
			Log.log(f'`l2` ({type(l2)}) is not iterable')
		return False
	
	if check_max_length is not None and len(l1) > len(l2):
		if to_log:
			Log.log(f'length `l1` ({len(l1)}) is more than length `l2` ({len(l2)})')
		return False
	
	if check_type:
		for item in l1:
			try:
				if type(l2[l2.index(item)]) != type(item):
					raise
			except:
				if to_log:
					Log.log(f'item `{item}` of `l1` is not present in `l2`')
				return False
	else:
		for item in l1:
			if item not in l2:
				if to_log:
					Log.log(f'item `{item}` of `l1` is not present in `l2`')
				return False
	return True


# noinspection PyUnboundLocalVariable
def level_detector(
		input_list: ty.List[ty.Union[int, float]],
		item: ty.Union[int, float],
		uptrend: bool = None,
		equality_as_new_level: bool = False
) -> int:
	"""
	detect which level does `item` have in `input_list`
	if len(input_list) < 2 then `uptrend` must be specified
	
	#############################################
	#   equality_as_new_level=True				#
	#            | 2     | 5     | 8			#
	#        0 1 | 2 3 4 | 5 6 7 | 8 9 10		#
	#   <--  ____|_______|_______|________  -->	#
	#   <--   0  |   1   |   3   |   4      -->	#
	#############################################
	
	#############################################
	#   equality_as_new_level=False				#
	#            2 |     5 |     8 |			#
	#        0 1 2 | 3 4 5 | 6 7 8 | 9 10		#
	#   <--  ______|_______|_______|______  -->	#
	#   <--     0  |   1   |   3   |  4     -->	#
	#############################################
	
	
	>>> level_detector([2, 5, 7], 1) # -> 0
	>>> level_detector([2, 5, 7], 2, equality_as_new_level=True) # -> 1
	>>> level_detector([2, 5, 7], 2) # -> 0
	>>> level_detector([7, 5, 2], 2) # -> 2
	>>> level_detector([7], 2, uptrend=True) # -> 0
	>>> level_detector([7], 2, uptrend=False) # -> 1
	
	"""
	if not input_list:
		raise ValueError('input_list must not be empty')
	
	if len(input_list) < 2 and uptrend is None:
		raise ValueError('if len(input_list) < 2 then `uptrend` must be specified')
	
	if uptrend is None:
		uptrend = input_list[0] < input_list[1]
	
	if uptrend:
		if equality_as_new_level:
			for i, litem in enumerate(input_list):
				# when accept_equality_as_new_level is on -> do not check equality and let it be check at next loop
				if item < litem:
					return i
			return i + 1
		else:
			for i, litem in enumerate(input_list):
				if item <= litem:
					return i
			if litem == item:
				return i
			else:
				return i + 1
	else:
		if equality_as_new_level:
			for i, litem in enumerate(input_list):
				if item > litem:
					return i
			return i + 1
		else:
			for i, litem in enumerate(input_list):
				if item >= litem:
					return i
			if litem == item:
				return i
			else:
				return i + 1
