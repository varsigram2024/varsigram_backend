from rest_framework import serializers
from .models import Post, Comment, Like, Share, Follow
from users.serializer import UserSerializer, OrganizationProfileSerializer, StudentProfileSerializer

class PostSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    comments = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'user', 'content', 'slug', 'created_at', 'updated_at', 'comments', 'likes_count']

    def get_comments(self, obj):
        comments = Comment.objects.filter(post=obj)
        return CommentSerializer(comments, many=True).data

    def get_likes_count(self, obj):
        return Like.objects.filter(post=obj).count()

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Comment
        fields = ['id', 'user', 'post', 'content', 'created_at']

class LikeSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Like
        fields = ['id', 'user', 'post']

class ShareSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    post = PostSerializer(read_only=True)  # Serialize the full post data
    class Meta:
        model = Share
        fields = ('id', 'user', 'post', 'shared_at')

class FollowSerializer(serializers.ModelSerializer):
    organization = OrganizationProfileSerializer(read_only=True)
    student = StudentProfileSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ('id', 'organization', 'student', 'created_at')
        read_only_fields = ('created_at',)

class FollowingSerializer(serializers.ModelSerializer):
    organization = OrganizationProfileSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ('organization', 'created_at')
        read_only_fields = ('created_at',)

