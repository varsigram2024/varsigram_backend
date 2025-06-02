# from rest_framework import serializers
# from .models import Post, Comment, Like, Share, Follow
# from users.serializer import UserSerializer, OrganizationProfileSerializer, StudentProfileSerializer

# class PostSerializer(serializers.ModelSerializer):
#     user = serializers.ReadOnlyField(source='user.username')
#     comments = serializers.SerializerMethodField()
#     likes_count = serializers.SerializerMethodField()

#     class Meta:
#         model = Post
#         fields = ['id', 'user', 'content', 'slug', 'created_at', 'updated_at', 'comments', 'likes_count']

#     def get_comments(self, obj):
#         comments = Comment.objects.filter(post=obj)
#         return CommentSerializer(comments, many=True).data

#     def get_likes_count(self, obj):
#         return Like.objects.filter(post=obj).count()

# class CommentSerializer(serializers.ModelSerializer):
#     user = serializers.ReadOnlyField(source='user.username')

#     class Meta:
#         model = Comment
#         fields = ['id', 'user', 'post', 'content', 'created_at']

# class LikeSerializer(serializers.ModelSerializer):
#     user = serializers.ReadOnlyField(source='user.username')

#     class Meta:
#         model = Like
#         fields = ['id', 'user', 'post']

# class ShareSerializer(serializers.ModelSerializer):
#     user = UserSerializer(read_only=True)
#     post = PostSerializer(read_only=True)  # Serialize the full post data
#     class Meta:
#         model = Share
#         fields = ('id', 'user', 'post', 'shared_at')

# class FollowSerializer(serializers.ModelSerializer):
#     organization = OrganizationProfileSerializer(read_only=True)
#     student = StudentProfileSerializer(read_only=True)

#     class Meta:
#         model = Follow
#         fields = ('id', 'organization', 'student', 'created_at')
#         read_only_fields = ('created_at',)

# class FollowingSerializer(serializers.ModelSerializer):
#     organization = OrganizationProfileSerializer(read_only=True)

#     class Meta:
#         model = Follow
#         fields = ('organization', 'created_at')
#         read_only_fields = ('created_at',)


# your_app/serializers.py
from users.serializer import UserSerializer, OrganizationProfileSerializer, StudentProfileSerializer
from .models import Post, Comment, Like, Share, Follow
from rest_framework import serializers

# ... (User related serializers can remain if User model is still in SQL) ...

class FirestorePostCreateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=10000)
    slug = serializers.SlugField(required=False) # If you still want to generate/use slugs
    # Add other fields like media_url, etc.

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Post content cannot be empty.")
        return value

class FirestorePostUpdateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=10000, required=False)
    # other fields that can be updated

class FirestoreCommentSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000)

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Comment text cannot be empty.")
        return value

# You'll need serializers for Like and Share if they have input data, otherwise not strictly needed for create/delete.

class FirestoreLikeOutputSerializer(serializers.Serializer):
    """
    Serializer for representing a 'Like' object fetched from Firestore.
    Assumes a 'like' document might contain who liked and when.
    The 'id' could be the user_id if that's how you key the like documents
    under a post's 'likes' subcollection.
    """
    id = serializers.CharField(read_only=True) # Firestore document ID (e.g., user_id who liked)
    user_id = serializers.CharField(read_only=True) # ID of the user who liked
    # If you want to nest user details (assuming UserSerializer works for your SQL User model):
    # user = UserSerializer(read_only=True) # You'd need to pass the user object here
    post_id = serializers.CharField(read_only=True) # ID of the liked post
    timestamp = serializers.DateTimeField(read_only=True, source='liked_at') # Assuming 'liked_at' field

# your_app/serializers.py
from rest_framework import serializers
# Assuming UserSerializer is for your SQL-based Django User model
from users.serializer import UserSerializer
# from .firebase import db # Not typically needed in serializer, logic is in view

