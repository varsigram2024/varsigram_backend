from django.urls import path
from .views import (
    GenericFollowView, GenericUnfollowView, ListFollowersView, ListFollowingView, PostListCreateFirestoreView, PostDetailFirestoreView,
    CommentCreateFirestoreView, CommentListFirestoreView,
    LikeToggleFirestoreView, LikeListFirestoreView, SharePostFirestoreView,
    UserPostsFirestoreView, TrendingPostsFirestoreView, FeedView,
    WhoToFollowView
)

urlpatterns = [
    path('posts/', PostListCreateFirestoreView.as_view(), name='post-list-create'),
    path('posts/<str:post_id>/', PostDetailFirestoreView.as_view(), name='post-detail'),
    path('posts/<str:post_id>/comments/create/', CommentCreateFirestoreView.as_view(), name='post-comment-create'),
    path('posts/<str:post_id>/comments/', CommentListFirestoreView.as_view(), name='post-comments'),
    path('posts/<str:post_id>/like/', LikeToggleFirestoreView.as_view(), name='post-like'),
    path('posts/<str:post_id>/likes/', LikeListFirestoreView.as_view(), name='post-likes-list'), # New URL for listing likes
    path('posts/<str:post_id>/share/', SharePostFirestoreView.as_view(), name='post-share'),
    path('users/<str:user_id>/posts/', UserPostsFirestoreView.as_view(), name='user-posts'),
    # path('posts/search/', PostSearchView.as_view(), name='post-search'),
    path('feed/', FeedView.as_view(), name='feed'),
    path('trending/', TrendingPostsFirestoreView.as_view(), name='trending-posts'),
    path('users/follow/', GenericFollowView.as_view(), name='follow-user'),
    path('users/unfollow/', GenericUnfollowView.as_view(), name='generic-unfollow'),
    path('users/followers/', ListFollowersView.as_view(), name='list-followers'),
    path('users/following/', ListFollowingView.as_view(), name='list-following'),
    path('who-to-follow/', WhoToFollowView.as_view(), name='who-to-follow'),
]