from UTILS.dev_utils import safe_request
import typing as ty


def verify(
		secret: str,
		response: str,
		allowed_hosts: ty.List[str] = None,
		allowed_package_names: ty.List[str] = None,
		allowed_actions: ty.List[str] = None,
		min_score: float = 0.7
) -> dict:
	res = safe_request(
		'post',
		'https://www.google.com/recaptcha/api/siteverify',
		params={'secret': secret, 'response': response},
		expected_codes=[200]
	)
	if res.is_success and res.status_code == 200:
		if not res.Json['success']:
			return {'success': False, 'obj': res.Json}

		if 'hostname' in res.Json:
			if allowed_hosts is not None and res.Json['hostname'] not in allowed_hosts:
				return {'success': False, 'obj': res.Json}
			if allowed_actions is not None and res.Json['action'] not in allowed_actions:
				return {'success': False, 'obj': res.Json}
			if min_score is not None and res.Json['score'] < min_score:
				return {'success': False, 'obj': res.Json}

			return {'success': True, 'obj': res.Json}
		else:
			if allowed_package_names is not None and res.Json['apk_package_name'] not in allowed_package_names:
				return {'success': False, 'obj': res.Json}
			return {'success': True, 'obj': res.Json}

	return {'success': False, 'obj': None}
