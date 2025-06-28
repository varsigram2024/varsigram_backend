from rest_framework import permissions
from .models import Organization

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

