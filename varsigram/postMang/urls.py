from django.urls import path
from .views import (
    PostListCreateView, PostDetailView,
    CommentCreateView, LikeCreateDestroyView,
    SharePostView, UserPostsView,
    PostUpdateView, PostDeleteView,
    PostSearchView, TrendingPostsView,
    FollowOrganizationView, UnfollowOrganizationView,
    FollowingOrganizationsView, OrganizationFollowersView,
    FeedView
)

urlpatterns = [
    path('posts/', PostListCreateView.as_view(), name='post-list-create'),
    path('posts/<slug:slug>/', PostDetailView.as_view(), name='post-detail'),
    path('posts/<slug:slug>/comments/', CommentCreateView.as_view(), name='post-comments'),
    path('posts/<slug:slug>/like/', LikeCreateDestroyView.as_view(), name='post-like'),
    path('posts/<slug:slug>/share/', SharePostView.as_view(), name='post-share'),
    path('users/<slug:display_name_slug>/posts/', UserPostsView.as_view(), name='user-posts'),
    path('posts/<slug:slug>/edit/', PostUpdateView.as_view(), name='post-edit'),
    path('posts/<slug:slug>/delete/', PostDeleteView.as_view(), name='post-delete'),
    path('posts/search/', PostSearchView.as_view(), name='post-search'),
    path('feed/', FeedView.as_view(), name='feed'),
    path('trending/', TrendingPostsView.as_view(), name='trending-posts'),
    path('organizations/<str:username>/follow/', FollowOrganizationView.as_view(), name='follow-organization'),
    path('organizations/<str:username>/unfollow/', UnfollowOrganizationView.as_view(), name='unfollow-organization'),
    path('following/', FollowingOrganizationsView.as_view(), name='following-organizations'),
    path('organizations/<str:username>/followers/', OrganizationFollowersView.as_view(), name='organization-followers'),
]