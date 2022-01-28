from django.urls import path, include

urlpatterns = [
	path('v1/', include('API.v1.Urls', 'api_v1'))
]
