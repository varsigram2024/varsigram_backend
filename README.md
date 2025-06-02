# VARSIGRAM BACKEND

# API Documentation

This document provides detailed information about the API endpoints for the project. The API uses RESTful principles and communicates using JSON.

## Base URL

The base URL for the API is `/api/v1/`. All endpoints listed below are relative to this base URL.

## Authentication

Most endpoints require authentication. Authentication is handled using token-based authentication (e.g., JWT). Include the token in the `Authorization` header of your requests as follows:

>  Authorization: Bearer <your_token>

## Endpoints

### User Authentication and Management

*   **`GET /welcome/` \[name='welcome']**

    *   Description: Welcomes the user to the API.
    *   Request: `GET`
    *   Response (200 OK):

        ```json
        {"message": "Welcome to the API!"}
        ```

*   **`POST /register/` \[name='user register']**

    *   Description: Registers a new user.
    *   Request: `POST`
    *   Request Body (JSON):

        ```json
        {
            "email": "",
            "password": "",
            "bio": "",
            "student": {
                "name": "",
                "faculty": "",
                "department": "",
                "year": "",
                "religion": "",
                "phone_number": "",
                "sex": "",
                "university": "",
                "date_of_birth": null
            },
            "organization": {
                "organization_name": ""
            }
        }
        ```

    *   Response (201 Created): Returns user data on successful registration.
    *   Response (400 Bad Request): Returns error details if registration fails (e.g., invalid input, email already exists).

*   **`POST /login/` \[name='login']**

    *   Description: Logs in an existing user.
    *   Request: `POST`
    *   Request Body (JSON):

        ```json
        {
          "email": "user@example.com",
          "password": "password123"
        }
        ```

    *   Response (200 OK): Returns an authentication token.
    *   Response (401 Unauthorized): Returns an error if login fails (e.g., incorrect credentials).

*   **`POST /logout/` \[name='logout']**

    *   Description: Logs out the current user (invalidates the token).
    *   Request: `POST`
    *   Authentication: Required
    *   Response (204 No Content): On successful logout.

*   **`POST /password-reset/` \[name='password-reset']**

    *   Description: Initiates the password reset process by sending a reset link to the user's email.
    *   Request: `POST`
    *   Request Body (JSON):

        ```json
        {
          "email": "user@example.com"
        }
        ```

*   **`POST /password-reset-confirm/` \[name='password-reset-confirm']**

    *   Description: Confirms the password reset with the provided `uid` and `token` received via email and the new password.
    *   Request: `POST`
    *   How to use this endpoint:
        1.  The user requests a password reset using the `/password-reset/` endpoint.
        2.  The backend sends an email to the user containing a link with the `uid` and `token` as query parameters. The link will have the following format:

            ```
            <your_frontend_url>/password-reset/confirm/?uid=<uid>&token=<token>
            ```

            *   `<your_frontend_url>`: This is the URL of your frontend application's password reset confirmation page (e.g., `https://yourwebsite.com/reset-password`).
            *   `<uid>`: A unique identifier for the user (e.g., base64 encoded user id).
            *   `<token>`: A unique token generated for this password reset request.

        3.  The user clicks the link in the email. This will navigate them to your frontend's password reset confirmation page, which will extract the `uid` and `token` from the URL's query parameters.
        4.  The frontend then makes a `POST` request to this `/password-reset-confirm/` endpoint, including the `uid`, `token`, and the new password in the request body.

    *   Request Body (JSON):

        ```json
        {
          "uid": "<uid>", // From the URL query parameters
          "token": "<token>", // From the URL query parameters
          "new_password": "",
          "confirm_password": ""
        }
        ```

    *   Response (204 No Content): On successful password reset.
    *   Response (400 Bad Request): If the `uid`, `token`, or new password are invalid or if the reset process fails.
*   **`PUT /student/update/` \[name='student-update']**

    *   Description: Updates the authenticated student user's profile.
    *   Request: `PUT`
    *   Authentication: Required
    *   Request Body (JSON): (Same structure as registration but only the fields to be updated are required)

*   **`PUT /organization/update/` \[name='organization-update']**

    *   Description: Updates the authenticated organization user's profile.
    *   Request: `PUT`
    *   Authentication: Required
    *   Request Body (JSON): (Same structure as registration but only the fields to be updated are required)

*   **`POST /change-password/` \[name='change-password']**

    *   Description: Changes the authenticated user's password.
    *   Request: `POST`
    *   Authentication: Required
    *   Request Body (JSON):

        ```json
        {
          "old_password": "old_password123",
          "new_password": "new_password456"
        }
        ```

*   **`GET /profile/` \[name='user-profile']**

    *   Description: Retrieves the authenticated user's profile.
    *   Request: `GET`
    *   Authentication: Required
    *   Response (200 OK): Returns user profile data.

*   **`GET /users/search/?q=<query>` \[name='search']**

    *   Description: Searches for users based on a query string.
    *   Request: `GET`
    *   Query Parameters:
        *   `q`: The search query.
    *   Response (200 OK): Returns a list of matching users.

*   **`POST /deactivate/` \[name='user-deactivate']**

    *   Description: Deactivates the authenticated user's account.
    *   Request: `POST`
    *   Authentication: Required

*   **`POST /reactivate/` \[name='user-reactivate']**

    *   Description: Reactivates the authenticated user's account.
    *   Request: `POST`
    *   Authentication: Required

*   **`POST /send-otp/` \[name='send-otp']**

    *   Description: Sends an OTP to the user's registered email.
    *   Request: `POST`
    *   Request Body (JSON):

        ```json
        {
          "email": "user@example.com"
        }
        ```

