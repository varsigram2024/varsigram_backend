from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from users import urls as users_urls
from chat import urls as chat_urls
from postMang import urls as post_urls
from notifications_app import urls as notify_urls
from knowme import urls as knowme_urls
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView, # Optional: only if you need an endpoint to verify token validity
)
from users.views import CustomTokenObtainPairView, LogoutAndBlacklistRefreshToken
import os
# from users.views import (
    # GoogleLoginApi,
    # GoogleLoginRedirectApi,
# )

def assetlinks(request):
    return JsonResponse([
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
            "namespace": "android_app",
            "package_name": "com.varsigram.app",
            "sha256_cert_fingerprints":
                [os.getenv('ASSETLINKS_SHA256_FINGERPRINT')]
            }
        }
    ], safe=False)

urlpatterns = [
    path('admin/', admin.site.urls, name='admin_urls'),
    path('.well-known/assetlinks.json', assetlinks),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework_endpoints')),
    path('api/v1/', include(users_urls, namespace='users_api')),
    path('api/v1/', include(chat_urls, namespace='chat_api')),
    path('api/v1/', include(post_urls, namespace='posts_api')),
    # Uncomment if you want to use JWT authentication
    path('api/v1/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/v1/token/logout/', LogoutAndBlacklistRefreshToken.as_view(), name='token_logout'),
    path('api/v1/notifications/', include(notify_urls, namespace='notifications_api')),
    path('api/v1/', include(knowme_urls, namespace='knowme_api'))
    # path('callback/', GoogleLoginApi.as_view(), name='callback-sdk'),
    # path('redirect/', GoogleLoginRedirectApi.as_view(), name='redirect-sdk'),
]
