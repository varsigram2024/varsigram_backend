from rest_framework import generics, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from firebase_admin import firestore
from postMang.apps import get_firestore_db  # Import the Firestore client from the app config
from .models import (User, Follow, Student, Organization)
from .serializer import FirestoreCommentSerializer, FirestoreLikeOutputSerializer, FirestorePostCreateSerializer, FirestorePostUpdateSerializer, FirestorePostOutputSerializer, GenericFollowSerializer
from .utils import get_exclusive_org_user_ids, get_student_user_ids
import logging
from datetime import datetime, timezone, timedelta
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework_simplejwt.authentication import JWTAuthentication


# Initialize Firestore client
db = get_firestore_db()  # Get the Firestore client from the app config

class IsVerified(permissions.BasePermission):
    """
    Allows access only to verified users.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_verified", False))



class GenericFollowView(generics.CreateAPIView):
    serializer_class = GenericFollowSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

class GenericUnfollowView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        follower_type = request.data.get('follower_type')
        follower_user_id = request.data.get('follower_id')  # This is user.id from frontend
        followee_type = request.data.get('followee_type')
        followee_user_id = request.data.get('followee_id')  # This is user.id from frontend

        if not all([follower_type, follower_user_id, followee_type, followee_user_id]):
            return Response({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        follower_content_type = ContentType.objects.get(model=follower_type.lower())
        followee_content_type = ContentType.objects.get(model=followee_type.lower())

        # Resolve profile IDs from user IDs
        try:
            if follower_type.lower() == 'student':
                follower_profile_id = Student.objects.get(user_id=follower_user_id).id
            elif follower_type.lower() == 'organization':
                follower_profile_id = Organization.objects.get(user_id=follower_user_id).id
            else:
                return Response({"error": "Invalid follower_type."}, status=status.HTTP_400_BAD_REQUEST)

            if followee_type.lower() == 'student':
                followee_profile_id = Student.objects.get(user_id=followee_user_id).id
            elif followee_type.lower() == 'organization':
                followee_profile_id = Organization.objects.get(user_id=followee_user_id).id
            else:
                return Response({"error": "Invalid followee_type."}, status=status.HTTP_400_BAD_REQUEST)
        except (Student.DoesNotExist, Organization.DoesNotExist):
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            follow = Follow.objects.get(
                follower_content_type=follower_content_type,
                follower_object_id=follower_profile_id,
                followee_content_type=followee_content_type,
                followee_object_id=followee_profile_id,
            )
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Follow.DoesNotExist:
            return Response({"error": "Follow relationship does not exist."}, status=status.HTTP_404_NOT_FOUND)

class ListFollowersView(generics.ListAPIView):
    serializer_class = GenericFollowSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        followee_type = self.request.query_params.get('followee_type')
        followee_user_id = self.request.query_params.get('followee_id')  # This is user.id from frontend
        if not followee_type or not followee_user_id:
            return Follow.objects.none()
        followee_content_type = ContentType.objects.get(model=followee_type.lower())
        # Resolve profile id from user id
        if followee_type.lower() == 'student':
            try:
                followee_profile_id = Student.objects.get(user_id=followee_user_id).id
            except Student.DoesNotExist:
                return Follow.objects.none()
        elif followee_type.lower() == 'organization':
            try:
                followee_profile_id = Organization.objects.get(user_id=followee_user_id).id
            except Organization.DoesNotExist:
                return Follow.objects.none()
        else:
            return Follow.objects.none()
        return Follow.objects.filter(
            followee_content_type=followee_content_type,
            followee_object_id=followee_profile_id
        )

class ListFollowingView(generics.ListAPIView):
    serializer_class = GenericFollowSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        follower_type = self.request.query_params.get('follower_type')
        follower_user_id = self.request.query_params.get('follower_id')  # This is user.id from frontend
        if not follower_type or not follower_user_id:
            return Follow.objects.none()
        follower_content_type = ContentType.objects.get(model=follower_type.lower())
        # Resolve profile id from user id
        if follower_type.lower() == 'student':
            try:
                follower_profile_id = Student.objects.get(user_id=follower_user_id).id
            except Student.DoesNotExist:
                return Follow.objects.none()
        elif follower_type.lower() == 'organization':
            try:
                follower_profile_id = Organization.objects.get(user_id=follower_user_id).id
            except Organization.DoesNotExist:
                return Follow.objects.none()
        else:
            return Follow.objects.none()
        return Follow.objects.filter(
            follower_content_type=follower_content_type,
            follower_object_id=follower_profile_id
        )
logger = logging.getLogger(__name__)

class FeedView(APIView):
    """
    Feed: All posts by students, ordered by trending_score.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        posts_limit = 30
        all_feed_posts = []

        # Get all user IDs that have a Student profile
        student_user_ids_str = get_student_user_ids()  # This returns a list of user IDs as strings
        if not student_user_ids_str:
            logger.info("No student users found for feed.")
            return Response([], status=status.HTTP_200_OK)

        try:
            student_user_ids_for_query = student_user_ids_str[:10]  # Firestore 'in' query limit
            posts_query = db.collection('posts') \
                .where('author_id', 'in', student_user_ids_for_query) \
                .order_by('trending_score', direction=firestore.Query.DESCENDING) \
                    .order_by('timestamp', direction=firestore.Query.DESCENDING) \
                    .limit(posts_limit)

            current_user_id = str(request.user.id)  if request.user.is_authenticated else None

            for doc in posts_query.stream():
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                post_data['has_liked'] = False  # Default to False, will be updated later
                if current_user_id:
                    like_doc_ref = db.collection('posts').document(post_data['id']).collection('likes').document(current_user_id)
                    post_data['has_liked'] = like_doc_ref.get().exists
                all_feed_posts.append(post_data)
        
        
            authors_map = {}
            for user_id in student_user_ids_str:
                author_name = None
                display_name_slug = None
                try:
                    author = User.objects.get(id=user_id)
                    if hasattr(author, 'student'):
                        author_name = author.student.name
                        display_name_slug = getattr(author.student, 'display_name_slug', None)
                    elif hasattr(author, 'organization'):
                        author_name = author.organization.organization_name
                        display_name_slug = getattr(author.organization, 'display_name_slug', None)
                    
                    authors_map[str(author.id)] = {
                    "id": author.id,
                    "email": author.email,
                    "profile_pic_url": author.profile_pic_url,
                    "name": author_name,
                    "display_name_slug": display_name_slug,
                    "is_verified": author.is_verified
                }
                except User.DoesNotExist:
                    continue
                

            serializer = FirestorePostOutputSerializer(all_feed_posts, many=True, context={'authors_map': authors_map})
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error fetching feed posts: {str(e)}")
            return Response({"error": f"Failed to retrieve feed posts: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            posts_ref = db.collection('posts').order_by('timestamp', direction=firestore.Query.DESCENDING)
            docs = posts_ref.stream()
            posts_list = []
            author_ids = set()

            for doc in docs:
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                posts_list.append(post_data)
                if 'author_id' in post_data:
                    author_ids.add(str(post_data['author_id']))

            # Hydrate authors_map with display_name_slug
            authors_from_postgres = User.objects.filter(id__in=author_ids).only('id', 'email', 'profile_pic_url', 'is_verified')
            authors_map = {}
            for author in authors_from_postgres:
                author_name = None
                display_name_slug = None
                if hasattr(author, 'student'):
                    author_name = author.student.name
                    display_name_slug = getattr(author.student, 'display_name_slug', None)
                elif hasattr(author, 'organization'):
                    author_name = author.organization.organization_name
                    display_name_slug = getattr(author.organization, 'display_name_slug', None)

                authors_map[str(author.id)] = {
                    "id": author.id,
                    "email": author.email,
                    "profile_pic_url": author.profile_pic_url,
                    "name": author_name,
                    "display_name_slug": display_name_slug,
                    "is_verified": author.is_verified
                }

            # Add has_liked logic if needed (as you already have)
            if request.user.is_authenticated and posts_list:
                user_id = str(request.user.id)
                for post in posts_list:
                    like_doc_ref = db.collection('posts').document(post['id']).collection('likes').document(user_id)
                    post['has_liked'] = like_doc_ref.get().exists
            
            # print("Author IDs in posts:", [post.get('author_id') for post in posts_list])
            # print("Authors map keys:", list(authors_map.keys()))
            # Pass authors_map to serializer context
            serializer = FirestorePostOutputSerializer(posts_list, many=True, context={'authors_map': authors_map})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to retrieve posts: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        # if not getattr(request.user, 'is_verified', False):
        #     return Response({"error": "You must be a verified user to create posts."}, status=status.HTTP_403_FORBIDDEN)

        serializer = FirestorePostCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            try:
                post_payload = {
                    'author_id': str(request.user.id), # Link to Django User ID
                    # 'author_email': request.user.email, # Denormalize for convenience
                    'content': data['content'],
                    'slug': data.get('slug', ''), # Handle slug generation if needed
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'like_count': 0,
                    'comment_count': 0,
                    'share_count': 0,
                    'media_urls': data.get('media_urls', []), # Handle media URLs if provided
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
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsFirestoreDocOwner]
    authentication_classes = [JWTAuthentication]

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

    def get(self, request, post_id): # post_identifier can be ID or slug
        # Determine if post_identifier is a slug or ID based on your URL pattern
        # For this example, let's assume it's post_id. If using slug, pass is_slug=True
        doc_ref, post_data = self.get_post_doc_and_data(post_id) #, is_slug=True if your URL uses slug)

        if post_data:
            post_data['id'] = doc_ref.id

            # Hydrate author info
            author_id = str(post_data.get('author_id'))
            author_info = None
            if author_id:
                try:
                    author = User.objects.only('id', 'email', 'profile_pic_url', 'is_verified').get(id=author_id)
                    author_name = None
                    if hasattr(author, 'student') and author.student.name:
                        author_name = author.student.name
                    elif hasattr(author, 'organization') and author.organization.organization_name:
                        author_name = author.organization.organization_name

                    author_info = {
                        "id": author.id,
                        "email": author.email,
                        "profile_pic_url": author.profile_pic_url,
                        "name": author_name,
                        "is_verified": author.is_verified if hasattr(author, 'is_verified') else False,
                    }
                except User.DoesNotExist:
                    author_info = {
                        "id": author_id,
                        "email": None,
                        "profile_pic_url": None,
                        "name": None,
                        "is_verified": None
                    }
            else:
                author_info = None
            post_data['author_name'] = author_info['name'] if author_info else None
            post_data['author_profile_pic_url'] = author_info['profile_pic_url'] if author_info else None

            # Add has_liked
            post_data['has_liked'] = False
            if request.user.is_authenticated:
                user_id = str(request.user.id)
                like_doc_ref = db.collection('posts').document(post_data['id']).collection('likes').document(user_id)
                post_data['has_liked'] = like_doc_ref.get().exists

            return Response(post_data, status=status.HTTP_200_OK)
        return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, post_id):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        doc_ref, post_data = self.get_post_doc_and_data(post_id)
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

    def delete(self, request, post_id):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        doc_ref, post_data = self.get_post_doc_and_data(post_id)
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
    Create a new comment for a post in Firestore using a transactional decorator.
    URL: /api/posts/{post_id}/comments/
    """
    permission_classes = [permissions.IsAuthenticated, IsVerified]
    authentication_classes = [JWTAuthentication]

    def post(self, request, post_id): # Get post_id from URL
        user_id = str(request.user.id) # Ensure user ID is a string for Firestore

        # 1. Initial Post Existence Check (outside transaction for quick feedback)
        post_ref = db.collection('posts').document(post_id)
        post_doc_snapshot = post_ref.get() # Get a snapshot for initial check
        if not post_doc_snapshot.exists:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = FirestoreCommentSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            comment_payload = {
                'post_id': post_id, # Redundant if in subcollection, but useful for queries
                'author_id': user_id,
                'author_username': request.user.email, # Denormalize for convenience
                'text': data['text'],
                'timestamp': firestore.SERVER_TIMESTAMP,
                # Add other fields like parent_comment_id for replies, etc.
            }

            try:
                # Define the transactional function
                # It takes the transaction object and any other arguments it needs
                @firestore.transactional
                def create_comment_and_increment_count(transaction, current_post_ref, payload):
                    # Re-read post document within the transaction to ensure latest state
                    # This read helps Firestore detect conflicts and retry the transaction if needed.
                    current_post_doc_in_tx = current_post_ref.get(transaction=transaction)
                    if not current_post_doc_in_tx.exists:
                        # If the post was deleted concurrently, this transaction will fail.
                        raise ValueError("Post not found during transaction.")

                    # Add the new comment document to the subcollection
                    # Get a new auto-ID document reference for the comment
                    new_comment_ref = current_post_ref.collection('comments').document()
                    transaction.set(new_comment_ref, payload)

                    # Increment the comment_count on the parent Post document
                    transaction.update(current_post_ref, {
                        'comment_count': firestore.Increment(1)
                    })
                    
                    return new_comment_ref.id # Return the ID of the newly created comment

                # Run the transactional function.
                # It's called like a regular function, and db.transaction() is implicitly passed.
                # db.transaction() will retry the function automatically on contention.
                new_comment_id = create_comment_and_increment_count(db.transaction(), post_ref, comment_payload)
                
                # After successful transaction, fetch the created comment data for response
                created_comment_doc = post_ref.collection('comments').document(new_comment_id).get()
                created_comment_data = created_comment_doc.to_dict()
                created_comment_data['id'] = new_comment_id
                
                return Response(created_comment_data, status=status.HTTP_201_CREATED)

            except ValueError as ve: # Catch explicit errors from inside the transaction function
                return Response({"error": f"Transaction failed: {str(ve)}"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                # Catch any other Firestore errors or general exceptions
                # print(f"Error creating comment with transaction: {e}") # Log the full error for debugging
                return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentListFirestoreView(APIView):
    """
    List comments for a specific post.
    URL: /api/posts/{post_id}/comments/
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get(self, request, post_id):
        post_ref = db.collection('posts').document(post_id)
        if not post_ref.get().exists:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            comments_ref = post_ref.collection('comments').order_by('timestamp', direction=firestore.Query.ASCENDING)
            docs = comments_ref.stream()
            comments_list = []
            author_ids = set()
            for doc in docs:
                comment_data = doc.to_dict()
                comment_data['id'] = doc.id
                comments_list.append(comment_data)
                if 'author_id' in comment_data:
                    author_ids.add(str(comment_data['author_id']))

            # Hydrate authors_map
            authors_from_postgres = User.objects.filter(id__in=author_ids).only('id', 'email', 'profile_pic_url', 'is_verified')
            authors_map = {}
            for author in authors_from_postgres:
                author_name = None
                display_name_slug = None
                if hasattr(author, 'student'):
                    author_name = author.student.name
                    display_name_slug = getattr(author.student, 'display_name_slug', None)
                elif hasattr(author, 'organization'):
                    author_name = author.organization.organization_name
                    display_name_slug = getattr(author.organization, 'display_name_slug', None)
                authors_map[str(author.id)] = {
                    "id": author.id,
                    "name": author_name,
                    "display_name_slug": display_name_slug,
                    "profile_pic_url": author.profile_pic_url,
                    "is_verified": author.is_verified if hasattr(author, 'is_verified') else False,
                }

            serializer = FirestoreCommentSerializer(comments_list, many=True, context={'authors_map': authors_map})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to retrieve comments: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


##
## Like Views (Firestore)
##
# class LikeToggleFirestoreView(APIView):
#     """
#     Like or unlike a post. A single endpoint to toggle the like status.
#     URL: /api/posts/{post_id}/like/
#     """
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, post_id): # post_id from URL
#         user_id = str(request.user.id)
#         post_ref = db.collection('posts').document(post_id)
#         like_ref = post_ref.collection('likes').document(user_id) # Document ID is the user's ID

