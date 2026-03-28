from rest_framework import serializers
from .models import Wall, WallMember

class WallMemberSerializer(serializers.ModelSerializer):
    # Accept an uploaded file in requests (write-only). The view handles uploading it to Firebase
    photo = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = WallMember
        fields = ['id', 'full_name', 'contact_info', 'interests', 'photo', 'photo_url', 'joined_at']
        read_only_fields = ['id', 'joined_at', 'photo_url']

    def create(self, validated_data):
        # Remove 'photo' (uploaded file) before creating the model instance — we store only the `photo_url` field
        validated_data.pop('photo', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Ensure 'photo' doesn't get passed to the model on updates either
        validated_data.pop('photo', None)
        return super().update(instance, validated_data)

class WallSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(source='members.count', read_only=True)

    class Meta:
        model = Wall
        fields = ['id', 'code', 'name', 'description', 'creator_email', 'created_at', 'member_count']
        read_only_fields = ['id', 'created_at', 'code']