*   **`POST /verify-otp/` \[name='verify-otp']**

    *   Description: Verifies the provided OTP.
    *   Request: `POST`
    *   Request Body (JSON):

        ```json
        {
          "email": "user@example.com",
          "otp": "123456"
        }
        ```

*   **`GET /check-verification/` \[name='check-verification']**

    *   Description: Checks the verification status of a user.
    *   Request: `GET`
    *   Authentication: Required
    *   Response (200 OK): Returns verification status.

### Messaging

*   **`GET /messages/` and `POST /messages/` \[name='message-list-create']**

    *   Description: Retrieves a list of messages (GET) or creates a new message (POST).
    *   Request: `GET` or `POST`
    *   Authentication: Required
    *   Request Body (JSON - for POST):

        ```json
        {
            "receiver": null,
            "content": "",
            "is_read": false
        }
        ```

*   **`GET /messages/<int:pk>/`, `PUT /messages/<int:pk>/`, `DELETE /messages/<int:pk>/` \[name='message-retrieve-update-destroy']**

    *   Description: Retrieves (GET), updates (PUT), or deletes (DELETE) a specific message.
    *   Request: `GET`, `PUT`, or `DELETE`
    *   Authentication: Required

### Posts

*   **`GET /posts/` and `POST /posts/` \[name='post-list-create']**

    *   Description: Retrieves a list of posts (GET) or creates a new post (POST).
    *   Request: `GET` or `POST`
    *   Authentication: Required for `POST`
    *   Request Body (JSON - for POST):

        ```json
        {
          "content": "Post content",
          "image": "image_file" (Optional - file upload)
        }
        ```

*   **`GET /posts/<slug:slug>/` \[name='post-detail']**

    *   Description: Retrieves a specific post by its slug.
    *   Request: `GET`

*   **`GET /posts/<slug:slug>/comments/` \[name='post-comments']**

    *   Description: Retrieves comments for a specific post.
    *   Request: `GET`

*   **`POST /posts/<slug:slug>/like/` \[name='post-like']**

    *   Description: Likes a specific post.
    *   Request: `POST`
    *   Authentication: Required

*   **`POST /posts/<slug:slug>/share/` \[name='post-share']**

    *   Description: Shares a specific post. Creates a new "Share" entry referencing the original post.
    *   Request: `POST`
    *   Authentication: Required
    *   Response (201 Created): Returns the newly created share object.
    *   Response (400 Bad Request): If the post has already been shared by the user.

*   **`GET /users/<slug:display_name_slug>/posts/` \[name='user-posts']**

    *   Description: Retrieves all posts by a specific user, identified by their `display_name_slug`.
    *   Request: `GET`
    *   Response (200 OK): Returns a list of posts.
    *   Response (404 Not Found): If the user is not found.

*   **`PUT /posts/<slug:slug>/edit/` \[name='post-edit']**

    *   Description: Edits a specific post.
    *   Request: `PUT`
    *   Authentication: Required
    *   Request Body (JSON):

        ```json
        {
          "content": "Updated post content",
          "image": "updated_image_file" (Optional - file upload)
        }
        ```

*   **`DELETE /posts/<slug:slug>/delete/` \[name='post-delete']**

    *   Description: Deletes a specific post.
    *   Request: `DELETE`
    *   Authentication: Required
    *   Response (204 No Content): On successful deletion.

*   **`GET /posts/search/?q=<query>` \[name='post-search']**

    *   Description: Searches for posts based on a query string.
    *   Request: `GET`
    *   Query Parameters:
        *   `q`: The search query.
    *   Response (200 OK): Returns a list of matching posts.

*   **`GET /feed/` \[name='feed']**

    *   Description: Retrieves the authenticated user's feed, including posts from followed organizations, posts from users in the same department, faculty, religion, and the user's own posts and shares.
    *   Request: `GET`
    *   Authentication: Required
    *   Query Parameters:
        * `shared`: If present, will include shared posts in the feed

*   **`GET /trending/` \[name='trending-posts']**

    *   Description: Retrieves trending posts (based on likes, shares, or other criteria).
    *   Request: `GET`
    *   Response (200 OK): Returns a list of trending posts.

### Following/Followers

*   **`POST /users/<slug:display_name_slug>/follow/` \[name='follow-organization']**

    *   Description: Allows a student to follow an organization, identified by its `display_name_slug`.
    *   Request: `POST`
    *   Authentication: Required
    *   Response (201 Created): On successful follow.
    *   Response (400 Bad Request): If the user is not a student or is already following the organization.
    *   Response (404 Not Found): If the organization is not found.

*   **`POST /users/<slug:display_name_slug>/unfollow/` \[name='unfollow-organization']**

    *   Description: Allows a student to unfollow an organization, identified by its `display_name_slug`.
    *   Request: `POST`
    *   Authentication: Required
    *   Response (204 No Content): On successful unfollow.
    *   Response (404 Not Found): If the follow relationship does not exist.

*   **`GET /users/<slug:display_name_slug>/followers/` \[name='organization-followers']**

    *   Description: Retrieves the followers (students) of an organization, identified by its `display_name_slug`.
    *   Request: `GET`
    *   Response (200 OK): Returns a list of student followers.
    *   Response (404 Not Found): If the organization is not found.

*   **`GET /following/` \[name='following-organizations']**

    *   Description: Retrieves the organizations that the authenticated user (student) is following.
    *   Request: `GET`
    *   Authentication: Required
    *   Response (200 OK): Returns a list of followed organizations.
