from django.urls import path
from .views import CreateWallView, WallDetailView, WallMembersListView, JoinWallView

app_name = 'knowme'

urlpatterns = [
    # Create a wall
    path('walls/', CreateWallView.as_view(), name='create-wall'),

    # Get Wall Info (Name, Desc, Count) - Fast!
    path('walls/<uuid:id>/', WallDetailView.as_view(), name='wall-detail'),

    # Get Members (Paginated) - Optimized!
    # Usage: /api/walls/{uuid}/members/?page=1
    path('walls/<uuid:wall_id>/members/', WallMembersListView.as_view(), name='wall-members'),

    # Join Wall
    path('walls/<uuid:wall_id>/join/', JoinWallView.as_view(), name='join-wall'),
]