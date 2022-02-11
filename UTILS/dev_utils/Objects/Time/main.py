import asyncio as aio
import datetime as dt
import typing as ty
import time as ti

import pandas as pd
import pytz

import UTILS.dev_utils.Objects.Float as Float


def _get_tz(tz: str) -> str:
	return 'Asia/Tehran' if tz == 'local' else tz


def ts2dt(ts: ty.Union[int, float], tz: str = 'local', remove_tz=False) -> dt.datetime:
	t = dt.datetime.fromtimestamp(float(ts), tz=pytz.timezone(_get_tz(tz)))
	if remove_tz:
		t = tz_remove(t)
	return t


def dt2ts(t: dt.datetime, as_tz: str = 'gmt'):
	""" if `t` does not have timezone consider it at GMT """
	if t.tzinfo is None:
		t = t.replace(tzinfo=pytz.timezone(_get_tz(as_tz)))
	return t.timestamp()


def dtnow(tz: str = 'local', remove_tz=False) -> dt.datetime:
	t = dt.datetime.now(tz=pytz.timezone(_get_tz(tz)))
	if remove_tz:
		t = tz_remove(t)
	return t


def tz_convertor(_dt: dt.datetime, tz='local', auto_localize=False, remove_tz=False) -> dt.datetime:
	if _dt.tzinfo:
		t = _dt.astimezone(pytz.timezone(_get_tz(tz)))
	elif auto_localize:
		t = pytz.timezone(_get_tz(tz)).localize(_dt)
	else:
		t = _dt

	if remove_tz:
		t = tz_remove(t)
	return t


def tz_remove(_dt: dt.datetime) -> dt.datetime:
	return _dt.replace(tzinfo=None)


class ParseTimeDelta:
	def __init__(self, delta, int_convert=True):
		self.total_seconds = delta.total_seconds()
		self.microseconds = delta.microseconds
		self.milliseconds = Float.divide(self.microseconds, 1000, ndigits=2)
		self.seconds = delta.seconds

		self.minutes = Float.divide(self.total_seconds, 60, ndigits=2)
		if int_convert:
			self.minutes = int(self.minutes)

		self.hours = Float.divide(self.total_seconds, 3600, ndigits=2)
		if int_convert:
			self.hours = int(self.hours)

		self.days = delta.days

		self.weeks = Float.divide(delta.days, 7, ndigits=2)
		if int_convert:
			self.weeks = int(self.weeks)

		self.months = Float.divide(self.weeks, 4, ndigits=2)
		if int_convert:
			self.months = int(self.months)


def compare_times(
		compare_with: dt.datetime, compare_type='EQL',
		year=None, month=None, day=None,
		hour=None, minute=None, second=None, microsecond=None
) -> bool:
	year = year if year is not None else compare_with.year
	month = month if month is not None else compare_with.month
	day = day if day is not None else compare_with.day
	hour = hour if hour is not None else compare_with.hour
	minute = minute if minute is not None else compare_with.minute
	second = second if second is not None else compare_with.second
	microsecond = microsecond if microsecond is not None else compare_with.microsecond

	# create to_compare
	to_compare = dt.datetime(year, month, day, hour, minute, second, microsecond)

	if compare_type == 'EQL':
		return compare_with == to_compare
	elif compare_type == 'GRT':
		return compare_with > to_compare
	elif compare_type == 'GRT_EQL':
		return compare_with >= to_compare
	elif compare_type == 'LSS':
		return compare_with < to_compare
	elif compare_type == 'LSS_EQL':
		return compare_with <= to_compare
	else:
		raise ValueError(f"Bad 'compare_type' {compare_type} ")


def series_ts_from_dt(col: pd.Series) -> pd.Series:
	return col.apply(lambda x: None if pd.isna(x) else int(x.value / 1000000000))


def series_tz_convert(data: pd.Series, timezone: ty.Optional[str] = None) -> pd.DatetimeIndex:
	"""
	if `data` is tz-aware convert it to requested timezone
	"""
	_data = pd.DatetimeIndex(data)
	if _data.tz:  # tz-aware (we can change timezone)
		timezone = 'Asia/Tehran' if timezone == 'local' else timezone
		_data = _data.tz_convert(timezone)

		if str(_data.tz) == 'GMT':
			_data = _data.tz_localize(None)

	return _data


def sleep_till_next_minute():
	ti.sleep(65 - dt.datetime.now().second)


async def aio_sleep_till_next_minute():
	await aio.sleep(65 - dt.datetime.now().second)


class Tracer:
	def __init__(self, start=False):
		self.ts_start = None
		self.ts_end = None
		if start:
			self.start()

	def start(self):
		self.ts_start = dtnow()

	def end(self, start_again=False):
		self.ts_end = dtnow()
		delta = str(self.ts_end - self.ts_start)
		if start_again:
			self.start()
		return delta
