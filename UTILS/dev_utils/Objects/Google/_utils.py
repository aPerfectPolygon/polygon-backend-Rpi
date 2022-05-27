from google.auth.transport import requests
from google.auth.transport.requests import _Response
from google.auth import exceptions
import six
from UTILS.dev_utils import Defaults as dev_def


class ProxyRequest(requests.Request):
	def __init__(self):
		super().__init__()

	def __call__(
			self,
			url,
			method="GET",
			body=None,
			headers=None,
			timeout=6,
			**kwargs
	):
		# noinspection PyUnresolvedReferences
		try:
			return _Response(
				self.session.request(
					method, url, data=body, headers=headers, timeout=timeout,
					proxies=dev_def.proxies, **kwargs
				)
			)
		except requests.exceptions.RequestException as caught_exc:
			new_exc = exceptions.TransportError(caught_exc)
			six.raise_from(new_exc, caught_exc)
