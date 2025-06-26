from datetime import datetime, timezone
from users.serializer import UserSerializer, OrganizationProfileSerializer, StudentProfileSerializer
from .models import Follow
from rest_framework import serializers
import logging
from django.contrib.contenttypes.models import ContentType

class FirestorePostCreateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=10000)
    slug = serializers.CharField(max_length=255, required=False, allow_blank=True, help_text="Optional URL-friendly slug for the post.")
    media_urls = serializers.ListField(
        child=serializers.URLField(max_length=2000, allow_blank=True),
        required=False,
        allow_empty=True,
        help_text="List of media URLs associated with the post."
    )
    # Add other fields like media_url, etc.

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Post content cannot be empty.")
        return value

class FirestorePostUpdateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=10000, required=False)
    # other fields that can be updated

class FirestoreCommentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    author_id = serializers.CharField(read_only=True)
    author_name = serializers.CharField(read_only=True, required=False, allow_null=True)
    author_display_name_slug = serializers.CharField(read_only=True, required=False, allow_null=True)
    text = serializers.CharField(max_length=2000)
    timestamp = serializers.DateTimeField(read_only=True, required=False, allow_null=True)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        author_id = ret.get('author_id')
        authors_map = self.context.get('authors_map', {})
        if author_id and str(author_id) in authors_map:
            author = authors_map[str(author_id)]
            ret['author_name'] = author.get('name')
            ret['author_display_name_slug'] = author.get('display_name_slug')
        else:
            ret['author_name'] = "Unknown User"
            ret['author_display_name_slug'] = None
        return ret

class FirestoreLikeOutputSerializer(serializers.Serializer):
    """
    Serializer for representing a 'Like' object fetched from Firestore.
    Assumes a 'like' document might contain who liked and when.
    The 'id' could be the user_id if that's how you key the like documents
    under a post's 'likes' subcollection.
    """
    id = serializers.CharField(read_only=True) # Firestore document ID (e.g., user_id who liked)
    user_id = serializers.CharField(read_only=True) # ID of the user who liked
    post_id = serializers.CharField(read_only=True) # ID of the liked post
    timestamp = serializers.DateTimeField(read_only=True, source='liked_at') # Assuming 'liked_at' field  

class FirestoreShareCreateInputSerializer(serializers.Serializer):
    """
    Input serializer for when a user shares a post.
    post_id will likely come from the URL, but if it's in the body, include it here.
    """
    # post_id = serializers.CharField() # If you expect post_id in the request body
    user_comment = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True)