#         try:
#             post_doc = post_ref.get()
#             if not post_doc.exists:
#                 return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

#             like_doc = like_ref.get()
            
#             # Use a Firestore transaction to ensure atomic like/unlike and count update
#             @firestore.transactional
#             def toggle_like_transaction(transaction, current_post_ref, current_like_ref, current_like_exists):
#                 if current_like_exists:
#                     transaction.delete(current_like_ref)
#                     transaction.update(current_post_ref, {'like_count': firestore.Increment(-1)})
#                     return False # Unliked
#                 else:
#                     transaction.set(current_like_ref, {'liked_at': firestore.SERVER_TIMESTAMP})
#                     transaction.update(current_post_ref, {'like_count': firestore.Increment(1)})
#                     return True # Liked

#             transaction = db.transaction()
#             liked_now = toggle_like_transaction(transaction, post_ref, like_ref, like_doc.exists)

#             if liked_now:
#                 return Response({"message": "Post liked successfully."}, status=status.HTTP_201_CREATED)
#             else:
#                 return Response({"message": "Post unliked successfully."}, status=status.HTTP_200_OK) # Or 204 if you prefer

#         except Exception as e:
#             return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class LikeToggleFirestoreView(APIView):
    """
    Like or unlike a post. A single endpoint to toggle the like status.
    URL: /api/posts/{post_id}/like/
    """
    permission_classes = [permissions.IsAuthenticated, IsVerified] # Ensure user is authenticated and verified
    authentication_classes = [JWTAuthentication]

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
                # Define the weight for a like in the trending score
                LIKE_TREND_WEIGHT = 1 

                if current_like_exists:
                    transaction.delete(current_like_ref)
                    transaction.update(current_post_ref, {
                        'like_count': firestore.Increment(-1),
                        'trending_score': firestore.Increment(-LIKE_TREND_WEIGHT), # Decrement trending score
                        'last_engagement_at': firestore.SERVER_TIMESTAMP # Update last engagement time
                    })
                    return False # Unliked
                else:
                    transaction.set(current_like_ref, {'liked_at': firestore.SERVER_TIMESTAMP})
                    transaction.update(current_post_ref, {
                        'like_count': firestore.Increment(1),
                        'trending_score': firestore.Increment(LIKE_TREND_WEIGHT), # Increment trending score
                        'last_engagement_at': firestore.SERVER_TIMESTAMP # Update last engagement time
                    })
                    return True # Liked

            transaction = db.transaction()
            liked_now = toggle_like_transaction(transaction, post_ref, like_ref, like_doc.exists)

            if liked_now:
                return Response({"message": "Post liked successfully."}, status=status.HTTP_201_CREATED)
            else:
                return Response({"message": "Post unliked successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            # It's good practice to log the full exception here for debugging
            logging.error(f"Error toggling like for post {post_id}: {e}")
            return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LikeListFirestoreView(APIView):
    """
    List all likes for a specific post from Firestore.
    This view returns basic like information directly from Firestore,
    without hydrating user details from PostgreSQL.
    URL: /api/posts/{post_id}/likes/
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get(self, request, post_id):
        post_ref = db.collection('posts').document(post_id)
        # Check if the post itself exists
        if not post_ref.get().exists:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Reference to the 'likes' subcollection of the specific post
            likes_ref = post_ref.collection('likes').order_by('liked_at', direction=firestore.Query.ASCENDING)
            docs = likes_ref.stream() # Get all like documents

            raw_likes_list = []
            for doc in docs:
                like_data = doc.to_dict()
                
                # Add the Firestore document ID to the dictionary.
                # Since you're likely using the user_id as the document ID for a like,
                # 'id' will be the user_id. We also explicitly set 'user_id' in the dict
                # to match the serializer's expectation clearly.
                like_data['id'] = doc.id
                like_data['user_id'] = doc.id # The user_id is the document ID of the like

                # Add the post_id from the URL context, as it's not stored in the 'like' document itself
                # if the 'likes' are just a subcollection with user_id and liked_at.
                like_data['post_id'] = post_id 
                
                raw_likes_list.append(like_data)

            # Serialize the data. 'many=True' because we are serializing a list.
            serializer = FirestoreLikeOutputSerializer(raw_likes_list, many=True)
            
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            # Catch any other potential errors during Firestore interaction
            return Response({"error": f"Failed to retrieve likes: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class TrendingPostsFirestoreView(generics.ListAPIView):
#     """
#     Retrieve a list of trending posts from Firestore.
#     Trending is based on a 'trending_score' field and filtered by recent engagement.
#     """
#     permission_classes = [permissions.AllowAny] 
#     serializer_class = FirestorePostOutputSerializer # Use the serializer for output formatting

#     def get_queryset(self):
#         posts_ref = db.collection('posts')

#         # --- Define the time window for "recent" engagement ---
#         # Get posts with engagement in the last 7 days.
#         # This value can be made configurable (e.g., via query parameters in a more complex API)
#         RECENT_ENGAGEMENT_DAYS = 7 
        
#         # Calculate the cutoff datetime. Always use UTC for consistency with Firestore timestamps.
#         now_utc = datetime.now(timezone.utc)
#         from_datetime_utc = now_utc - timedelta(days=RECENT_ENGAGEMENT_DAYS)

#         logging.info(f"Fetching trending posts engaged since: {from_datetime_utc.isoformat()}")

#         # ----------------------------------------------------------------------
#         # Firestore Query Construction:
#         # 1. Filter by recent engagement: `where('last_engagement_at', '>=', from_datetime_utc)`
#         # 2. Order by recency: `order_by('last_engagement_at', direction=firestore.Query.DESCENDING)`
#         # 3. Order by trending score (secondary sort): `order_by('trending_score', direction=firestore.Query.DESCENDING)`
#         #
#         # IMPORTANT: For this combined query, you MUST create a composite index in Firestore.
#         # The required index will be on (last_engagement_at ASC, trending_score DESC).
#         # If you get a Firestore error about a "missing index", follow the URL provided
#         # in the error message to create it in the Firebase console.
#         # ----------------------------------------------------------------------
        
#         query = posts_ref.where('last_engagement_at', '>=', from_datetime_utc) \
#                          .order_by('last_engagement_at', direction=firestore.Query.DESCENDING) \
#                          .order_by('trending_score', direction=firestore.Query.DESCENDING) \
#                          .limit(20) # Limit the number of trending posts returned (e.g., top 20)

#         try:
#             docs = query.stream()
#             # Convert Firestore documents to a list of dictionaries for the serializer
#             posts_list = []
#             for doc in docs:
#                 post_data = doc.to_dict()
#                 post_data['id'] = doc.id # Add the document ID to the dictionary
#                 posts_list.append(post_data)
#             return posts_list # Return a list of dicts
#         except Exception as e:
#             logging.error(f"Failed to fetch trending posts from Firestore: {e}", exc_info=True)
#             # Depending on your error handling, you might return an empty list or raise an APIException
#             return [] 

#     def list(self, request, *args, **kwargs):
#         posts_data = self.get_queryset()

#         # Add has_liked status (already in your code)
#         for post in posts_data:
#             post_id = post.get('id')
#             if request.user.is_authenticated:
#                 user_id = str(request.user.id)
#                 try:
#                     like_doc = db.collection('posts').document(post_id).collection('likes').document(user_id).get()
#                     post['has_liked'] = like_doc.exists
#                 except Exception as e:
#                     logging.warning(f"Error checking like status for post {post_id}: {e}")
#                     post['has_liked'] = False
#             else:
#                 post['has_liked'] = False

#         # --- Hydrate author info ---
#         author_ids = list(set(str(post['author_id']) for post in posts_data if 'author_id' in post))
#         authors_from_postgres = User.objects.filter(id__in=author_ids).only('id', 'email', 'profile_pic_url', 'is_verified')
#         authors_map = {}
#         for author in authors_from_postgres:
#             author_name = None
#             display_name_slug = None
#             if hasattr(author, 'student'):
#                 author_name = author.student.name
#                 display_name_slug = getattr(author.student, 'display_name_slug', None)
#             elif hasattr(author, 'organization'):
#                 author_name = author.organization.organization_name
#                 display_name_slug = getattr(author.organization, 'display_name_slug', None)

#             authors_map[str(author.id)] = {
#                 "id": author.id,
#                 "email": author.email,
#                 "profile_pic_url": author.profile_pic_url,
#                 "name": author_name,
#                 "display_name_slug": display_name_slug,
#                 "is_verified": author.is_verified if hasattr(author, 'is_verified') else False,
#             }

#         # --- Serialize with authors_map ---
#         serializer = self.get_serializer(posts_data, many=True, context={'authors_map': authors_map})
#         return Response(serializer.data, status=status.HTTP_200_OK)

class ExclusiveOrgsRecentPostsView(APIView):
    """
    List recent posts from organizations with exclusive=True.
    Only posts authored by exclusive organizations are included.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        posts_limit = 20

        # 1. Get all exclusive organizations' user IDs
        exclusive_org_user_ids_str = get_exclusive_org_user_ids()

        if not exclusive_org_user_ids_str:
            return Response([], status=200)

        # 2. Query Firestore for posts from exclusive orgs
        posts = []
        try:
            # Firestore 'in' queries are limited to 10 items
            org_user_ids_for_query = exclusive_org_user_ids_str[:10]
            query = db.collection('posts') \
                .where('author_id', 'in', org_user_ids_for_query) \
                .order_by('timestamp', direction=firestore.Query.DESCENDING) \
                .limit(posts_limit)
            
            current_user_id = str(request.user.id) if request.user.is_authenticated else None
    
            for doc in query.stream():
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                post_data['has_liked'] = False
                if current_user_id:
                    like_doc_ref = db.collection('posts').document(post_data['id']).collection('likes').document(current_user_id)
                    post_data['has_liked'] = like_doc_ref.get().exists
                # post_data['is_shared'] = False  # Mark as original post
                posts.append(post_data)
            
            # Hydrate author info for exclusive orgs
            authors_map = {}
            for user_id in exclusive_org_user_ids_str:
                try:
                    author = User.objects.only('id', 'email', 'profile_pic_url', 'is_verified').get(id=user_id)
                    author_name = author.organization.organization_name

                    authors_map[str(author.id)] = {
                        "id": author.id,
                        "email": author.email,
                        "profile_pic_url": author.profile_pic_url,
                        "name": author_name,
                        "is_verified": author.is_verified,
                    }
                except User.DoesNotExist:
                    pass
            
            serializer = FirestorePostOutputSerializer(posts, many=True, context={'authors_map': authors_map})
            return Response(serializer.data, status=status.HTTP_200_OK)
    
        except Exception as e:
            logger.error(f"Error fetching exclusive org posts: {e}", exc_info=True)
            return Response({"detail": "Error fetching posts."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserPostsFirestoreView(APIView):
    """
    List all posts by a specific user identified by their user_id, including shares.
    URL: /api/users/{user_id}/posts/
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsVerified]
    authentication_classes = [JWTAuthentication]

    def get(self, request, user_id):
        target_user_id = user_id

        try:
            posts_ref = db.collection('posts')
            posts_query = posts_ref.where('author_id', '==', target_user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
            
            posts_list = []
            current_user_id = str(request.user.id) if request.user.is_authenticated else None

            for doc in posts_query:
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                post_data['has_liked'] = False
                if current_user_id:
                    like_doc_ref = db.collection('posts').document(post_data['id']).collection('likes').document(current_user_id)
                    post_data['has_liked'] = like_doc_ref.get().exists
                post_data['is_shared'] = False  # Mark as original post
                posts_list.append(post_data)

            # --- Add shares made by this user ---
            shares_query = db.collection('shares').where('shared_by_id', '==', target_user_id).order_by('shared_at', direction=firestore.Query.DESCENDING).stream()
            shares_map = {}
            for share_doc in shares_query:
                share_data = share_doc.to_dict()
                original_post_id = share_data.get('original_post_id')
                if original_post_id:
                    # Add this share to the shares_map for the original post
                    if original_post_id not in shares_map:
                        shares_map[original_post_id] = []
                    # Optionally, serialize with FirestoreShareOutputSerializer
                    share_data['id'] = share_doc.id
                    shares_map[original_post_id].append(share_data)

                    # Also add the shared post to the posts_list if you want to show it in the user's activity
                    original_post_ref = db.collection('posts').document(original_post_id)
                    original_post_doc = original_post_ref.get()
                    if original_post_doc.exists:
                        post_data = original_post_doc.to_dict()
                        post_data['id'] = original_post_doc.id
                        post_data['is_shared'] = True
                        post_data['shared_by_id'] = share_data.get('shared_by_id')
                        post_data['shared_at'] = share_data.get('shared_at')
                        post_data['has_liked'] = False
                        if current_user_id:
                            like_doc_ref = db.collection('posts').document(post_data['id']).collection('likes').document(current_user_id)
                            post_data['has_liked'] = like_doc_ref.get().exists
                        posts_list.append(post_data)

            # Hydrate author info for the target user
            authors_map = {}
            try:
                author = User.objects.only('id', 'email', 'profile_pic_url', 'is_verified').get(id=target_user_id)
                author_name = None
                if hasattr(author, 'student') and author.student.name:
                    author_name = author.student.name
                elif hasattr(author, 'organization') and author.organization.organization_name:
                    author_name = author.organization.organization_name

                authors_map[str(author.id)] = {
                    "id": author.id,
                    "email": author.email,
                    "profile_pic_url": author.profile_pic_url,
                    "name": author_name,
                    "is_verified": author.is_verified,
                }
            except User.DoesNotExist:
                pass

            # Sort posts by timestamp or shared_at (most recent first)
            posts_list.sort(key=lambda x: x.get('shared_at') or x.get('timestamp'), reverse=True)

            serializer = FirestorePostOutputSerializer(
                posts_list, many=True, context={'authors_map': authors_map, 'shares_map': shares_map}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            # print(f"Error retrieving user posts: {e}")
            return Response({"error": f"Failed to retrieve posts for user: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WhoToFollowView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        user = request.user
        try:
            student = Student.objects.select_related('user').get(user=user)
            student_ct = ContentType.objects.get(model='student')
            org_ct = ContentType.objects.get(model='organization')

            # print("Current user:", user)
            # print("Current student id:", student.id)
            # print("student_ct.id:", student_ct.id)
            # print("org_ct.id:", org_ct.id)

            follows = Follow.objects.filter(
                follower_content_type=student_ct,
                follower_object_id=student.id
            )
            followed_student_ids = set(int(x) for x in follows.filter(followee_content_type=student_ct).values_list('followee_object_id', flat=True))
            followed_org_ids = set(int(x) for x in follows.filter(followee_content_type=org_ct).values_list('followee_object_id', flat=True))

            keywords = []
            if student.department:
                keywords.append(student.department)
            if student.faculty:
                keywords.append(student.faculty)
            if student.religion:
                keywords.append(student.religion)

            student_query = Q()
            for kw in keywords:
                student_query |= Q(department__icontains=kw) | Q(faculty__icontains=kw) | Q(religion__icontains=kw)
            recommended_students = Student.objects.filter(student_query).exclude(
                id__in=followed_student_ids
            ).exclude(user=user)[:20]

            org_query = Q()
            for kw in keywords:
                org_query |= Q(organization_name__icontains=kw) | Q(user__bio__icontains=kw)
            recommended_orgs = Organization.objects.filter(org_query).exclude(
                id__in=followed_org_ids
            )[:20]

            exclusive_orgs = Organization.objects.filter(exclusive=True).exclude(id__in=followed_org_ids)

            # print("followed_student_ids:", followed_student_ids)
            # print("followed_org_ids:", followed_org_ids)
            # print("Recommended org IDs:", [org.id for org in (recommended_orgs | exclusive_orgs).distinct()])

            users_data = [
                {
                    "type": "student",
                    "id": s.id,
                    "user_id": s.user.id,
                    "name": s.name,
                    "display_name_slug": getattr(s, "display_name_slug", None),
                    "profile_pic_url": getattr(s.user, "profile_pic_url", None),
                    "bio": getattr(s.user, "bio", None),
                    "is_following": s.id in followed_student_ids,
                    "is_verified": s.user.is_verified if hasattr(s, 'user') else False,
                }
                for s in recommended_students
            ] + [
                {
                    "type": "organization",
                    "id": org.id,
                    "user_id": org.user.id,
                    "name": org.organization_name,
                    "display_name_slug": org.display_name_slug,
                    "profile_pic_url": getattr(org.user, "profile_pic_url", None),
                    "bio": org.user.bio if hasattr(org, 'user') else None,
                    "exclusive": org.exclusive,
                    "is_following": org.id in followed_org_ids,
                    "is_verified": org.user.is_verified if hasattr(org, 'user') else False,
                }
                for org in (recommended_orgs | exclusive_orgs).distinct()
            ]

            users_data = users_data[:20]

            return Response(users_data, status=status.HTTP_200_OK)
        except Student.DoesNotExist:
            return Response({"error": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

class VerifiedOrgBadge(APIView):
    """Checks if the Organization is Exclusive and Verified"""
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        user = request.user
        try:
            org = Organization.objects.get(user=user)
            if org.exclusive and org.user.is_verified:
                return Response({"is_verified": True}, status=status.HTTP_200_OK)
            else:
                return Response({"is_verified": False}, status=status.HTTP_200_OK)
        except Organization.DoesNotExist:
            return Response({"error": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)
