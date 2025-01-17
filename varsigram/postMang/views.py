from rest_framework import generics, permissions, filters
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Exists, OuterRef, Count, Q

from .models import ( Post, Comment, Like, Share,
                     User, Follow, Student)
from .serializer import PostSerializer, CommentSerializer, LikeSerializer, ShareSerializer, FollowSerializer
from .utils import IsOwnerOrReadOnly
from itertools import chain


class PostListCreateView(generics.ListCreateAPIView):
    """ Create a new post or list all posts """
    queryset = Post.objects.all().order_by('-created_at')
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PostDetailView(generics.RetrieveAPIView):
    """ Retrieve a single post """
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
    """ Create a new comment """
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        post = get_object_or_404(Post, slug=self.kwargs['slug'])
        serializer.save(user=self.request.user, post=post)


class LikeCreateDestroyView(generics.GenericAPIView):
    """ Like or unlike a post """
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

        if Share.objects.filter(user=self.request.user, post=post).exists():
            return Response({"message": "You have already shared this post."}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(user=self.request.user, post=post)

class UserPostsView(generics.ListAPIView):
    """ List all posts by a user """
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        username = self.kwargs['username']  # Get username from URL
        user = get_object_or_404(User, username=username)  # Retrieve the user
        if self.request.user.is_authenticated:
            return Post.objects.filter(user=user).annotate(
                has_liked=Exists(Like.objects.filter(post=OuterRef('pk'), user=self.request.user))
            ).order_by('-created_at')
        return Post.objects.filter(user=user).order_by('-created_at')

class PostUpdateView(generics.UpdateAPIView):
    """ Update a post """
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = 'slug'

class PostDeleteView(generics.DestroyAPIView):
    """ Delete a post """
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = 'slug'

class PostSearchView(generics.ListAPIView):
    """ Search for posts """
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['content'] # fields to search
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return super().get_queryset().annotate(
                has_liked=Exists(Like.objects.filter(post=OuterRef('pk'), user=self.request.user))
            ).order_by('-created_at')
        return super().get_queryset().order_by('-created_at')

class TrendingPostsView(generics.ListAPIView):
    """ List trending posts """
    queryset = Post.objects.annotate(like_count=Count('like')).order_by('-like_count', '-created_at')
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return super().get_queryset().annotate(
                has_liked=Exists(Like.objects.filter(post=OuterRef('pk'), user=self.request.user))
            ).order_by('-like_count', '-created_at')
        return super().get_queryset().order_by('-like_count', '-created_at')

class FollowOrganizationView(generics.CreateAPIView):
    """ Follow an organization """
    queryset = Follow.objects.all()
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        organization_username = self.kwargs['username']
        try:
            organization = User.objects.get(username=organization_username, organization__isnull=False)
            student = Student.objects.get(user=self.request.user)
            if Follow.objects.filter(student=student, organization=organization).exists():
                return Response({"message": "You are already following this organization."}, status=status.HTTP_400_BAD_REQUEST)

            serializer.save(student=self.request.user, organization=organization)

        except User.DoesNotExist:
            return Response({"message": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)
        except Student.DoesNotExist:
            return Response({"message": "Only students can follow organizations."}, status=status.HTTP_400_BAD_REQUEST)


class UnfollowOrganizationView(generics.DestroyAPIView):
    """ Unfollow an organization """
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        organization_username = self.kwargs['username']
        try:
            organization = User.objects.get(username=organization_username, organization__isnull=False)
            return Follow.objects.get(student=self.request.user, organization=organization)
        except User.DoesNotExist:
            return None
        except Follow.DoesNotExist:
            return None


class FollowingOrganizationsView(generics.ListAPIView):
    """ List organizations followed by a student """
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Follow.objects.filter(student=user)

class OrganizationFollowersView(generics.ListAPIView):
    """ List followers of an organization """
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        username = self.kwargs['username']
        try:
            organization = User.objects.get(username=username, organization__isnull=False)
            return Follow.objects.filter(organization=organization)
        except User.DoesNotExist:
            return Follow.objects.none()

class FeedView(generics.ListAPIView):
    """ List posts in the feed """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if 'shared' in self.request.query_params:
            return ShareSerializer
        return PostSerializer

    def get_queryset(self):
        user = self.request.user
        shared = self.request.query_params.get('shared', None)  
        try:
            student = Student.objects.get(user=user)
            department = student.department
            faculty = student.faculty
            religion = student.religion
            following_organizations = Follow.objects.filter(student=student).values_list('organization', flat=True)
            post_queryset = Post.objects.filter(Q(user__in=following_organizations) | Q(user__student=student) | Q(user__student__department=department) | Q(user__student__faculty=faculty) | Q(user__student__religion=religion))
            share_queryset = Share.objects.filter(user=user) if shared else Share.objects.none()

            queryset = sorted(
                chain(post_queryset, share_queryset),
                key=lambda instance: instance.created_at if isinstance(instance, Post) else instance.shared_at,
                reverse=True
            )
        except Student.DoesNotExist:
            queryset = Post.objects.all().order_by('-created_at')

        if self.request.user.is_authenticated:
            annotated_queryset = []
            for item in queryset:
                if isinstance(item, Post):
                    annotated_queryset.append(Post.objects.filter(pk=item.pk).annotate(has_liked=Exists(Like.objects.filter(post=OuterRef('pk'), user=self.request.user))).first())
                else:
                    annotated_queryset.append(item)
            return annotated_queryset

        return queryset

