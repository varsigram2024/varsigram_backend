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

*   **`GET /welcome/`**  [name='welcome']

    *   Description: Welcomes the user to the API.
    *   Request: `GET`
    *   Response (200 OK):
        ```json
        {"message": "Welcome to the API!"}
        ```

*   **`POST /register/`**  [name='user register']

    *   Description: Registers a new user (student or organization).
    *   Request: `POST`
    *   Request Body (JSON):
        ```json
        {
            "email": "user@example.com",
            "password": "password123",
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
                "organization_name": "",
                "exclusive": false
            }
        }
        ```
    *   Response (201 Created): Returns a JWT token and a success message.
    *   Response (400 Bad Request): If registration fails (e.g., invalid input, email already exists, both student and organization provided, or neither).

*   **`POST /login/`**  [name='login']

    *   Description: Logs in an existing user.
    *   Request: `POST`
    *   Request Body (JSON):
        ```json
        {
            "email": "user@example.com",
            "password": "password123"
        }
        ```
    *   Response (200 OK): Returns a JWT token and a success message.
    *   Response (401 Unauthorized): If login fails (e.g., incorrect credentials).

*   **`POST /logout/`**  [name='logout']

    *   Description: Logs out the current user (invalidates the token).
    *   Request: `POST`
    *   Authentication: Required
    *   Response (200 OK): On successful logout.

*   **`POST /password-reset/`**  [name='password-reset']

    *   Description: Initiates the password reset process by sending a reset link to the user's email.
    *   Request: `POST`
    *   Request Body (JSON):
        ```json
        {
            "email": "user@example.com"
        }
        ```
    *   Response (200 OK): On successful email send.

*   **`POST /password-reset-confirm/`**  [name='password-reset-confirm']

    *   Description: Confirms the password reset with the provided `uid` and `token` received via email and the new password.
    *   Request: `POST`
    *   Request Body (JSON):
        ```json
        {
            "uid": "<uid>",
            "token": "<token>",
            "new_password": "",
            "confirm_password": ""
        }
        ```
    *   Response (204 No Content): On successful password reset.
    *   Response (400 Bad Request): If the `uid`, `token`, or new password are invalid or if the reset process fails.

*   **`PUT /student/update/`**  [name='student-update']

    *   Description: Updates the authenticated student user's profile.
    *   Request: `PUT`
    *   Authentication: Required
    *   Request Body (JSON): (Only the fields to be updated are required)
    *   Response (200 OK): Returns updated student profile data.

*   **`PUT /organization/update/`**  [name='organization-update']

    *   Description: Updates the authenticated organization user's profile.
    *   Request: `PUT`
    *   Authentication: Required
    *   Request Body (JSON): (Only the fields to be updated are required)
    *   Response (200 OK): Returns updated organization profile data.

*   **`POST /change-password/`**  [name='change-password']

    *   Description: Changes the authenticated user's password.
    *   Request: `POST`
    *   Authentication: Required
    *   Request Body (JSON):
        ```json
        {
            "old_password": "old_password123",
            "new_password": "new_password456",
            "confirm_password": "new_password456"
        }
        ```
    *   Response (200 OK): On successful password change.

*   **`GET /profile/`**  [name='user-profile']

    *   Description: Retrieves the authenticated user's profile (student or organization).
    *   Request: `GET`
    *   Authentication: Required
    *   Response (200 OK): Returns user profile data and profile type.

*   **`GET /users/search/`**  [name='user-search']

    *   Description: Search for users (students or organizations) using filters such as name, faculty, and department.  
        This endpoint searches both Students and Organizations models and returns a unified result set.
    *   Request: `GET`
    *   Authentication: Required (JWT)
    *   Query Parameters:
        *   `query`: (optional) Search by student name or organization name (case-insensitive, partial match).
        *   `faculty`: (optional, students only) Filter by faculty name (case-insensitive).
        *   `department`: (optional, students only) Filter by department name (case-insensitive).
    *   Response (200 OK): Returns a list of matching users.
        ```json
        [
            {
                "type": "student",
                "email": "student@email.com",
                "faculty": "Science",
                "department": "Mathematics",
                "name": "John Doe",
                "display_name_slug": "john-doe-1"
            },
            {
                "type": "organization",
                "email": "org@email.com",
                "organization_name": "Varsigram Inc",
                "display_name_slug": "varsigram-inc-1",
                "exclusive": true
            }
        ]
        ```
    *   Response (400 Bad Request): If no valid filter is provided.
        ```json
        {
            "message": "Provide at least \"query\", \"faculty\", or \"department\"."
        }
        ```
    *   Response (200 OK, empty): If no users match the search.
        ```json
        []
        ```

