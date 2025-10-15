from rest_framework import permissions, serializers
from .models import Organization, User
from firebase_admin import firestore

# class IsOwnerOrReadOnly(permissions.BasePermission):
#     """
#     Custom permission to only allow owners of an object to edit it.
#     """

#     def has_object_permission(self, request, view, obj):
#         # Read permissions are allowed to any request,
#         # so we'll always allow GET, HEAD or OPTIONS requests.
#         if request.method in permissions.SAFE_METHODS:
#             return True

#         # Instance must have an attribute named `user`.
#         return obj.user == request.user


def get_exclusive_org_user_ids():
    """
    Returns a list of user_id strings for organizations with exclusive=True.
    """
    exclusive_org_user_ids = list(
        Organization.objects.filter(exclusive=True).values_list('user_id', flat=True)
    )
    exclusive_org_user_ids_str = [str(uid) for uid in exclusive_org_user_ids]
    return exclusive_org_user_ids_str

def get_student_user_ids():
    """
    Returns a list of user_id strings for organizations with exclusive=False.
    """
    student_user_ids = list(
        User.objects.filter(student__isnull=False).values_list('id', flat=True)
    )
    student_user_ids_str = [str(uid) for uid in student_user_ids]
    return student_user_ids_str

def get_firestore_client():
    """Returns the Firestore client instance."""
    return firestore.client()

def get_post_author_id_from_firestore(post_id: str) -> int:
    """
    Fetches the post's author's local Postgres User ID from the Firestore database.

    :param post_id: The unique Firestore document ID of the post.
    :returns: The local Postgres User ID (int) of the post's author.
    :raises: serializers.ValidationError if the post is not found or data is invalid.
    """
    if not post_id:
        raise serializers.ValidationError("Post ID cannot be empty.")

    db = get_firestore_client()
    
    # ASSUMPTION: Your posts are in a collection named 'posts'
    # and the author's local Django User ID is stored in a field named 'author_id'.
    try:
        post_ref = db.collection('posts').document(post_id)
        post_doc = post_ref.get()

        if not post_doc.exists:
            raise serializers.ValidationError(
                f"Post with ID '{post_id}' not found in Firestore."
            )
        
        post_data = post_doc.to_dict()
        author_id = post_data.get('author_id')
        
        if not author_id:
            raise serializers.ValidationError(
                "Post data is missing the required 'author_id' field."
            )

        # Ensure the author_id is an integer (as it is a local PK)
        return int(author_id)
        
    except serializers.ValidationError:
        # Re-raise explicit validation errors
        raise
    except Exception as e:
        # Catch potential Firestore connectivity or permission errors
        raise serializers.ValidationError(
            f"Firestore lookup failed for Post ID {post_id}: {e}"
        )

