from rest_framework import generics, permissions, filters
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Exists, OuterRef, Count, Q
from django.http import Http404
from firebase_admin import firestore

from .models import ( Post, Comment, Like, Share,
                     User, Follow, Student, Organization)
from .serializer import PostSerializer, CommentSerializer, LikeSerializer, ShareSerializer, FollowSerializer, FollowingSerializer
from .utils import IsOwnerOrReadOnly
from itertools import chain
from ..firebase import db


# class PostListCreateView(generics.ListCreateAPIView):
#     """ Create a new post or list all posts """
#     queryset = Post.objects.all().order_by('-created_at')
#     serializer_class = PostSerializer
#     permission_classes = [permissions.IsAuthenticatedOrReadOnly]

#     def perform_create(self, serializer):
#         serializer.save(user=self.request.user)


# class PostDetailView(generics.RetrieveAPIView):
#     """ Retrieve a single post """
#     queryset = Post.objects.all()
#     serializer_class = PostSerializer
#     permission_classes = [permissions.IsAuthenticatedOrReadOnly]
#     lookup_field = 'slug'

#     def get_queryset(self):
#         user = self.request.user
#         if user.is_authenticated:
#             return Post.objects.annotate(
#                 has_liked=Exists(Like.objects.filter(post=OuterRef('pk'), user=user))
#             )
#         return super().get_queryset()


# class CommentCreateView(generics.CreateAPIView):
#     """ Create a new comment """
#     queryset = Comment.objects.all()
#     serializer_class = CommentSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def perform_create(self, serializer):
#         post = get_object_or_404(Post, slug=self.kwargs['slug'])
#         serializer.save(user=self.request.user, post=post)


# class LikeCreateDestroyView(generics.GenericAPIView):
#     """ Like or unlike a post """
#     queryset = Like.objects.all()
#     serializer_class = LikeSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, slug):
#         post = get_object_or_404(Post, slug=slug)
#         like, created = Like.objects.get_or_create(user=request.user, post=post)
#         if created:
#             return Response({"message": "Post liked successfully."}, status=status.HTTP_201_CREATED)
#         return Response({"message": "You have already liked this post."}, status=status.HTTP_400_BAD_REQUEST)

#     def delete(self, request, slug):
#         post = get_object_or_404(Post, slug=slug)
#         try:
#             like = Like.objects.get(user=request.user, post=post)
#             like.delete()
#             return Response({"message": "Post unliked successfully."}, status=status.HTTP_204_NO_CONTENT)
#         except Like.DoesNotExist:
#             return Response({"message": "You have not liked this post."}, status=status.HTTP_400_BAD_REQUEST)

# class SharePostView(generics.CreateAPIView):
#     queryset = Share.objects.all()
#     serializer_class = ShareSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def perform_create(self, serializer):
#         post_slug = self.kwargs['slug']
#         post = get_object_or_404(Post, slug=post_slug)

#         if Share.objects.filter(user=self.request.user, post=post).exists():
#             return Response({"message": "You have already shared this post."}, status=status.HTTP_400_BAD_REQUEST)

#         serializer.save(user=self.request.user, post=post)

# class UserPostsView(generics.ListAPIView):
#     serializer_class = PostSerializer
#     permission_classes = [permissions.IsAuthenticatedOrReadOnly]

#     def get_queryset(self):
#         display_name_slug = self.kwargs['display_name_slug']

#         try:
#             student = Student.objects.get(display_name_slug=display_name_slug)
#             user = student.user
#         except Student.DoesNotExist:
#             try:
#                 organization = Organization.objects.get(display_name_slug=display_name_slug)
#                 user = organization.user
#             except Organization.DoesNotExist:
#                 raise Http404

#         if self.request.user.is_authenticated:
#             return Post.objects.filter(user=user).annotate(
#                 has_liked=Exists(Like.objects.filter(post=OuterRef('pk'), user=self.request.user))
#             ).order_by('-created_at')

#         return Post.objects.filter(user=user).order_by('-created_at')

# class PostUpdateView(generics.UpdateAPIView):
#     """ Update a post """
#     queryset = Post.objects.all()
#     serializer_class = PostSerializer
#     permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
#     lookup_field = 'slug'

# class PostDeleteView(generics.DestroyAPIView):
#     """ Delete a post """
#     queryset = Post.objects.all()
#     serializer_class = PostSerializer
#     permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
#     lookup_field = 'slug'

