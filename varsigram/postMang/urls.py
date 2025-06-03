from django.urls import path
from .views import (
    PostListCreateFirestoreView, PostDetailFirestoreView,
    CommentCreateFirestoreView, CommentListFirestoreView,
    LikeToggleFirestoreView, LikeListFirestoreView, FollowingOrganizationsView, OrganizationFollowersView, FollowOrganizationView, UnfollowOrganizationView 
)

urlpatterns = [
    path('posts/', PostListCreateFirestoreView.as_view(), name='post-list-create'),
    path('posts/<str:post_id>/', PostDetailFirestoreView.as_view(), name='post-detail'),
    path('posts/<str:post_id>/comments/create/', CommentCreateFirestoreView.as_view(), name='post-comment-create'),
    path('posts/<str:post_id>/comments/', CommentListFirestoreView.as_view(), name='post-comments'),
    path('posts/<str:post_id>/like/', LikeToggleFirestoreView.as_view(), name='post-like'),
    path('posts/<str:post_id>/likes/', LikeListFirestoreView.as_view(), name='post-likes-list'), # New URL for listing likes
    # path('posts/<slug:slug>/share/', SharePostView.as_view(), name='post-share'),
    # path('users/<slug:display_name_slug>/posts/', UserPostsView.as_view(), name='user-posts'),
    # path('posts/<slug:slug>/edit/', PostUpdateView.as_view(), name='post-edit'),
    # path('posts/<slug:slug>/delete/', PostDeleteView.as_view(), name='post-delete'),
    # path('posts/search/', PostSearchView.as_view(), name='post-search'),
    # path('feed/', FeedView.as_view(), name='feed'),
    # path('trending/', TrendingPostsView.as_view(), name='trending-posts'),
    path('users/<slug:display_name_slug>/follow/', FollowOrganizationView.as_view(), name='follow-organization'),
    path('users/<slug:display_name_slug>/unfollow/', UnfollowOrganizationView.as_view(), name='unfollow-organization'),
    path('following/', FollowingOrganizationsView.as_view(), name='following-organizations'),
    path('users/<slug:display_name_slug>/followers/', OrganizationFollowersView.as_view(), name='organization-followers'),
]