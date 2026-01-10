from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from uuid import uuid4
import os
from postMang.apps import get_firebase_storage_client
from users.tasks import send_wall_notification_email

from .models import Wall, WallMember
from .serializer import WallSerializer, WallMemberSerializer

# --- Pagination Config ---
class MemberPagination(PageNumberPagination):
    page_size = 50  # Load 50 members per page
    page_size_query_param = 'page_size'
    max_page_size = 100

# 1. Create Wall (Unchanged)
class CreateWallView(generics.CreateAPIView):
    queryset = Wall.objects.all()
    serializer_class = WallSerializer
    permission_classes = [AllowAny]

# 2. Get Wall Details (Lightweight now - No members list)
class WallDetailView(generics.RetrieveAPIView):
    queryset = Wall.objects.all()
    serializer_class = WallSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'

# 3. Get Wall Members (New Endpoint for performance)
class WallMembersListView(generics.ListAPIView):
    serializer_class = WallMemberSerializer
    pagination_class = MemberPagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        wall_id = self.kwargs['wall_id']
        # Fetch members for specific wall, ordered by newest first
        return WallMember.objects.filter(wall_id=wall_id).order_by('-joined_at')

# 4. Join Wall (With 300 Limit)
class JoinWallView(generics.CreateAPIView):
    serializer_class = WallMemberSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        wall_id = self.kwargs.get('wall_id')
        wall = get_object_or_404(Wall, id=wall_id)

        # --- OPTIMIZATION CHECK: Limit to 300 ---
        current_count = wall.members.count()
        if current_count >= 300:
            raise ValidationError({"detail": "This wall has reached its limit of 300 members."})

        # Handle photo upload to Firebase if provided
        photo_file = self.request.FILES.get('photo')
        photo_url = None
        if photo_file:
            try:
                bucket = get_firebase_storage_client()
                _, ext = os.path.splitext(photo_file.name)
                destination_path = f"knowme/{wall.id}/{uuid4().hex}{ext}"
                blob = bucket.blob(destination_path)
                blob.upload_from_file(photo_file, content_type=getattr(photo_file, 'content_type', None))
                photo_url = (
                    f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/"
                    f"{destination_path.replace('/', '%2F')}?alt=media"
                )
            except Exception as e:
                print(f"Error uploading knowme photo to Firebase for wall {wall.id}: {e}")
        
        # Save Member (passing photo_url if available)
        member = serializer.save(wall=wall, photo_url=photo_url)

        # Send email asynchronously via Celery task
        try:
            send_wall_notification_email.delay(
                wall.creator_email,
                wall.name,
                member.full_name,
                member.interests,
                f"{settings.FRONTEND_URL}/walls/{wall.id}",
            )
        except Exception:
            # Don't fail the creation if email scheduling fails
            pass

    def send_notification_email(self, wall, member):
        # Backwards-compatible wrapper (schedules the Celery task)
        send_wall_notification_email.delay(
            wall.creator_email,
            wall.name,
            member.full_name,
            member.interests,
            f"{settings.FRONTEND_URL}/walls/{wall.id}",
        )