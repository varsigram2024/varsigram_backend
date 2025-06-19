from rest_framework import generics, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Exists, OuterRef, Count, Q
from django.http import Http404
from django.contrib.auth import get_user_model
from firebase_admin import firestore
from postMang.apps import db  # Import the Firestore client from the app config
from .models import ( Post, Comment, Like, Share,
                     User, Follow, Student, Organization)
from .serializer import FirestoreCommentSerializer, FirestoreLikeOutputSerializer, FirestorePostCreateSerializer, FirestorePostUpdateSerializer, FirestorePostOutputSerializer, FollowingSerializer, FollowSerializer, FirestoreShareOutputSerializer
from .utils import IsOwnerOrReadOnly
from itertools import chain
import logging
from datetime import datetime, timezone, timedelta

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

class FollowOrganizationView(generics.CreateAPIView):
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        organization_display_name = self.kwargs['display_name_slug']
        try:
            organization = Organization.objects.get(display_name_slug=organization_display_name)
            student = Student.objects.get(user=self.request.user)

            if Follow.objects.filter(student=student, organization=organization).exists():
                return Response({"message": "You are already following this organization."}, status=status.HTTP_400_BAD_REQUEST)

            serializer.save(student=student, organization=organization)
            return Response({"message": "Following successful!"}, status=status.HTTP_201_CREATED)

        except Organization.DoesNotExist:
            return Response({"message": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)
        except Student.DoesNotExist:
            return Response({"message": "Only students can follow organizations."}, status=status.HTTP_400_BAD_REQUEST)

class UnfollowOrganizationView(generics.DestroyAPIView):
    """ Unfollow an organization """
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        organization_display_name_slug = self.kwargs['display_name_slug']
        try:
            organization = Organization.objects.get(display_name_slug=organization_display_name_slug)
            student = Student.objects.get(user=self.request.user)
            return Follow.objects.get(student=student, organization=organization)
        except Organization.DoesNotExist:
            return None
        except Follow.DoesNotExist:
            return None


class FollowingOrganizationsView(generics.ListAPIView):
    """ List organizations followed by a student """
    serializer_class = FollowingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        try:
            student = Student.objects.get(user=self.request.user)
            return Follow.objects.filter(student=student)
        except Student.DoesNotExist:
            return Follow.objects.none()

class OrganizationFollowersView(generics.ListAPIView):
    """ List followers of an organization """
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        organization_display_name_slug = self.kwargs['display_name_slug']
        try:
            organization = Organization.objects.get(display_name_slug=organization_display_name_slug)
            return Follow.objects.filter(organization=organization)
        except Organization.DoesNotExist:
            return Follow.objects.none()

logger = logging.getLogger(__name__)
class FeedView(generics.ListAPIView):
    """
    List posts in the personalized feed based on user's follows and profile attributes,
    and potentially shared posts.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FirestorePostOutputSerializer # Default serializer

    def get_serializer_class(self):
        # This part handles 'shared' query param if you have a separate ShareSerializer
        if 'shared' in self.request.query_params:
            return FirestoreShareOutputSerializer # Make sure this serializer works with your Share data structure
        return FirestorePostOutputSerializer

    def get_queryset(self): 
        user = self.request.user
        shared_param = self.request.query_params.get('shared', None)
        posts_limit = 20
        
        last_created_at_str = self.request.query_params.get('last_created_at')
        last_post_id = self.request.query_params.get('last_post_id')

        start_after_values = None
        if last_created_at_str and last_post_id:
            try:
                start_after_created_at = datetime.fromisoformat(last_created_at_str.replace('Z', '+00:00'))
                start_after_values = (start_after_created_at, last_post_id) 
            except ValueError:
                logger.warning(f"Invalid last_created_at format: {last_created_at_str}")
                start_after_values = None

        all_feed_posts = {} 

        try:
            student = Student.objects.select_related('user').get(user=user)
            user_id_postgres = str(user.id) 

            followed_org_user_ids = list(Follow.objects.filter(student=student).values_list('organization__user__id', flat=True))
            if followed_org_user_ids:
                logger.info(f"User {user_id_postgres} follows organizations: {followed_org_user_ids}")
                if len(followed_org_user_ids) > 10:
                    logger.warning("Too many followed organizations for single Firestore 'in' query. Limiting to first 10.")
                    followed_org_user_ids = followed_org_user_ids[:10] 
                
                try:
                    followed_posts_query = db.collection('posts') \
                                             .where('author_id', 'in', [str(uid) for uid in followed_org_user_ids]) \
                                             .order_by('created_at', direction=firestore.Query.DESCENDING) # Order by created_at for feed
                                             
                    if start_after_values:
                        followed_posts_query = followed_posts_query.start_after(start_after_values[0], start_after_values[1])
                    followed_posts_query = followed_posts_query.limit(posts_limit)

                    for doc in followed_posts_query.stream():
                        post_data = doc.to_dict()
                        post_data['id'] = doc.id
                        all_feed_posts[doc.id] = post_data
                except Exception as e:
                    logger.error(f"Error fetching followed organization posts for user {user_id_postgres}: {e}", exc_info=True)


            eligible_user_ids = set() 

            if student.department:
                dept_users = User.objects.filter(student__department=student.department).values_list('id', flat=True)
                eligible_user_ids.update(dept_users)
                logger.info(f"Found {len(dept_users)} users in same department for user {user_id_postgres}.")

            if student.faculty:
                faculty_users = User.objects.filter(student__faculty=student.faculty).values_list('id', flat=True)
                eligible_user_ids.update(faculty_users)
                logger.info(f"Found {len(faculty_users)} users in same faculty for user {user_id_postgres}.")

            if student.religion:
                religion_users = User.objects.filter(student__religion=student.religion).values_list('id', flat=True)
                eligible_user_ids.update(religion_users)
                logger.info(f"Found {len(religion_users)} users with same religion for user {user_id_postgres}.")
            
            eligible_user_ids.discard(user.id) 

            eligible_user_ids_list = [str(uid) for uid in list(eligible_user_ids)]
            if eligible_user_ids_list:
                if len(eligible_user_ids_list) > 10:
                    logger.warning("Too many eligible users for single Firestore 'in' query. Limiting to first 10.")
                    eligible_user_ids_list = eligible_user_ids_list[:10] 

                try:
                    attribute_posts_query = db.collection('posts') \
                                            .where('author_id', 'in', eligible_user_ids_list) \
                                            .order_by('created_at', direction=firestore.Query.DESCENDING)
                    
                    if start_after_values:
                        attribute_posts_query = attribute_posts_query.start_after(start_after_values[0], start_after_values[1])
                    attribute_posts_query = attribute_posts_query.limit(posts_limit)

                    for doc in attribute_posts_query.stream():
                        post_data = doc.to_dict()
                        post_data['id'] = doc.id
                        all_feed_posts[doc.id] = post_data
                except Exception as e:
                    logger.error(f"Error fetching attribute-based posts for user {user_id_postgres}: {e}", exc_info=True)


            if shared_param == 'true':
                try:
                    shared_posts_query = db.collection('shares') \
                                           .where('shared_by_id', '==', user_id_postgres) \
                                           .order_by('shared_at', direction=firestore.Query.DESCENDING)
                    
                    if start_after_values: 
                        shared_posts_query = shared_posts_query.start_after(start_after_values[0], start_after_values[1])
                    shared_posts_query = shared_posts_query.limit(posts_limit)

                    for share_doc in shared_posts_query.stream():
                        share_data = share_doc.to_dict()
                        original_post_id = share_data.get('original_post_id')
                        if original_post_id and original_post_id not in all_feed_posts:
                            original_post_ref = db.collection('posts').document(original_post_id)
                            original_post_doc = original_post_ref.get()
                            if original_post_doc.exists:
                                post_data = original_post_doc.to_dict()
                                post_data['id'] = original_post_doc.id
                                post_data['is_shared'] = True 
                                post_data['shared_by_id'] = share_data.get('shared_by_id')
                                post_data['shared_at'] = share_data.get('shared_at')
                                all_feed_posts[original_post_doc.id] = post_data
                            else:
                                logger.warning(f"Shared post {original_post_id} not found for share {share_doc.id}")
                except Exception as e:
                    logger.error(f"Error fetching shared posts for user {user_id_postgres}: {e}", exc_info=True)

            if not all_feed_posts:
                logger.info(f"No personalized feed posts found for user {user_id_postgres}. Fetching general recent posts.")
                general_posts_query = db.collection('posts') \
                                        .order_by('created_at', direction=firestore.Query.DESCENDING)
                
                if start_after_values:
                    general_posts_query = general_posts_query.start_after(start_after_values[0], start_after_values[1])
                general_posts_query = general_posts_query.limit(posts_limit)

                for doc in general_posts_query.stream():
                    post_data = doc.to_dict()
                    post_data['id'] = doc.id
                    all_feed_posts[doc.id] = post_data

        except Student.DoesNotExist:
            logger.info(f"Student profile not found for user {user.id}. Falling back to general recent posts.")
            general_posts_query = db.collection('posts') \
                                    .order_by('created_at', direction=firestore.Query.DESCENDING)
            
            if start_after_values:
                general_posts_query = general_posts_query.start_after(start_after_values[0], start_after_values[1])
            general_posts_query = general_posts_query.limit(posts_limit)

            for doc in general_posts_query.stream():
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                all_feed_posts[doc.id] = post_data
        except Exception as e:
            logger.error(f"Unexpected error during feed generation for user {user.id}: {e}", exc_info=True)
            return []


        final_posts = list(all_feed_posts.values())
        final_posts.sort(key=lambda x: x.get('created_at', datetime.min.replace(tzinfo=timezone.utc)), reverse=True)

        user_id_str = str(user.id)
        for post in final_posts:
            post_id = post.get('id')
            try:
                like_doc = db.collection('posts').document(post_id).collection('likes').document(user_id_str).get()
                post['has_liked'] = like_doc.exists
            except Exception as e:
                logger.warning(f"Error checking like status for post {post_id} by user {user_id_str}: {e}")
                post['has_liked'] = False
        
        return final_posts
    
    def list(self, request, *args, **kwargs):
        posts_data = self.get_queryset()

        author_ids = list(set(str(post['author_id']) for post in posts_data if 'author_id' in post))
        authors_from_postgres = User.objects.filter(id__in=author_ids).only('id', 'email', 'profile_pic_url')
        authors_map = {}
        for author in authors_from_postgres:
            display_name_slug = None
            if hasattr(author, 'student') and author.student.display_name_slug:
                display_name_slug = author.student.display_name_slug
            elif hasattr(author, 'organization') and author.organization.display_name_slug:
                display_name_slug = author.organization.display_name_slug

            authors_map[str(author.id)] = {
                "id": author.id,
                "email": author.email,
                "profile_pic_url": author.profile_pic_url,
                "display_name_slug": display_name_slug,
            }

        serializer = self.get_serializer(posts_data, many=True, context={'authors_map': authors_map})
        return Response(serializer.data, status=status.HTTP_200_OK)


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
            authors_from_postgres = User.objects.filter(id__in=author_ids).only('id', 'email', 'profile_pic_url')
            authors_map = {}
            for author in authors_from_postgres:
                display_name_slug = None
                if hasattr(author, 'student') and author.student.display_name_slug:
                    display_name_slug = author.student.display_name_slug
                elif hasattr(author, 'organization') and author.organization.display_name_slug:
                    display_name_slug = author.organization.display_name_slug

                authors_map[str(author.id)] = {
                    "id": author.id,
                    "email": author.email,
                    "profile_pic_url": author.profile_pic_url,
                    "display_name_slug": display_name_slug,
                }

            # Add has_liked logic if needed (as you already have)
            if request.user.is_authenticated and posts_list:
                user_id = str(request.user.id)
                for post in posts_list:
                    like_doc_ref = db.collection('posts').document(post['id']).collection('likes').document(user_id)
                    post['has_liked'] = like_doc_ref.get().exists
            
            print("Author IDs in posts:", [post.get('author_id') for post in posts_list])
            print("Authors map keys:", list(authors_map.keys()))
            # Pass authors_map to serializer context
            serializer = FirestorePostOutputSerializer(posts_list, many=True, context={'authors_map': authors_map})
            return Response(serializer.data, status=status.HTTP_200_OK)
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
                    'author_username': request.user.email, # Denormalize for convenience
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
                    author = User.objects.only('id', 'email', 'profile_pic_url').get(id=author_id)
                    display_name_slug = None
                    if hasattr(author, 'student') and author.student.display_name_slug:
                        display_name_slug = author.student.display_name_slug
                    elif hasattr(author, 'organization') and author.organization.display_name_slug:
                        display_name_slug = author.organization.display_name_slug

                    author_info = {
                        "id": author.id,
                        "email": author.email,
                        "profile_pic_url": author.profile_pic_url,
                        "display_name_slug": display_name_slug,
                    }
                except User.DoesNotExist:
                    author_info = {
                        "id": author_id,
                        "email": None,
                        "profile_pic_url": None,
                        "display_name_slug": None,
                    }
            else:
                author_info = None

            post_data['author_display_name_slug'] = author_info['display_name_slug'] if author_info else None
            post_data['author_profile_pic_url'] = author_info['profile_pic_url'] if author_info else None

            # Add has_liked
            post_data['has_liked'] = False
            if request.user.is_authenticated:
                user_id = str(request.user.id)
                like_doc_ref = db.collection('posts').document(post_data['id']).collection('likes').document(user_id)
                post_data['has_liked'] = like_doc_ref.get().exists

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
    Create a new comment for a post in Firestore using a transactional decorator.
    URL: /api/posts/{post_id}/comments/
    """
    permission_classes = [permissions.IsAuthenticated]

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
                print(f"Error creating comment with transaction: {e}") # Log the full error for debugging
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


class TrendingPostsFirestoreView(generics.ListAPIView):
    """
    Retrieve a list of trending posts from Firestore.
    Trending is based on a 'trending_score' field and filtered by recent engagement.
    """
    permission_classes = [permissions.AllowAny] 
    serializer_class = FirestorePostOutputSerializer # Use the serializer for output formatting

    def get_queryset(self):
        posts_ref = db.collection('posts')

        # --- Define the time window for "recent" engagement ---
        # Get posts with engagement in the last 7 days.
        # This value can be made configurable (e.g., via query parameters in a more complex API)
        RECENT_ENGAGEMENT_DAYS = 7 
        
        # Calculate the cutoff datetime. Always use UTC for consistency with Firestore timestamps.
        now_utc = datetime.now(timezone.utc)
        from_datetime_utc = now_utc - timedelta(days=RECENT_ENGAGEMENT_DAYS)

        logging.info(f"Fetching trending posts engaged since: {from_datetime_utc.isoformat()}")

        # ----------------------------------------------------------------------
        # Firestore Query Construction:
        # 1. Filter by recent engagement: `where('last_engagement_at', '>=', from_datetime_utc)`
        # 2. Order by recency: `order_by('last_engagement_at', direction=firestore.Query.DESCENDING)`
        # 3. Order by trending score (secondary sort): `order_by('trending_score', direction=firestore.Query.DESCENDING)`
        #
        # IMPORTANT: For this combined query, you MUST create a composite index in Firestore.
        # The required index will be on (last_engagement_at ASC, trending_score DESC).
        # If you get a Firestore error about a "missing index", follow the URL provided
        # in the error message to create it in the Firebase console.
        # ----------------------------------------------------------------------
        
        query = posts_ref.where('last_engagement_at', '>=', from_datetime_utc) \
                         .order_by('last_engagement_at', direction=firestore.Query.DESCENDING) \
                         .order_by('trending_score', direction=firestore.Query.DESCENDING) \
                         .limit(20) # Limit the number of trending posts returned (e.g., top 20)

        try:
            docs = query.stream()
            # Convert Firestore documents to a list of dictionaries for the serializer
            posts_list = []
            for doc in docs:
                post_data = doc.to_dict()
                post_data['id'] = doc.id # Add the document ID to the dictionary
                posts_list.append(post_data)
            return posts_list # Return a list of dicts
        except Exception as e:
            logging.error(f"Failed to fetch trending posts from Firestore: {e}", exc_info=True)
            # Depending on your error handling, you might return an empty list or raise an APIException
            return [] 

    def list(self, request, *args, **kwargs):
        posts_data = self.get_queryset()

        # Add has_liked status (already in your code)
        for post in posts_data:
            post_id = post.get('id')
            if request.user.is_authenticated:
                user_id = str(request.user.id)
                try:
                    like_doc = db.collection('posts').document(post_id).collection('likes').document(user_id).get()
                    post['has_liked'] = like_doc.exists
                except Exception as e:
                    logging.warning(f"Error checking like status for post {post_id}: {e}")
                    post['has_liked'] = False
            else:
                post['has_liked'] = False

        # --- Hydrate author info ---
        author_ids = list(set(str(post['author_id']) for post in posts_data if 'author_id' in post))
        authors_from_postgres = User.objects.filter(id__in=author_ids).only('id', 'email', 'profile_pic_url')
        authors_map = {}
        for author in authors_from_postgres:
            display_name_slug = None
            if hasattr(author, 'student') and author.student.display_name_slug:
                display_name_slug = author.student.display_name_slug
            elif hasattr(author, 'organization') and author.organization.display_name_slug:
                display_name_slug = author.organization.display_name_slug

            authors_map[str(author.id)] = {
                "id": author.id,
                "email": author.email,
                "profile_pic_url": author.profile_pic_url,
                "display_name_slug": display_name_slug,
            }

        # --- Serialize with authors_map ---
        serializer = self.get_serializer(posts_data, many=True, context={'authors_map': authors_map})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SharePostFirestoreView(APIView):
    """
    Allows an authenticated user to share a specific post using a Firestore transactional decorator.
    URL: /api/posts/{post_id}/share/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id):
        user_id = str(request.user.id) # Firestore UIDs are strings

        # 1. Get references to the documents we'll interact with
        post_ref = db.collection('posts').document(post_id)
        shares_ref = db.collection('shares')

        try:
            # 2. Initial Post Existence Check (outside transaction for quick validation)
            post_doc_snapshot = post_ref.get()
            if not post_doc_snapshot.exists:
                return Response({"message": "Post not found."}, status=status.HTTP_404_NOT_FOUND)

            # 3. Check if the user has already shared (outside transaction for quick feedback)
            existing_share_query = shares_ref.where('user_id', '==', user_id)\
                                           .where('post_id', '==', post_id)\
                                           .limit(1).get()

            if existing_share_query:
                return Response({"message": "You have already shared this post."}, status=status.HTTP_400_BAD_REQUEST)

            # --- Define the transactional function ---
            # It takes the transaction object and any other arguments it needs
            @firestore.transactional
            def create_share_and_increment_count(transaction, current_post_ref, current_shares_ref, payload):
                # Re-read post document within the transaction to ensure latest state
                current_post_doc_in_tx = current_post_ref.get(transaction=transaction)
                if not current_post_doc_in_tx.exists:
                    # If the post was deleted concurrently, this transaction will fail.
                    raise ValueError("Post not found during transaction.")

                # Create the share document within the transaction
                new_share_doc_ref = current_shares_ref.document() # Get a new auto-ID document reference
                transaction.set(new_share_doc_ref, payload)

                # Increment the share_count on the Post document within the transaction
                transaction.update(current_post_ref, {
                    'share_count': firestore.Increment(1)
                })
                
                return new_share_doc_ref.id # Return the ID of the newly created share

            # --- Run the transactional function ---
            # It's called like a regular function, and db.transaction() is implicitly passed.
            # db.transaction() will retry the function automatically on contention.
            share_payload = {
                'user_id': user_id,
                'post_id': post_id,
                'shared_at': firestore.SERVER_TIMESTAMP,
            }
            new_share_id = create_share_and_increment_count(db.transaction(), post_ref, shares_ref, share_payload)
            
            return Response({"message": "Post shared successfully.", "share_id": new_share_id}, status=status.HTTP_201_CREATED)

        except ValueError as ve: # Catch explicit errors from inside the transaction function
            return Response({"error": f"Transaction failed: {str(ve)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Error sharing post with transaction: {e}") # Log the full error
            return Response({"error": f"Failed to share post: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserPostsFirestoreView(APIView):
    """
    List all posts by a specific user identified by their user_id.
    URL: /api/users/{user_id}/posts/
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

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
                posts_list.append(post_data)

            # Hydrate author info for the target user
            authors_map = {}
            try:
                author = User.objects.only('id', 'email', 'profile_pic_url').get(id=target_user_id)
                display_name_slug = None
                if hasattr(author, 'student') and author.student.display_name_slug:
                    display_name_slug = author.student.display_name_slug
                elif hasattr(author, 'organization') and author.organization.display_name_slug:
                    display_name_slug = author.organization.display_name_slug

                authors_map[str(author.id)] = {
                    "id": author.id,
                    "email": author.email,
                    "profile_pic_url": author.profile_pic_url,
                    "display_name_slug": display_name_slug,
                }
            except User.DoesNotExist:
                pass

            serializer = FirestorePostOutputSerializer(posts_list, many=True, context={'authors_map': authors_map})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error retrieving user posts: {e}")
            return Response({"error": f"Failed to retrieve posts for user: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