# class PostSearchView(generics.ListAPIView):
#     """ Search for posts """
#     queryset = Post.objects.all()
#     serializer_class = PostSerializer
#     filter_backends = [filters.SearchFilter]
#     search_fields = ['content'] # fields to search
#     permission_classes = [permissions.IsAuthenticatedOrReadOnly]

#     def get_queryset(self):
#         if self.request.user.is_authenticated:
#             return super().get_queryset().annotate(
#                 has_liked=Exists(Like.objects.filter(post=OuterRef('pk'), user=self.request.user))
#             ).order_by('-created_at')
#         return super().get_queryset().order_by('-created_at')

# class TrendingPostsView(generics.ListAPIView):
#     """ List trending posts """
#     queryset = Post.objects.annotate(like_count=Count('likes')).order_by('-like_count', '-created_at')
#     serializer_class = PostSerializer
#     permission_classes = [permissions.IsAuthenticatedOrReadOnly]

#     def get_queryset(self):
#         if self.request.user.is_authenticated:
#             return super().get_queryset().annotate(
#                 has_liked=Exists(Like.objects.filter(post=OuterRef('pk'), user=self.request.user))
#             ).order_by('-like_count', '-created_at')
#         return super().get_queryset().order_by('-like_count', '-created_at')

# class FollowOrganizationView(generics.CreateAPIView):
#     serializer_class = FollowSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def perform_create(self, serializer):
#         organization_display_name = self.kwargs['display_name_slug']
#         try:
#             organization = Organization.objects.get(display_name_slug=organization_display_name)
#             student = Student.objects.get(user=self.request.user)

#             if Follow.objects.filter(student=student, organization=organization).exists():
#                 return Response({"message": "You are already following this organization."}, status=status.HTTP_400_BAD_REQUEST)

#             serializer.save(student=student, organization=organization)
#             return Response({"message": "Following successful!"}, status=status.HTTP_201_CREATED)

#         except Organization.DoesNotExist:
#             return Response({"message": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)
#         except Student.DoesNotExist:
#             return Response({"message": "Only students can follow organizations."}, status=status.HTTP_400_BAD_REQUEST)

# class UnfollowOrganizationView(generics.DestroyAPIView):
#     """ Unfollow an organization """
#     serializer_class = FollowSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_object(self):
#         organization_display_name_slug = self.kwargs['display_name_slug']
#         try:
#             organization = Organization.objects.get(display_name_slug=organization_display_name_slug)
#             student = Student.objects.get(user=self.request.user)
#             return Follow.objects.get(student=student, organization=organization)
#         except Organization.DoesNotExist:
#             return None
#         except Follow.DoesNotExist:
#             return None


# class FollowingOrganizationsView(generics.ListAPIView):
#     """ List organizations followed by a student """
#     serializer_class = FollowingSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         try:
#             student = Student.objects.get(user=self.request.user)
#             return Follow.objects.filter(student=student)
#         except Student.DoesNotExist:
#             return Follow.objects.none()

# class OrganizationFollowersView(generics.ListAPIView):
#     """ List followers of an organization """
#     serializer_class = FollowSerializer
#     permission_classes = [permissions.IsAuthenticatedOrReadOnly]

#     def get_queryset(self):
#         organization_display_name_slug = self.kwargs['display_name_slug']
#         try:
#             organization = Organization.objects.get(display_name_slug=organization_display_name_slug)
#             return Follow.objects.filter(organization=organization)
#         except Organization.DoesNotExist:
#             return Follow.objects.none()

# class FeedView(generics.ListAPIView):
#     """ List posts in the feed """
#     permission_classes = [permissions.IsAuthenticated]

#     def get_serializer_class(self):
#         if 'shared' in self.request.query_params:
#             return ShareSerializer
#         return PostSerializer

#     def get_queryset(self):
#         user = self.request.user
#         shared = self.request.query_params.get('shared', None)

#         try:
#             student = Student.objects.get(user=user)
#             following_organizations = Follow.objects.filter(student=student).values_list('organization__user', flat=True)
#             department = student.department
#             faculty = student.faculty
#             religion = student.religion

#             # Pre-query for followed organizations (assuming Follow model has a student field)
#             # followed_user_pks = Follow.objects.filter(student=student).values_list('user__pk', flat=True)

