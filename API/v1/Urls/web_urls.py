from API.v1.Urls import url_patterns
from UTILSD import Defaults as djn_def
from UTILSD import main as djn_utils

app_name = 'api_v1_web'
urlpatterns = url_patterns(
	djn_utils.ApiInfo(
		djn_def.Platforms.web,
		['POST'],
		djn_def.Models.web,
		djn_def.Models.web,
		token_expiration_in_seconds=djn_def.TokenExpiration.web
	)
)