class FirestorePostOutputSerializer(serializers.Serializer):
    """
    Serializer for representing a 'Post' object fetched from Firestore.
    This is an OUTPUT (read-only) serializer, meant for displaying post data.
    """
    id = serializers.CharField(read_only=True, help_text="The Firestore document ID of the post.")
    author_id = serializers.CharField(read_only=True, help_text="The ID of the post's author (denormalized).")
    author_name = serializers.CharField(read_only=True, help_text="The actual name of the post's author (denormalized).")
    author_profile_pic_url = serializers.URLField(read_only=True, allow_null=True, allow_blank=True)
    content = serializers.CharField(read_only=True, help_text="The main text content of the post.")
    
    # Include other fields that exist in your Firestore post documents and you want to output:
    slug = serializers.CharField(read_only=True, required=False, help_text="URL-friendly slug of the post.")
    media_urls = serializers.ListField(
        child=serializers.URLField(max_length=2000, allow_blank=True),
        read_only=True,
        allow_empty=True,
        help_text="List of media URLs associated with the post."
    )
    timestamp = serializers.DateTimeField(read_only=True, help_text="Timestamp when the post was created.")
    like_count = serializers.IntegerField(read_only=True, help_text="Number of likes on the post.")
    comment_count = serializers.IntegerField(read_only=True, help_text="Number of comments on the post.")
    share_count = serializers.IntegerField(read_only=True, help_text="Number of shares of the post.")

    # If you implement the 'has_liked' logic in your view:
    has_liked = serializers.BooleanField(read_only=True, required=False, help_text="True if the current authenticated user has liked this post.")
    trending_score = serializers.IntegerField(default=0)
    
    # Firestore Timestamp objects need special handling for output
    # You might want a custom field for this or simply convert to string
    # For simplicity, let's assume it's just a string in the DB for now,
    # or you'd use a custom serializer field or a datetime.datetime object.
    # If last_engagement_at is a Firestore Timestamp, it will be a datetime object in Python
    last_engagement_at = serializers.DateTimeField(required=False, allow_null=True)

    author_display_name_slug = serializers.CharField(read_only=True, help_text="The display_name_slug of the post's author (denormalized).", required=False, allow_null=True)

    # You might need to add a custom method for representation if your Firestore
    # data structure doesn't directly map to these fields (e.g., nested author info)
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        
        # Format Firestore Timestamps to ISO strings
        for field in ['last_engagement_at', 'created_at', 'updated_at']:
            if field in ret and isinstance(ret[field], datetime):
                # Ensure datetime objects have timezone info before ISO formatting
                if ret[field].tzinfo is None:
                    ret[field] = ret[field].replace(tzinfo=timezone.utc)
                ret[field] = ret[field].isoformat()


        # Fetch author details from PostgreSQL using author_id from context
        author_id = ret.get('author_id')
        if author_id:
            authors_map = self.context.get('authors_map')
            if authors_map and str(author_id) in authors_map:
                author = authors_map[str(author_id)]
                ret['author_name'] = author.get('name')
                ret['author_profile_pic_url'] = author.get('profile_pic_url')
                ret['author_display_name_slug'] = author.get('display_name_slug')
            else:
                logging.warning(f"Author with PostgreSQL ID {author_id} not found in authors_map for post {ret.get('id')}.")
                ret['author_name'] = "Unknown User"
                ret['author_profile_pic_url'] = None
                ret['author_display_name_slug'] = None
        else:
            ret['author_name'] = "Unknown User"
            ret['author_profile_pic_url'] = None
            ret['author_display_name_slug'] = None

        return ret




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

class GenericFollowSerializer(serializers.ModelSerializer):
    follower_type = serializers.CharField(write_only=True)
    follower_id = serializers.IntegerField(write_only=True)
    followee_type = serializers.CharField(write_only=True)
    followee_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Follow
        fields = [
            'id', 'follower_type', 'follower_id', 'followee_type', 'followee_id',
            'created_at',
            'follower_student', 'follower_organization',
            'followee_student', 'followee_organization'
        ]
        read_only_fields = ('created_at', 'id', 'follower_student', 'follower_organization', 'followee_student', 'followee_organization')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Follower
        follower = instance.follower
        if hasattr(follower, 'name'):  # Student
            data['follower_student'] = StudentProfileSerializer(follower).data
            data['follower_organization'] = None
        elif hasattr(follower, 'organization_name'):  # Organization
            data['follower_student'] = None
            data['follower_organization'] = OrganizationProfileSerializer(follower).data
        else:
            data['follower_student'] = None
            data['follower_organization'] = None
        # Followee
        followee = instance.followee
        if hasattr(followee, 'name'):  # Student
            data['followee_student'] = StudentProfileSerializer(followee).data
            data['followee_organization'] = None
        elif hasattr(followee, 'organization_name'):  # Organization
            data['followee_student'] = None
            data['followee_organization'] = OrganizationProfileSerializer(followee).data
        else:
            data['followee_student'] = None
            data['followee_organization'] = None
        return data

    def create(self, validated_data):
        follower_type = validated_data.pop('follower_type')
        follower_id = validated_data.pop('follower_id')
        followee_type = validated_data.pop('followee_type')
        followee_id = validated_data.pop('followee_id')

        follower_content_type = ContentType.objects.get(model=follower_type.lower())
        followee_content_type = ContentType.objects.get(model=followee_type.lower())

        follow, created = Follow.objects.get_or_create(
            follower_content_type=follower_content_type,
            follower_object_id=follower_id,
            followee_content_type=followee_content_type,
            followee_object_id=followee_id,
        )
        return follow