# ... (other serializers) ...

class FirestoreLikeOutputSerializer(serializers.Serializer):
    """
    Serializer for representing a 'Like' object fetched from Firestore.
    Assumes a 'like' document might contain who liked and when.
    The 'id' could be the user_id if that's how you key the like documents
    under a post's 'likes' subcollection.
    """
    id = serializers.CharField(read_only=True) # Firestore document ID (e.g., user_id who liked)
    user_id = serializers.CharField(read_only=True) # ID of the user who liked
    # If you want to nest user details (assuming UserSerializer works for your SQL User model):
    # user = UserSerializer(read_only=True) # You'd need to pass the user object here
    post_id = serializers.CharField(read_only=True) # ID of the liked post
    timestamp = serializers.DateTimeField(read_only=True, source='liked_at') # Assuming 'liked_at' field

    # Note: For simply creating/deleting likes, your views might not need an input serializer
    # as the necessary info (user_id from request, post_id from URL) is usually sufficient.    

class FirestoreShareCreateInputSerializer(serializers.Serializer):
    """
    Input serializer for when a user shares a post.
    post_id will likely come from the URL, but if it's in the body, include it here.
    """
    # post_id = serializers.CharField() # If you expect post_id in the request body
    user_comment = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True)

# You'll need a FirestorePostOutputSerializer (adapted from previous responses)
# if you want to nest the full post details. Let's assume you have one:
class FirestorePostOutputSerializer(serializers.Serializer): # Simplified for this example
    id = serializers.CharField(read_only=True)
    author_username = serializers.CharField(read_only=True)
    content = serializers.CharField(read_only=True)
    # ... other relevant post fields ...

class FirestoreShareOutputSerializer(serializers.Serializer):
    """
    Serializer for representing a 'Share' object fetched from Firestore.
    """
    id = serializers.CharField(read_only=True) # Firestore document ID of the share
    
    # Information about the user who shared
    # Assuming UserSerializer is for your SQL-based Django User model
    # In the view, when serializing, you'd fetch the Django User object using user_id from Firestore
    # and pass it to UserSerializer.
    user = UserSerializer(read_only=True) # Represents the user who shared

    # Information about the post that was shared
    # This assumes 'original_post_data' is a dictionary stored in the share document
    # or you fetch the post separately and pass it to FirestorePostOutputSerializer
    post = FirestorePostOutputSerializer(read_only=True) # Represents the shared post

    user_comment = serializers.CharField(read_only=True, required=False) # User's comment on the share
    shared_at = serializers.DateTimeField(read_only=True, source='timestamp') # Timestamp of the share

class FollowSerializer(serializers.ModelSerializer):
    """
    Serializer for the Follow model (Student follows Organization).
    This assumes Follow, Student, and Organization are still Django ORM models.
    """
    # For read operations, these nested serializers will show details
    organization = OrganizationProfileSerializer(read_only=True)
    student = StudentProfileSerializer(read_only=True)

    # For write operations (creating a follow), you might want to accept IDs
    # or have these come from the view context/URL.
    # If you need to accept IDs in the request body for creating a follow:
    # organization_id = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all(), source='organization', write_only=True)
    # student_id = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), source='student', write_only=True)

    class Meta:
        model = Follow
        fields = ('id', 'organization', 'student', 'created_at')
        read_only_fields = ('created_at', 'id') # 'student' is often set in perform_create

    # Your view's perform_create would typically set the student from request.user
    # and get the organization from a URL kwarg.


class FollowingSerializer(serializers.ModelSerializer):
    """
    Serializer to list organizations a student is following.
    This assumes Follow and Organization are still Django ORM models.
    """
    organization = OrganizationProfileSerializer(read_only=True)

    class Meta:
        model = Follow # This serializer is still based on the Follow model instances
        fields = ('organization', 'created_at') # Shows the followed organization and when
        read_only_fields = ('created_at',)