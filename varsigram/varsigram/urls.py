"""varsigram URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from users import urls as users_urls
from chat import urls as chat_urls
from postMang import urls as post_urls
from notifications_app import urls as notify_urls
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView, # Optional: only if you need an endpoint to verify token validity
)
# from users.views import (
    # GoogleLoginApi,
    # GoogleLoginRedirectApi,
# )

urlpatterns = [
    path('admin/', admin.site.urls, name='admin_urls'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework_endpoints')),
    path('api/v1/', include(users_urls, namespace='users_api')),
    path('api/v1/', include(chat_urls, namespace='chat_api')),
    path('api/v1/', include(post_urls, namespace='posts_api')),
    # Uncomment if you want to use JWT authentication
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/v1/notifications/', include(notify_urls, namespace='notifications_api')),
    # path('callback/', GoogleLoginApi.as_view(), name='callback-sdk'),
    # path('redirect/', GoogleLoginRedirectApi.as_view(), name='redirect-sdk'),
]
