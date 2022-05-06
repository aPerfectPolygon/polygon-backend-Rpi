import pandas as pd


class TrackerManager:
	def __init__(self):
		self.trackers = pd.DataFrame(columns=['id', 'tag', 'value'])
	
	def tracker_untrack(self, tracker_id: int, tag: str = None, value: str = None):
		conds = (self.trackers.id == tracker_id)
		if tag is not None:
			conds &= (self.trackers.tag == tag)
		if value is not None:
			conds &= (self.trackers.value == value)
		
		self.trackers = self.trackers.loc[~conds]
	
	def tracker_track(self, tracker_id: int, tag: str, value: str = None):
		# check if it already exists
		conds = (self.trackers.tag == tag)
		if value is not None:
			conds &= (self.trackers.value == value)
		if self.trackers.loc[conds].empty:
			self.trackers = self.trackers.append(
				pd.DataFrame(
					[[tracker_id, tag, value]], columns=['id', 'tag', 'value']
				)
			)
	
	def get_trackers(self, tag: str, value: str = None):
		conds = (self.trackers.tag == tag)
		if value is not None:
			conds &= (self.trackers.value == value)
			
		return self.trackers.loc[conds]


if __name__ == '__main__':
	tracker_manager = TrackerManager()
	tracker_manager.tracker_track(1, 'X', 1)
	tracker_manager.tracker_track(1, 'X', 2)
	tracker_manager.tracker_track(1, 'Y')
	# tracker_manager.tracker_untrack(1)
	print(tracker_manager.trackers)
	print(tracker_manager.get_trackers('X', 1))
	