#             # Combine filters into a single Q object
#             combined_filter = Q(user__in=following_organizations)
#             if department:
#                 combined_filter |= Q(user__student__department=department)
#             if faculty:
#                 combined_filter |= Q(user__student__faculty=faculty)
#             if religion:
#                 combined_filter |= Q(user__student__religion=religion)
            

#             post_queryset = Post.objects.filter(combined_filter)
#             share_queryset = Share.objects.filter(user=user) if shared else Share.objects.none()

#             queryset = sorted(
#                 chain(post_queryset, share_queryset),
#                 key=lambda instance: instance.created_at if isinstance(instance, Post) else instance.shared_at,
#                 reverse=True
#             )
#         except Student.DoesNotExist:
#             queryset = Post.objects.all().order_by('-created_at')

#         if self.request.user.is_authenticated:
#             annotated_queryset = []
#             for item in queryset:
#                 if isinstance(item, Post):
#                     annotated_queryset.append(Post.objects.filter(pk=item.pk).annotate(has_liked=Exists(Like.objects.filter(post=OuterRef('pk'), user=self.request.user))).first())
#                 else:
#                     annotated_queryset.append(item)
#             return annotated_queryset
        
#         return queryset

# Custom Permission Example (simplified)
class IsFirestoreDocOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj_data):
        # For read permissions, they are often granted (IsAuthenticatedOrReadOnly)
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions are only allowed to the owner of the doc.
        # obj_data is the dictionary from Firestore
        return obj_data.get('author_id') == str(request.user.id)

