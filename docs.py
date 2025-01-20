# Description: This file contains the API documentation for the project.

# api/v1/ welcome/ [name='welcome'] : This endpoint is used to welcome the user to the API.

# api/v1/ register/ [name='user register'] : This endpoint is used to register a new user.

# api/v1/ login/ [name='login'] : This endpoint is used to login the user.

# api/v1/ logout/ [name='logout'] : This endpoint is used to logout the user.

# api/v1/ password-reset/ [name='password-reset'] : This endpoint is used to reset the user's password.

# api/v1/ password-reset-confirm/ [name='password-reset-confirm'] : This endpoint is used to confirm the user's password reset.

# api/v1/ student/update/ [name='student-update'] : This endpoint is used to update the student's profile.

# api/v1/ organization/update/ [name='organization-update'] : This endpoint is used to update the organization's profile.

# api/v1/ change-password/ [name='change-password'] : This endpoint is used to change the user's password.

# api/v1/ profile/ [name='user-profile'] : This endpoint is used to view the user's profile.

# api/v1/ users/search/ [name='search'] : This endpoint is used to search for users.

# api/v1/ deactivate/ [name='user-deactivate'] : This endpoint is used to deactivate the user.

# api/v1/ reactivate/ [name='user-reactivate'] : This endpoint is used to reactivate the user.

# api/v1/ send-otp/ [name='send-otp'] : This endpoint is used to send an OTP to the user.

# api/v1/ verify-otp/ [name='verify-otp'] : This endpoint is used to verify the OTP.

# api/v1/ check-verification/ [name='check-verification'] : This endpoint is used to check the user's verification status.

# api/v1/ messages/ [name='message-list-create'] : This endpoint is used to list and create messages.

# api/v1/ messages/<int:pk>/ [name='message-retrieve-update-destroy'] : This endpoint is used to retrieve, update and destroy messages.

# api/v1/ posts/ [name='post-list-create'] : This endpoint is used to list and create posts.

# api/v1/ posts/<slug:slug>/ [name='post-detail'] : This endpoint is used to view the post detail.

# api/v1/ posts/<slug:slug>/comments/ [name='post-comments'] : This endpoint is used to view the post comments.

# api/v1/ posts/<slug:slug>/like/ [name='post-like'] : This endpoint is used to like the post.

# api/v1/ posts/<slug:slug>/share/ [name='post-share'] : This endpoint is used to share the post.

# api/v1/ users/<slug:display_name_slug>/posts/ [name='user-posts'] : This endpoint is used to view the user's posts.

# api/v1/ posts/<slug:slug>/edit/ [name='post-edit'] : This endpoint is used to edit the post.

# api/v1/ posts/<slug:slug>/delete/ [name='post-delete'] : This endpoint is used to delete the post.

# api/v1/ posts/search/ [name='post-search'] : This endpoint is used to search for posts.

# api/v1/ feed/ [name='feed'] : This endpoint is used to view the user's feed.

# api/v1/ trending/ [name='trending-posts'] : This endpoint is used to view the trending posts.

# api/v1/ organizations/<slug:display_name_slug>/follow/ [name='follow-organization'] :This endpoint is used to follow the organization.

# api/v1/ organizations/<slug:display_name_slug>/unfollow/ [name='unfollow-organization'] : This endpoint is used to unfollow the organization.

# api/v1/ organizations/<slug:display_name_slug>/followers/ [name='organization-followers'] : This endpoint is used to view the organization's followers.

# api/v1/ following/ [name='following-organizations'] : This endpoint is used to view the following organizations.