**Notes:**
- The endpoint searches both students and organizations and combines results.
- For students, you can filter by `faculty`, `department`, or `query`.
- For organizations, only `query` is supported for filtering.
- All searches are case-insensitive and support partial matches.
- The `type` field in each result indicates whether


*   **`POST /deactivate/`**  [name='user-deactivate']

    *   Description: Deactivates the authenticated user's account.
    *   Request: `POST`
    *   Authentication: Required
    *   Request Body (JSON):
        ```json
        {
            "password": "your_password"
        }
        ```
    *   Response (200 OK): On successful deactivation.

*   **`POST /reactivate/`**  [name='user-reactivate']

    *   Description: Reactivates the authenticated user's account.
    *   Request: `POST`
    *   Authentication: Required
    *   Request Body (JSON):
        ```json
        {
            "password": "your_password"
        }
        ```
    *   Response (200 OK): On successful reactivation.

*   **`POST /send-otp/`**  [name='send-otp']

    *   Description: Sends an OTP to the user's registered email.
    *   Request: `POST`
    *   Authentication: Required
    *   Response (200 OK): On successful OTP send.

*   **`POST /verify-otp/`**  [name='verify-otp']

    *   Description: Verifies the provided OTP.
    *   Request: `POST`
    *   Authentication: Required
    *   Request Body (JSON):
        ```json
        {
            "otp": "123456"
        }
        ```
    *   Response (200 OK): On successful verification.

*   **`GET /check-verification/`**  [name='check-verification']

    *   Description: Checks the verification status of a user.
    *   Request: `GET`
    *   Authentication: Required
    *   Response (200 OK): Returns verification status.

*   **`POST /get-signed-upload-url/`**  [name='get-signed-upload-url']

    *   Description: Returns a signed URL for uploading files (e.g., profile pictures) to Firebase Storage.
    *   Request: `POST`
    *   Authentication: Required
    *   Request Body (JSON):
        ```json
        {
            "file_name": "filename.jpg",
            "content_type": "image/jpeg"
        }
        ```
    *   Response (200 OK): Returns the signed upload URL and file path.

*   **`GET /profile/<slug:slug>/`**  [name='public-profile']

    *   Description: Retrieves a user's public profile by `display_name_slug`.
    *   Request: `GET`
    *   Response (200 OK): Returns the public profile data and profile type.

---

**Note:**  
- All endpoints that modify or access sensitive data require authentication.
- Registration requires either a `student` or `organization` object, not both.
- Passwords must be confirmed where required.

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

*   **`GET /posts/`**  [name='post-list-firestore']

    *   Description: Retrieves a paginated list of all posts from Firestore, ordered by `timestamp` (most recent first).
    *   Request: `GET`
    *   Authentication: Optional (some fields like `has_liked` depend on authentication)
    *   Query Parameters:
        *   `page_size`: (optional, default: 10) Number of posts to return per page.
        *   `start_after`: (optional) Firestore post ID to start after (for pagination).
    *   Response (200 OK): Returns a paginated list of posts.
        ```json
        {
            "results": [
                {
                    "id": "post_id",
                    "content": "Post content",
                    "timestamp": "2025-07-22T12:34:56Z",
                    "author_id": "user_id",
                    "has_liked": false,
                    "media_urls": [],
                    // ...other post fields...
                }
            ],
            "next_cursor": "next_post_id"
        }
        ```
    *   Response (200 OK, empty): If no posts are found.
        ```json
        {
            "results": [],
            "next_cursor": null
        }
        ```
    *   Response (400 Bad Request): If an invalid `start_after` ID is provided.
        ```json
        {
            "error": "Invalid start_after ID"
        }
        ```
    *   Response (500 Internal Server Error): If an error occurs.
        ```json
        {
            "error": "Failed to retrieve posts: <error_message>"
        }
        ```