##
## Post Views (Firestore)
##
class PostListCreateFirestoreView(APIView):
    """
    Create a new post or list all posts from Firestore.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        try:
            posts_ref = db.collection('posts').order_by('timestamp', direction=firestore.Query.DESCENDING)
            # Implement pagination here if needed (using limit() and start_after())
            docs = posts_ref.stream()
            posts_list = []
            for doc in docs:
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                # How to handle 'has_liked'? See notes at the end.
                posts_list.append(post_data)
            return Response(posts_list, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to retrieve posts: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = FirestorePostCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            try:
                post_payload = {
                    'author_id': str(request.user.id), # Link to Django User ID
                    'author_username': request.user.username, # Denormalize for convenience
                    'content': data['content'],
                    'slug': data.get('slug', ''), # Handle slug generation if needed
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'like_count': 0,
                    'comment_count': 0,
                    'share_count': 0,
                    # Add other fields like media_urls, visibility, etc.
                }
                # Add a new document with an auto-generated ID
                update_time, doc_ref = db.collection('posts').add(post_payload)
                
                created_post = doc_ref.get().to_dict()
                created_post['id'] = doc_ref.id
                return Response(created_post, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PostDetailFirestoreView(APIView):
    """
    Retrieve, update, or delete a single post from Firestore using document ID.
    If using slugs, you'd query: db.collection('posts').where('slug', '==', slug_value).limit(1).stream()
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Add IsFirestoreDocOwner for mutations

    def get_post_doc_and_data(self, post_id_or_slug, is_slug=False):
        try:
            if is_slug:
                docs = db.collection('posts').where('slug', '==', post_id_or_slug).limit(1).stream()
                doc = next(docs, None) # Get the first document if it exists
                if doc:
                    return doc.reference, doc.to_dict()
                return None, None
            else: # Assume it's a document ID
                doc_ref = db.collection('posts').document(post_id_or_slug)
                doc = doc_ref.get()
                if doc.exists:
                    return doc_ref, doc.to_dict()
                return None, None
        except Exception: # Broad exception for brevity
            return None, None

    def get(self, request, post_identifier): # post_identifier can be ID or slug
        # Determine if post_identifier is a slug or ID based on your URL pattern
        # For this example, let's assume it's post_id. If using slug, pass is_slug=True
        doc_ref, post_data = self.get_post_doc_and_data(post_identifier) #, is_slug=True if your URL uses slug)

        if post_data:
            post_data['id'] = doc_ref.id
            # Handle 'has_liked' here if needed for detail view
            return Response(post_data, status=status.HTTP_200_OK)
        return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, post_identifier):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        doc_ref, post_data = self.get_post_doc_and_data(post_identifier)
        if not post_data:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        # Ownership check
        if post_data.get('author_id') != str(request.user.id):
            return Response({"error": "You do not have permission to edit this post."}, status=status.HTTP_403_FORBIDDEN)

        serializer = FirestorePostUpdateSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            update_payload = serializer.validated_data
            if not update_payload:
                return Response({"error": "No data provided for update."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                doc_ref.update(update_payload)
                updated_post_data = doc_ref.get().to_dict()
                updated_post_data['id'] = doc_ref.id
                return Response(updated_post_data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, post_identifier):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        doc_ref, post_data = self.get_post_doc_and_data(post_identifier)
        if not post_data:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        # Ownership check
        if post_data.get('author_id') != str(request.user.id):
            return Response({"error": "You do not have permission to delete this post."}, status=status.HTTP_403_FORBIDDEN)

        try:
            # Important: Also delete associated comments, likes, shares (e.g., using a Cloud Function or batch writes)
            doc_ref.delete()
            # Example: Batch delete for subcollection (do this carefully)
            # comments_ref = doc_ref.collection('comments')
            # for comment_doc in comments_ref.stream():
            #     comment_doc.reference.delete() # This can be slow for many comments, use batch/Cloud Function

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

##
## Comment Views (Firestore)
## Assuming comments are a subcollection under posts: `posts/{post_id}/comments/{comment_id}`
##
class CommentCreateFirestoreView(APIView):
    """
    Create a new comment for a post in Firestore.
    URL: /api/posts/{post_id}/comments/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id): # Get post_id from URL
        post_ref = db.collection('posts').document(post_id)
        post_doc = post_ref.get()
        if not post_doc.exists:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = FirestoreCommentSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            try:
                comment_payload = {
                    'post_id': post_id,
                    'author_id': str(request.user.id),
                    'author_username': request.user.username,
                    'text': data['text'],
                    'timestamp': firestore.SERVER_TIMESTAMP
                }
                # Add comment to the subcollection
                update_time, comment_ref = post_ref.collection('comments').add(comment_payload)
                
                # Increment comment_count on the post document
                post_ref.update({'comment_count': firestore.Increment(1)})

                created_comment = comment_ref.get().to_dict()
                created_comment['id'] = comment_ref.id
                return Response(created_comment, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CommentListFirestoreView(APIView):
    """
    List comments for a specific post.
    URL: /api/posts/{post_id}/comments/
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, post_id):
        post_ref = db.collection('posts').document(post_id)
        if not post_ref.get().exists:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            comments_ref = post_ref.collection('comments').order_by('timestamp', direction=firestore.Query.ASCENDING)
            # Add pagination if needed
            docs = comments_ref.stream()
            comments_list = []
            for doc in docs:
                comment_data = doc.to_dict()
                comment_data['id'] = doc.id
                comments_list.append(comment_data)
            return Response(comments_list, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to retrieve comments: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


##
## Like Views (Firestore)
##
class LikeToggleFirestoreView(APIView):
    """
    Like or unlike a post. A single endpoint to toggle the like status.
    URL: /api/posts/{post_id}/like/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id): # post_id from URL
        user_id = str(request.user.id)
        post_ref = db.collection('posts').document(post_id)
        like_ref = post_ref.collection('likes').document(user_id) # Document ID is the user's ID

        try:
            post_doc = post_ref.get()
            if not post_doc.exists:
                return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

            like_doc = like_ref.get()
            
            # Use a Firestore transaction to ensure atomic like/unlike and count update
            @firestore.transactional
            def toggle_like_transaction(transaction, current_post_ref, current_like_ref, current_like_exists):
                if current_like_exists:
                    transaction.delete(current_like_ref)
                    transaction.update(current_post_ref, {'like_count': firestore.Increment(-1)})
                    return False # Unliked
                else:
                    transaction.set(current_like_ref, {'liked_at': firestore.SERVER_TIMESTAMP})
                    transaction.update(current_post_ref, {'like_count': firestore.Increment(1)})
                    return True # Liked

            transaction = db.transaction()
            liked_now = toggle_like_transaction(transaction, post_ref, like_ref, like_doc.exists)

            if liked_now:
                return Response({"message": "Post liked successfully."}, status=status.HTTP_201_CREATED)
            else:
                return Response({"message": "Post unliked successfully."}, status=status.HTTP_200_OK) # Or 204 if you prefer

        except Exception as e:
            return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)