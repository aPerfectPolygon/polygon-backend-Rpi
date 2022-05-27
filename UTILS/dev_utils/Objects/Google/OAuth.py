from UTILS.dev_utils.Objects.Google._utils import *
from google.oauth2 import id_token
import typing as ty


def verify(token: str) -> ty.Optional[dict]:
	try:
		return id_token.verify_oauth2_token(token, ProxyRequest())
	except ValueError:
		pass


if __name__ == '__main__':
	print(verify('eyJhbGciOiJSUzI1NiIsImtpZCI6ImZjYmQ3ZjQ4MWE4MjVkMTEzZTBkMDNkZDk0ZTYwYjY5ZmYxNjY1YTIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJhY2NvdW50cy5nb29nbGUuY29tIiwiYXpwIjoiODU0NDI5NDM3ODc4LXFrOGxua3QxdDR2cXIzdTFtbGo5b2lma2drN2pidnU2LmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tIiwiYXVkIjoiODU0NDI5NDM3ODc4LXFrOGxua3QxdDR2cXIzdTFtbGo5b2lma2drN2pidnU2LmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tIiwic3ViIjoiMTExMDYwNjM3NDM5ODM5ODQyMTAwIiwiZW1haWwiOiJwYXJzYS5hcnplc2htYW5kQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJhdF9oYXNoIjoiRHByOWJsWDQ3a3hyeUJtdmdiRXNoQSIsIm5hbWUiOiJQYXJzYSBBcnplc2htYW5kIiwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FBVFhBSnkzdV9CWkIwQ0FITkdtdHBsYTRQbklRVjJpdVBybFJ0WEV4V2p1PXM5Ni1jIiwiZ2l2ZW5fbmFtZSI6IlBhcnNhIiwiZmFtaWx5X25hbWUiOiJBcnplc2htYW5kIiwibG9jYWxlIjoiZW4iLCJpYXQiOjE2NTE0ODg5NDMsImV4cCI6MTY1MTQ5MjU0MywianRpIjoiYTQxNDg4ODY2OTJmNjM3YzYzZjYxNWI4MDJkYjRiNGI2ODA1ZmE5NCJ9.KmYrYmbw3yT5kzlh6Ahp577cRYvMXq6F3Hj_7ndQqcMy5GU0ANh6-S6lPhpOqG1X3w0O0RF7e0X08kkmcKu2ScL73YUJkYPT96F-YPvz7jgoqC3I-64tHFmA_ktwnXXYt4ERVsuKo21zxhMCLVPAheSAqawUCTImTlYmEoMMsPgoGlDH8zK1mFxcdLki5psL3f3RCkpi_pPieCIcpMInR7bKGDHHqoRmj_iNb-Iwl4mhdF7TOiRlUd5RydK1HrM8Ip2g8FPcgS40XGh0ts2Fbul-0Xp6SoR9VnS4yrtOL_Sl3pS2z_uX1mLOPr0RqhUcJPgnLos4Lx13Fi9bhBdX2A'))