**Notes:**
- The endpoint returns posts sorted by `timestamp` (most recent first).
- Pagination is handled via the `start_after` query parameter and `next_cursor` in the response.
- Each post includes hydrated author information in the response context.
- If authenticated, the `has_liked` field reflects whether the current user has

*  **`POST /posts/`**  [name='post-list-create']

    *   **POST**: Creates a new post.
    *   Authentication: Required for POST.
    *   Request Body (POST, JSON):
        ```json
        {
            "content": "Post content",
            "slug": "optional-slug",
            "media_urls": ["url1", "url2"]
        }
        ```
    *   Response (201 Created): Returns the created post.

*   **`GET /posts/<str:post_id>/`**  [name='post-detail']

    *   Retrieves a specific post by its ID.
    *   Request: GET
    *   Response (200 OK): Returns the post data.

*   **`PUT /posts/<str:post_id>/`**  [name='post-detail']

    *   Updates a specific post.
    *   Authentication: Required
    *   Request Body (JSON):
        ```json
        {
          "content": "Updated content",
          "image": "updated_image_file" // Optional, file upload
        }
        ```
    *   Response (200 OK): Returns the updated post.

*   **`DELETE /posts/<str:post_id>/`**  [name='post-detail']

    *   Deletes a specific post.
    *   Authentication: Required
    *   Response (204 No Content): On successful deletion.

*   **`GET /posts/<str:post_id>/comments/`**  [name='post-comments']

    *   Description: Retrieves comments for a specific post. Supports cursor-based pagination.
    *   Request: `GET`
    *   Authentication: Optional (some fields may depend on authentication)
    *   Path Parameters:
        *   `post_id`: The ID of the post whose comments you want to retrieve.
    *   Query Parameters:
        *   `page_size`: (optional, default: 10) Number of comments to return per page.
        *   `start_after`: (optional) Firestore comment ID to start after (for pagination).
    *   Response (200 OK): Returns a paginated list of comments for the post.
        ```json
        {
            "results": [
                {
                    "id": "comment_id",
                    "text": "Comment text",
                    "author_id": "user_id",
                    "timestamp": "2025-07-22T12:34:56Z",
                    "profile_pic_url": "https://...",
                    "display_name_slug": "user-slug",
                    // ...other comment fields...
                }
            ],
            "next_cursor": "next_comment_id"
        }
        ```
    *   Response (200 OK, empty): If the post has no comments.
        ```json
        {
            "results": [],
            "next_cursor": null
        }
        ```
    *   Response (404 Not Found): If the post does not exist.
        ```json
        {
            "error": "Post not found"
        }
        ```
    *   Response (500 Internal Server Error): If an error occurs.
        ```json
        {
            "error": "Failed to retrieve comments: <error_message>"
        }
        ```

*   **`POST /posts/<str:post_id>/comments/create/`**  [name='post-detail']

    *   Adds a comment to a post.
    *   Authentication: Required
    *   Request Body (JSON):
        ```json
        {
            "text": "Comment text"
        }
        ```
    *   Response (201 Created): Returns the created comment.

*   **`POST /posts/<str:post_id>/like/`**  [name='post-like']

    *   Likes a specific post.
    *   Authentication: Required

*   **`GET /posts/<str:post_id>/likes/`**  [name='post-likes-list']

    *   Retrieves likes for a specific post.
    *   Request: GET

*   **`POST /posts/<str:post_id>/share/`**  [name='post-share']

    *   Shares a specific post.
    *   Authentication: Required
    *   Response (201 Created): Returns the share object.

