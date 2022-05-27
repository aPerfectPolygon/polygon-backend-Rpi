import pandas as pd

from UTILS import Cache
from UTILSD import Defaults as djn_def
from UTILSD import main as djn_utils


def objects(request: djn_utils.CustomRequest, info: djn_utils.ApiInfo):
	"""
	UpdatedAt: ---

	About:
	-----
	return home objects

	Input:
	-----
	| Link: Home/objects
	| methods: post
	| token required: True
	| user must be active: True

	Response:
	-----
	| status: 200
	| comment: ---
	| Message: UTILSD.Defaults.Messages.ok
	| Result: [
	| 	{
	| 		"id": 2,
	| 		"room_id": 1,
	| 		"name": "Lamp1",
	| 		"type": "lamp",
	| 		"module_type": "IO",
	| 		"module_io": 1
	| 	},
	| ]
	| ----------------------------------------------------

	Django Errors:
	-----
	main:
		| ---
	links:
		| UTILSD.main.MainMiddleware.utils.check_user_if_required
		| UTILSD.main.MainMiddleware.utils.check_active_user_if_detected
	possible attack:
		| ---
	unexpected:
		| ---
	"""
	if not Cache.home_objects_api:
		for item in Cache.home_objects.to_dict('records'):
			item['room_id'] = None if pd.isna(item['room_id']) else int(item['room_id'])
			item['module_io'] = None if pd.isna(item['module_io']) else int(item['module_io'])
			
			Cache.home_objects_api.append(item)
	
	return djn_utils.d_response(
		request,
		djn_def.Messages.ok,
		result=Cache.home_objects_api
	)
