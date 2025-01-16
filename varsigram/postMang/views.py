from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Exists, OuterRef

from .models import Post, Comment, Like, Share
from .serializer import PostSerializer, CommentSerializer, LikeSerializer, ShareSerializer


class PostListCreateView(generics.ListCreateAPIView):
    queryset = Post.objects.all().order_by('-created_at')
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PostDetailView(generics.RetrieveAPIView):
    """ """
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Post.objects.annotate(
                has_liked=Exists(Like.objects.filter(post=OuterRef('pk'), user=user))
            )
        return super().get_queryset()


class CommentCreateView(generics.CreateAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        post = get_object_or_404(Post, slug=self.kwargs['slug'])
        serializer.save(user=self.request.user, post=post)


class LikeCreateDestroyView(generics.GenericAPIView):
    queryset = Like.objects.all()
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        post = get_object_or_404(Post, slug=slug)
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if created:
            return Response({"message": "Post liked successfully."}, status=status.HTTP_201_CREATED)
        return Response({"message": "You have already liked this post."}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug):
        post = get_object_or_404(Post, slug=slug)
        try:
            like = Like.objects.get(user=request.user, post=post)
            like.delete()
            return Response({"message": "Post unliked successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Like.DoesNotExist:
            return Response({"message": "You have not liked this post."}, status=status.HTTP_400_BAD_REQUEST)

class SharePostView(generics.CreateAPIView):
    queryset = Share.objects.all()
    serializer_class = ShareSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        post_slug = self.kwargs['slug']
        post = get_object_or_404(Post, slug=post_slug)

        # Check if the user has already shared the post
        if Share.objects.filter(user=self.request.user, post=post).exists():
            return Response({"message": "You have already shared this post."}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(user=self.request.user, post=post)