*   **`GET /users/<str:user_id>/posts/`**  [name='user-posts-firestore']

    *   Description: Retrieves all posts authored by a specific user, including posts the user has shared. Supports cursor-based pagination.
    *   Request: `GET`
    *   Authentication: Optional (some fields like `has_liked` depend on authentication)
    *   Path Parameters:
        *   `user_id`: The ID of the user whose posts you want to retrieve.
    *   Query Parameters:
        *   `page_size`: (optional, default: 20) Number of posts to return per page.
        *   `start_after`: (optional) Firestore post ID to start after (for pagination).
    *   Response (200 OK): Returns a paginated list of posts authored or shared by the user.
        ```json
        {
            "results": [
                {
                    "id": "post_id",
                    "content": "Post content",
                    "timestamp": "2025-07-22T12:34:56Z",
                    "author_id": "user_id",
                    "is_shared": false,
                    "has_liked": false,
                    "media_urls": [],
                    // ...other post fields...
                },
                {
                    "id": "shared_post_id",
                    "content": "Shared post content",
                    "timestamp": "2025-07-21T10:00:00Z",
                    "author_id": "original_author_id",
                    "is_shared": true,
                    "shared_by_id": "user_id",
                    "shared_at": "2025-07-22T13:00:00Z",
                    "has_liked": false,
                    "media_urls": [],
                    // ...other post fields...
                }
            ],
            "next_cursor": "next_post_id"
        }
        ```
    *   Response (200 OK, empty): If the user has no posts or shares.
        ```json
        {
            "results": [],
            "next_cursor": null
        }
        ```
    *   Response (500 Internal Server Error): If an error occurs.
        ```json
        {
            "error": "Failed to retrieve posts for user: <error_message>"
        }
        ```

**Notes:**
- The endpoint returns posts sorted by `shared_at` (if shared) or `timestamp` (if authored), most recent first.
- Pagination is handled via the `start_after` query parameter and `next_cursor` in the response.
- Each post includes hydrated author information and share details if applicable.
- If authenticated, the `has_liked`


*   **`PUT /posts/{post_id}/comments/{comment_id}/`**  
    *Edit a comment (author only)*

    - **Description:** Update the content of a specific comment on a post. Only the comment's author can edit.
    - **Authentication:** Required (JWT, verified user)
    - **Path Parameters:**
        - `post_id`: The ID of the post.
        - `comment_id`: The ID of the comment to edit.
    - **Request Body:**
        ```json
        {
            "text": "Updated comment text"
        }
        ```
    - **Response (200 OK):**
        ```json
        {
            "id": "comment_id",
            "text": "Updated comment text",
            "author_id": "user_id",
            "timestamp": "2025-07-22T12:34:56Z",
            // ...other comment fields...
        }
        ```
    - **Response (403 Forbidden):**
        ```json
        {
            "error": "You do not have permission to edit this comment."
        }
        ```
    - **Response (404 Not Found):**
        ```json
        {
            "error": "Comment not found"
        }
        ```

*   **`DELETE /posts/{post_id}/comments/{comment_id}/`**  
    *Delete a comment (author only)*

    - **Description:** Delete a specific comment on a post. Only the comment's author can delete.
    - **Authentication:** Required (JWT, verified user)
    - **Path Parameters:**
        - `post_id`: The ID of the post.
        - `comment_id`: The ID of the comment to delete.
    - **Response (204 No Content):** Comment deleted successfully.
    - **Response (403 Forbidden):**
        ```json
        {
            "error": "You do not have permission to delete this comment."
        }
        ```
    - **Response (404 Not Found):**
        ```json
        {
            "error": "Comment not found"
        }
        ```

**Notes:**
- Only the author of the comment can edit or delete it.
- Deleting a comment decrements the parent post's `comment_count`.
- Editing supports partial updates (PATCH semantics via PUT).

*   **`GET /official`**  [name='exclusive-orgs-recent-posts']

    *   Description: Retrieves recent posts from organizations marked as `exclusive=True`. Supports cursor-based pagination.
    *   Request: `GET`
    *   Authentication: Optional (some fields like `has_liked` depend on authentication)
    *   Query Parameters:
        *   `page_size`: (optional, default: 20) Number of posts to return per page.
        *   `start_after`: (optional) Firestore document ID to start after (for pagination).
    *   Response (200 OK): Returns a paginated list of recent posts from exclusive organizations.
        ```json
        {
            "results": [
                {
                    "id": "post_id",
                    "content": "Post content",
                    "timestamp": "2025-07-22T12:34:56Z",
                    "author_id": "org_user_id",
                    "has_liked": false,
                    "media_urls": [],
                    // ...other post fields...
                }
            ],
            "next_cursor": "next_post_id"
        }
        ```
    *   Response (200 OK, empty): If no exclusive organizations or posts are found.
        ```json
        {
            "results": [],
            "next_cursor": null
        }
        ```
    *   Response (500 Internal Server Error): If an error occurs.
        ```json
        {
            "detail": "Error fetching posts."
        }
        ```

