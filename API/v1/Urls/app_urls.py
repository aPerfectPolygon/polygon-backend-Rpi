from API.v1.Urls import url_patterns
from UTILSD import Defaults as djn_def
from UTILSD import main as djn_utils

app_name = 'api_v1_app'
urlpatterns = url_patterns(
	djn_utils.ApiInfo(
		djn_def.Platforms.app,
		['POST'],
		djn_def.Models.app,
		djn_def.Models.app,
		token_expiration_in_seconds=djn_def.TokenExpiration.app
	)
)
