import typing as ty

from UTILS.dev_utils import Decorators
from UTILS.engines.__base__ import Sms

templates = []


@Decorators.threaded
def send(
		receivers: ty.Union[str, ty.List[str]],
		template: str,
		var1: ty.Optional[str] = None,
		var2: ty.Optional[str] = None,
		var3: ty.Optional[str] = None,
):
	if template not in templates:
		raise ValueError(f'bad template: {template}')
	
	if not isinstance(receivers, list):
		receivers = [receivers]
	
	Sms.Kavehnegar().send(receivers, template, var1, var2, var3)


if __name__ == '__main__':
	send(
		['+989196864660'],
		'social2',
		'NAME',
		'LINK'
	)
	print('ok')