**Notes:**
- The endpoint returns posts sorted by `timestamp` (most recent first).
- Pagination is handled via the `start_after` query parameter and `next_cursor` in the response.
- Each post includes hydrated author information in the response context.
- Only organizations with `exclusive=True` are included.
- If authenticated, the `has_liked` field reflects whether the current user has liked each post.


### `GET /feed/` [name='feed-view']

- **Description:**  
  Returns a randomized, paginated feed of posts for the authenticated user.  
  The feed is dynamically weighted based on the user's profile type (Student or Organization) and includes posts from followed users, organizations, and other relevant categories.

- **Request:**  
  `GET /feed/`

- **Authentication:**  
  Required (JWT)

- **Query Parameters:**
  - `page`: (optional, default: 1) The page number for pagination.
  - `page_size`: (optional, default: 10) Number of posts per page.
  - `session_id`: (optional) A unique string to ensure consistent feed order for a session. If not provided, a new session ID is generated.

- **Response (200 OK):**
    ```json
    {
      "results": [
        {
          "id": "post_id_123",
          "author_id": "user_id_456",
          "author_name": "John Doe",
          "author_profile_pic_url": "https://...",
          "is_verified": true,
          "exclusive": false,
          "faculty": "Science",
          "department": "Mathematics",
          "display_name_slug": "john-doe-1",
          "content": "Post content here...",
          "timestamp": "2025-09-17T12:34:56Z",
          "media_urls": [],
          "view_count": 42,
          "like_count": 5,
          "has_liked": false
        }
        // ...more posts
      ],
      "session_id": "abc123-session-id",
      "page": 1,
      "page_size": 10,
      "has_next": true
    }
    ```

- **Response (400/500):**
    ```json
    {
      "error": "Failed to retrieve feed posts: <error message>"
    }
    ```

**Notes:**
- The feed is shuffled and weighted per user type for diversity.
- `view_count` is incremented only when the frontend calls the batch view endpoint for posts actually seen.
- `like_count` and `has_liked` are included for each post.
- Use the returned `session_id` for consistent pagination within a session.
- `has_next` indicates if more pages are available.


### `POST /api/posts/batch_view/` [name='batch-post-view-increment']

- **Description:**  
  Increments the view count for multiple posts in a single request.  
  This endpoint is intended to be called by the frontend when posts actually appear in the user's viewport (e.g., detected via Intersection Observer).

- **Request:**  
  `POST /api/posts/batch_view/`

- **Authentication:**  
  Required (JWT)

- **Request Body:**
    ```json
    {
      "post_ids": ["post_id_1", "post_id_2", "post_id_3"]
    }
    ```

- **Response (200 OK):**
    ```json
    {
      "message": "3 post view counts incremented successfully."
    }
    ```

- **Response (400 Bad Request):**
    ```json
    {
      "error": "A list of post_ids is required."
    }
    ```

- **Response (500 Internal Server Error):**
    ```json
    {
      "error": "Failed to increment view count: <error message>"
    }
    ```

**Notes:**
- Only unique post IDs are processed per request.
- Use this endpoint to increment views only for posts that are actually seen by the user.
- This does not affect like

<!-- 
*   **`GET /trending/`**  [name='trending-posts']

    *   Retrieves trending posts (based on likes, shares, or other criteria).
    *   Request: GET
    *   Response (200 OK): Returns a list of trending posts. -->


### Following & Followers

#### **Follow a User or Organization**

- **`POST /users/follow/`**  
  *Allows any student or organization to follow another student or organization.*

  **Request:**
  - Method: `POST`
  - Authentication: Required
  - Body:
    ```json
    {
      "follower_type": "student",        // or "organization"
      "follower_id": 1,
      "followee_type": "organization",   // or "student"
      "followee_id": 2
    }
    ```
  **Responses:**
  - `201 Created`: Follow successful.
  - `400 Bad Request`: Invalid request or already following.
  - `404 Not Found`: Follower or followee not found.

---

#### **Unfollow a User or Organization**

