from rest_framework import serializers
from .models import Post, Comment, Like

class PostSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    comments = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'user', 'title', 'content', 'slug', 'created_at', 'updated_at', 'comments', 'likes_count']

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
