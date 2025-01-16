from django.urls import path
from .views import (
    PostListCreateView, PostDetailView,
    CommentCreateView, LikeCreateDestroyView,
    SharePostView
)

urlpatterns = [
    path('posts/', PostListCreateView.as_view(), name='post-list-create'),
    path('posts/<slug:slug>/', PostDetailView.as_view(), name='post-detail'),
    path('posts/<slug:slug>/comments/', CommentCreateView.as_view(), name='post-comments'),
    path('posts/<slug:slug>/like/', LikeCreateDestroyView.as_view(), name='post-like'),
    path('posts/<slug:slug>/share/', SharePostView.as_view(), name='post-share'),
]