- **`POST /users/unfollow/`**  
  *Allows a student or organization to unfollow another student or organization.*

  **Request:**
  - Method: `POST`
  - Authentication: Required
  - Body:
    ```json
    {
      "follower_type": "student",        // or "organization"
      "follower_id": 1,
      "followee_type": "organization",   // or "student"
      "followee_id": 2
    }
    ```
  **Responses:**
  - `204 No Content`: Unfollow successful.
  - `404 Not Found`: Follow relationship does not exist.

---

#### **List Followers**

- **`GET /users/followers/?followee_type=&followee_id=`**  
  *Retrieve all followers (students or organizations) of a given user or organization.*

  **Request:**
  - Method: `GET`
  - Query Parameters:
    - `followee_type`: `"student"` or `"organization"`
    - `followee_id`: ID of the user or organization

  **Responses:**
  - `200 OK`: Returns a list of followers.
  - `404 Not Found`: Followee not found.

---

#### **List Following**

- **`GET /users/following/?follower_type=&follower_id=`**  
  *Retrieve all users or organizations that a given user or organization is following.*

  **Request:**
  - Method: `GET`
  - Authentication: Required
  - Query Parameters:
    - `follower_type`: `"student"` or `"organization"`
    - `follower_id`: ID of the user or organization

  **Responses:**
  - `200 OK`: Returns a list of followed users/organizations.

---

**Notes:**
- All follow/unfollow actions require authentication.
- You can follow/unfollow between any combination of students and organizations.
- The same endpoints

*   **`GET /who-to-follow/` \[name='who-to-follow']**

    *   Description: Returns a list of recommended organizations for the authenticated student to follow. Recommendations are based on the student's department, faculty, religion, and always include exclusive organizations.
    *   Request: `GET`
    *   Authentication: Required
    *   Response (200 OK): Returns a list of recommended organizations, each with:
        ```json
        [
          {
            "id": 1,
            "name": "Organization Name",
            "display_name_slug": "org-slug",
            "profile_pic_url": "https://...",
            "bio": "Organization bio"
          }
        ]
        ```

---

**Note:**  
- All follow/unfollow actions require the user to be authenticated and to be a student.
- The "Who To Follow" endpoint will always include organizations marked as exclusive, and will not return organizations the student already follows.

...
### Organization Verification

*   **`GET /verified-org-badge/`**  [name='verified-org-badge']

    *   Description: Checks if the authenticated organization is both exclusive and verified.
    *   Request: `GET`
    *   Authentication: Required
    *   Response (200 OK): Returns `{"is_verified": true}` if the organization is exclusive and verified, otherwise `{"is_verified": false}`.
    *   Response (404 Not Found): If the organization profile is not found.


## Notification Device Endpoints

### Register Device

*   **`POST /notifications/register/`**  
    Registers a device for push notifications.

    - **Description:**  
      Registers or updates a device for the authenticated user using the device's FCM registration token.

    - **Authentication:**  
      Required (JWT)

    - **Request Body:**
        ```json
        {
            "registration_id": "FCM_DEVICE_TOKEN",
            "device_id": "optional_device_identifier"
        }
        ```

    - **Response (201 Created):**
        ```json
        {
            "registration_id": "FCM_DEVICE_TOKEN",
            "device_id": "optional_device_identifier",
            "user": 123,
            "active": true
        }
        ```

    - **Response (400 Bad Request):**
        ```json
        {
            "detail": "registration_id is required."
        }
        ```

---

### Unregister Device

*   **`DELETE /notifications/unregister/<registration_id>/`**  
    Unregisters a device from push notifications.

    - **Description:**  
      Unregisters (deletes) a device for the authenticated user by its FCM registration token.

    - **Authentication:**  
      Required (JWT)

    - **Path Parameters:**
        - `registration_id`: The FCM registration token of the device to unregister.

    - **Response (204 No Content):**  
      Device unregistered successfully.

    - **Response (404 Not Found):**
        ```json
        {
            "detail": "Device not found or not associated with this user."
        }
        ```

    - **Response (400 Bad Request):**
        ```json
        {
            "detail": "registration_id is required."
        }
        ```

**Notes:**
- Devices must be registered to receive push notifications.
- Unregistering a device disables notifications for that device only.
- Only the authenticated user can register or unregister their own devices.




