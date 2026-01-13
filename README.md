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

-----

## 🌐 API Endpoint Documentation: User Search

  * **`GET /users/search/`**  \[name='user-search']

      * **Description**: Search for users (students or organizations) using filters such as name, faculty, and department. This endpoint searches both **Student** and **Organization** models and returns a unified, **paginated** result set.
      * **Request**: `GET`
      * **Authentication**: Required (**JWT**)
      * **Permissions**: `IsAuthenticated`
      * **Query Parameters**:
          * `query`: (**Optional** $\\rightarrow$ see **Mandatory Filter Note**) Search by student name or organization name (**case-insensitive, partial match**).
          * `faculty`: (**Optional**, students only) Filter by student's faculty name (**case-insensitive, partial match**).
          * `department`: (**Optional**, students only) Filter by student's department name (**case-insensitive, partial match**).
          * `page`: (Optional) The page number to retrieve. Defaults to **1**.
          * `page_size`: (Optional) Custom page size. Max size is **50**. Defaults to **10**.
      * **Response (200 OK)**: Returns a paginated list of matching users.
        ```json
        {
            "count": 42,
            "next": "http://api.varsigram.com/users/search/?page=2",
            "previous": null,
            "results": [
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
        }
        ```
      * **Response (400 Bad Request)**: If no valid filter is provided.
        ```json
        {
            "message": "Provide at least \"query\", \"faculty\", or \"department\"."
        }
        ```

-----

  * **Mandatory Filter Note**: You **must** provide at least one of the following query parameters: `query`, `faculty`, or `department`.
  * **Combined Results**: The endpoint searches both students and organizations and combines results into a single list before pagination.
  * **Filtering Logic**:
      * For students, you can filter by `faculty`, `department`, or `query` (on `name`).
      * For organizations, only `query` (on `organization_name`) is supported for filtering.
  * **Search Type**: All searches are **case-insensitive** and support **partial matches**.
  * **Pagination**: The default page size is **10**, and the maximum allowed page size is **50**.

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

*   **`POST /get_media_upload_url/`**  [name='get_media_upload_url']

    *   Description: Returns a signed URL for uploading media files to Firebase Storage.
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

* **`GET /posts/questions/`**
[name='questions-recent-posts']

    *   Description: Retrieves recent posts with question tag. Supports cursor-based pagination.
    *   Request: `GET`
    *   Authentication: Optional (some fields like `has_liked` depend on authentication)
    *   Query Parameters:
        *   `page`: (optional, default: 1) The page number for pagination.
        *   `page_size`: (optional, default: 10) Number of posts to return per page.
        *   `session_id`: (optional) A unique string to ensure consistent feed order for a session. If not provided, a new session ID is generated.
    *   Response (200 OK): Returns a paginated list of recent posts with question tag.
        ```json
        {
            "results": [
                {
                    "id": "post_id",
                    "content": "Post content",
                    "timestamp": "2025-07-22T12:34:56Z",
                    "author_id": "org_user_id",
                    "has_liked": false,
                    "has_rewarded": true,
                    "media_urls": [],
                    // ...other post fields...
                }
            ],
            "session_id": "abc123-session-id",
            "page": 1,
            "page_size": 10,
            "has_next": true
        }
        ```
    *   Response (200 OK, empty): If no posts are found.
        ```json
        {
            "results": [],
            "session_id": "abc123-session-id",
            "page": 1,
            "page_size": 10,
            "has_next": false
        }
        ```
    *   Response (500 Internal Server Error): If an error occurs.
        ```json
        {
            "detail": "Error fetching posts."
        }
        ```

* **`GET /posts/relatable/`**
[name='relatable-recent-posts']

    *   Description: Retrieves recent posts with relatable tag. Supports cursor-based pagination.
    *   Request: `GET`
    *   Authentication: Optional (some fields like `has_liked` depend on authentication)
    *   Query Parameters:
        *   `page`: (optional, default: 1) The page number for pagination.
        *   `page_size`: (optional, default: 10) Number of posts to return per page.
        *   `session_id`: (optional) A unique string to ensure consistent feed order for a session. If not provided, a new session ID is generated.
    *   Response (200 OK): Returns a paginated list of recent posts with relatable tag.
        ```json
        {
            "results": [
                {
                    "id": "post_id",
                    "content": "Post content",
                    "timestamp": "2025-07-22T12:34:56Z",
                    "author_id": "org_user_id",
                    "has_liked": false,
                    "has_rewarded": true,
                    "media_urls": [],
                    // ...other post fields...
                }
            ],
            "session_id": "abc123-session-id",
            "page": 1,
            "page_size": 10,
            "has_next": true
        }
        ```
    *   Response (200 OK, empty): If no posts are found.
        ```json
        {
            "results": [],
            "session_id": "abc123-session-id",
            "page": 1,
            "page_size": 10,
            "has_next": false
        }
        ```
    *   Response (500 Internal Server Error): If an error occurs.
        ```json
        {
            "detail": "Error fetching posts."
        }
        ```

* **`GET /posts/updates/`**
[name='updates-recent-posts']

    *   Description: Retrieves recent posts with update tag. Supports cursor-based pagination.
    *   Request: `GET`
    *   Authentication: Optional (some fields like `has_liked` depend on authentication)
    *   Query Parameters:
        *   `page`: (optional, default: 1) The page number for pagination.
        *   `page_size`: (optional, default: 10) Number of posts to return per page.
        *   `session_id`: (optional) A unique string to ensure consistent feed order for a session. If not provided, a new session ID is generated.
    *   Response (200 OK): Returns a paginated list of recent posts with update tag.
        ```json
        {
            "results": [
                {
                    "id": "post_id",
                    "content": "Post content",
                    "timestamp": "2025-07-22T12:34:56Z",
                    "author_id": "org_user_id",
                    "has_liked": false,
                    "has_rewarded": true,
                    "media_urls": [],
                    // ...other post fields...
                }
            ],
            "session_id": "abc123-session-id",
            "page": 1,
            "page_size": 10,
            "has_next": true
        }
        ```
    *   Response (200 OK, empty): If no posts are found.
        ```json
        {
            "results": [],
            "session_id": "abc123-session-id",
            "page": 1,
            "page_size": 10,
            "has_next": false
        }
        ```
    *   Response (500 Internal Server Error): If an error occurs.
        ```json
        {
            "detail": "Error fetching posts."
        }
        ```

* **`GET /posts/milestones/`**
[name='milestones-recent-posts']

    *   Description: Retrieves recent posts with milestone tag. Supports cursor-based pagination.
    *   Request: `GET`
    *   Authentication: Optional (some fields like `has_liked` depend on authentication)
    *   Query Parameters:
        *   `page`: (optional, default: 1) The page number for pagination.
        *   `page_size`: (optional, default: 10) Number of posts to return per page.
        *   `session_id`: (optional) A unique string to ensure consistent feed order for a session. If not provided, a new session ID is generated.
    *   Response (200 OK): Returns a paginated list of recent posts with milestone tag.
        ```json
        {
            "results": [
                {
                    "id": "post_id",
                    "content": "Post content",
                    "timestamp": "2025-07-22T12:34:56Z",
                    "author_id": "org_user_id",
                    "has_liked": false,
                    "has_rewarded": true,
                    "media_urls": [],
                    // ...other post fields...
                }
            ],
            "session_id": "abc123-session-id",
            "page": 1,
            "page_size": 10,
            "has_next": true
        }
        ```
    *   Response (200 OK, empty): If no posts are found.
        ```json
        {
            "results": [],
            "session_id": "abc123-session-id",
            "page": 1,
            "page_size": 10,
            "has_next": false
        }
        ```
    *   Response (500 Internal Server Error): If an error occurs.
        ```json
        {
            "detail": "Error fetching posts."
        }
        ```

*   **`GET /official`**  [name='exclusive-orgs-recent-posts']

    *   Description: Retrieves recent posts from organizations marked as `exclusive=True`. Supports cursor-based pagination.
    *   Request: `GET`
    *   Authentication: Optional (some fields like `has_liked` depend on authentication)
    *   Query Parameters:
        *   `page`: (optional, default: 1) The page number for pagination.
        *   `page_size`: (optional, default: 10) Number of posts to return per page.
        *   `session_id`: (optional) A unique string to ensure consistent feed order for a session. If not provided, a new session ID is generated.
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
            "session_id": "abc123-session-id",
            "page": 1,
            "page_size": 10,
            "has_next": true
        }
        ```
    *   Response (200 OK, empty): If no exclusive organizations or posts are found.
        ```json
        {
            "results": [],
            "session_id": "abc123-session-id",
            "page": 1,
            "page_size": 10,
            "has_next": false
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

---

## Knowme (Walls & Members) ✅

A lightweight feature for creating **Walls** and letting people **join** them with short profiles (optional photo). Images are uploaded to Firebase Storage and the API stores a public `photo_url` on the member record.

**Base paths:**
- `POST /api/v1/walls/` — Create a new wall (name, description, creator_email)
- `GET /api/v1/walls/<uuid:id>/` — Retrieve wall details (name, description, member_count)
- `GET /api/v1/walls/<uuid:wall_id>/members/` — List wall members (paginated)
- `POST /api/v1/walls/<uuid:wall_id>/join/` — Join a wall (multipart form-data, optional image upload)

### Models & important fields 🔧
- **Wall**: `id` (UUID), `name`, `description`, `creator_email`, `created_at`
- **WallMember**: `id`, `wall` (FK), `full_name`, `contact_info`, `interests`, `photo_url` (nullable), `joined_at`

### Join Wall (Usage notes) 💡
- Accepts `multipart/form-data` with fields: `full_name`, `contact_info`, `interests`, and optional file field `photo`.
- The serializer accepts a write-only `photo` field; the view uploads the file to Firebase and stores the public `photo_url` on the `WallMember`.
- Photo upload path: `knowme/<wall_id>/<random>.ext` in Firebase Storage. Public URL format:
  `https://firebasestorage.googleapis.com/v0/b/<bucket-name>/o/<path>?alt=media`
- If Firebase upload fails, the member is still created but `photo_url` may be `null` (upload errors are logged).
- The operation is **open (AllowAny)** — authentication is not required.

### Constraints & behaviors ⚠️
- A wall is limited to **300 members**; attempts to join after the limit will return `400 Bad Request` with a message about the limit.
- Member listing is paginated (default `page_size=50`, `max_page_size=100`). Use `?page=` and `?page_size=` query params.
- On successful join, the backend schedules an asynchronous email to the wall creator with a link to the wall: `{FRONTEND_URL}/walls/{wall_id}` (via Celery task). Email scheduling failures do NOT block member creation.

### Example: Join (multipart)
Request (multipart/form-data):
- `full_name=Jane Doe`
- `contact_info=jane@example.com`
- `interests=Photography, Art`
- `photo` = image file (optional)

Response (201 Created):
```json
{
  "id": "<member_id>",
  "full_name": "Jane Doe",
  "contact_info": "jane@example.com",
  "interests": "Photography, Art",
  "photo_url": "https://... (or null)",
  "joined_at": "2025-01-01T12:00:00Z"
}
```

### Example: List Members (paginated)
`GET /api/v1/walls/<wall_id>/members/?page=1`

Response (200 OK):
```json
{
  "count": 123,
  "next": "...",
  "previous": null,
  "results": [
    {
      "id": "...",
      "full_name": "Jane Doe",
      "contact_info": "jane@example.com",
      "interests": "Photography, Art",
      "photo_url": "https://...",
      "joined_at": "2025-01-01T12:00:00Z"
    }
  ]
}
```

---

# Comments API Documentation

---

## Endpoints

### 1. Create a Comment or Reply  
`POST /api/posts/<post_id>/comments/create/`

- **Description:**  
  Create a new comment on a post, or reply to an existing comment.
- **Authentication:**  
  Required (JWT, verified user)
- **Request Body:**
    ```json
    {
      "text": "Your comment text",
      "parent_comment_id": "optional_parent_comment_id" // Only for replies
    }
    ```
- **Response (201 Created):**
    ```json
    {
      "id": "comment_id",
      "post_id": "post_id",
      "author_id": "user_id",
      "author_username": "user@example.com",
      "text": "Your comment text",
      "timestamp": "2025-09-17T12:34:56Z",
      "parent_comment_id": "optional_parent_comment_id",
      "reply_count": 0
    }
    ```
- **Notes:**
  - If `parent_comment_id` is provided, the comment is treated as a reply.
  - Increments `comment_count` on the post and `reply_count` on the parent comment (for replies).
  - Sends push notifications to post author or parent comment author.

---

### 2. List Comments  
`GET /api/posts/<post_id>/comments/`

- **Description:**  
  List all comments and replies for a post, paginated.
- **Authentication:**  
  Optional
- **Query Parameters:**  
  - `page_size` (default: 10)
  - `page` (default: 1)
- **Response (200 OK):**
    ```json
    {
      "results": [
        {
          "id": "comment_id",
          "author_id": "user_id",
          "text": "Comment text",
          "timestamp": "...",
          "reply_count": 2,
          "replies": [ ...nested replies... ]
        }
        // ...
      ],
      "next_page": 2,
      "total_comments": 15
    }
    ```
- **Notes:**
  - Returns paginated top-level comments with nested replies.
  - Author info is hydrated from PostgreSQL.

---

### 3. Retrieve, Edit, or Delete a Comment  
`GET /api/posts/<post_id>/comments/<comment_id>/`  
`PUT /api/posts/<post_id>/comments/<comment_id>/`  
`DELETE /api/posts/<post_id>/comments/<comment_id>/`

- **Description:**  
  Retrieve, update, or delete a specific comment.
- **Authentication:**  
  Required for edit/delete (JWT, verified user)
- **Request Body (PUT):**
    ```json
    {
      "text": "Updated comment text"
    }
    ```
- **Response:**  
  - `200 OK` for GET/PUT, `204 No Content` for DELETE.
  - Error responses for unauthorized access or comment not found.
- **Notes:**
  - Only the comment author can edit or delete.
  - Deleting a top-level comment also deletes its replies.
  - Updates `comment_count` and `reply_count` as needed.

---

## General Notes

- All comment endpoints use Firestore transactions for atomic updates.
- Replies are stored as comments with a `parent_comment_id` field.
- Author info is hydrated from PostgreSQL for richer responses.
- Error responses are descriptive for missing resources or permissions.
- Push notifications are sent for new comments and replies.

---

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


### `POST /api/v1/posts/batch-view/` [name='batch-post-view-increment']

- **Description:**  
  Increments the view count for multiple posts in a single request.  
  This endpoint is intended to be called by the frontend when posts actually appear in the user's viewport (e.g., detected via Intersection Observer).

- **Request:**  
  `POST /api/v1/posts/batch-view/`

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

#### **Department Follow Suggestions**

- **`GET /follow-department/`**  
  *Suggests students to follow from the authenticated user's department. Provides personalized follow recommendations based on shared department.*

- **Authentication:**  
  Required (JWT)

- **Parameters:**
  - No parameters required. Uses authenticated user's department automatically.

- **Response (200 OK):**
    ```json
    {
        "results": [
            {
                "type": "student",
                "id": "string",
                "user_id": "string",
                "name": "string",
                "department": "string",
                "profile_pic_url": "string",
                "is_verified": boolean,
                "bio": "string"
            }
        ]
    }
    ```

- **Error Responses:**
  - `401 Unauthorized`: Authentication required
  - `403 Forbidden`: User is not a student
  - `404 Not Found`: User's student profile not found
  - `400 Bad Request`: User has no department set

- **Notes:**
  - Limited to suggesting 20 students at a time
  - Only suggests students from the same department
  - Excludes students that are already being followed
  - Excludes the requesting user from suggestions
  - Results are randomized for variety
  - Includes basic profile information for easy display

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

**NOTIFICATION DATA PAYLOAD**

## I. Standard Payload Fields

All notifications contain these fields, with the required values being context-specific. The client should primarily use the **`type`** field to determine the necessary routing logic.

| Field Name | Type | Description | Purpose for Client Routing |
| :--- | :--- | :--- | :--- |
| **`type`** | `string` | Defines the specific **event** that occurred (e.g., `'comment'`, `'like'`, `'follow'`, `'new_post'`). | **Primary discriminator** for client-side routing logic. |
| **`post_id`** | `string` | The **Firestore ID** of the target post. | Used to build the deep-link path: `/posts/:post_id`. |
| **`comment_id`** | `string` | The **Firestore ID** of a new comment or reply. | **Contextual cue**: Used to scroll to or highlight the specific comment on the Post Screen. |
| **`follower_id`** | `string` | The **PostgreSQL ID** of the user who initiated a follow. | Used for redirection to a User Profile Screen: `/profile/:user_id`. |
| **`commenter_id` / `liker_id`** | `string` | PostgreSQL ID of the user who performed the action. | Used for display or secondary profile lookup. |

---

## II. Client Redirection Logic by Event Type

The client application's router should switch on the value of the **`type`** field to determine the correct target route.

### 1. New Comment or Reply (`type: 'comment'` or `'reply'`)

This notification redirects the user to the parent post and highlights the new comment.

| Field Used | Action | Client Route Structure |
| :--- | :--- | :--- |
| **`post_id`** | Direct to the Post Screen. | `/posts/:post_id` |
| **`comment_id`** | Pass as a query parameter for scrolling/highlighting. | `?commentId=:comment_id` |

---


```json
{
    "type": "comment",
    "post_id": "fskj34klj5h6g7f8d9s0a1",
    "comment_id": "a1b2c3d4e5f6g7h8i9j0k1",
    "commenter_id": "23456789-abcd-efgh-ijkl-1234567890ab",
    "commenter_profile_pic_url":"hbvkyfqvegwfvjwgvfoyewvf"
}
```

### 2. Post Like or New Post (type: 'like' or 'new_post')

These actions redirect the user directly to the target post.

| Field Used | Action | Client Route Structure |
| :--- | :--- | :--- |
| **`post_id`** | Direct to the Post Screen. | `/posts/:post_id` |


**Example Server Payload (Like):**


```json
{
    "type": "like",
    "post_id": "fskj34klj5h6g7f8d9s0a1",
    "liker_id": "23456789-abcd-efgh-ijkl-1234567890ab" 
}
```

### 3. New Follow (type: 'follow')

This action redirects the user to the profile of the user who initiated the follow (the follower).

| Field Used | Action | Client Route Structure |
| :--- | :--- | :--- |
| **`follower_display_name_slug`** | Direct to the User Profile Screen. | `/profile/:follower_display_name_slug` |


**Example Server Payload:**

```json
{
    "type": "follow",
    "follower_id": "12345678-abcd-efgh-ijkl-000000000001",
    "follower_name": "ashdcugwiugwrf",
    "follower_display_name_slug": "dshwydyd-1",
    "follower_profile_pic_url":"",
}
```

## III. Client Implementation Notes
- Prioritization: The client should prioritize deep-linking based on the presence of the necessary ID fields. The check should prioritize follower_id for 'follow' events, and post_id for all others.

- Route Construction: The client must dynamically construct the route path, appending optional query parameters (?commentId=...) only when the corresponding ID is present.

- Fallback: If the notification data lacks the required ID for a deep link, the application should fall back to a safe route, such as the main /notifications screen or the Home Feed.



### Point Submission (RewardPointCreateView)

#### 1. Reward Point Submission (UPSERT)
    This endpoint allows an authenticated user to submit points (a reward) to a post, initiating a transaction that is validated against Firestore data before being saved to the local database.

    Detail	Specification
    Name	reward-submit
    URL	/api/v1/reward-points/
    Method	POST
    Authentication	Required (IsAuthenticated)
    Logic	UPSERT: If the giver has previously rewarded this post_id, the existing points are updated to the new value. If not, a new record is created. (Max 5 points total per user per post enforced).

    Request Payload (POST Body)
    Field	Type	Description
    post_id	string (max 100)	The unique ID of the Post document in Firestore.
    points	integer	The point value to assign (Must be between 1 and 5).

```
JSON

{
    "post_id": "fkewp0ldfIxpT3m7uYGh",
    "points": 4
}
```

Data Flow Summary (on POST)
Serializer receives post_id and points.

Serializer calls Firebase SDK with post_id to retrieve the post's author_id (local Postgres ID).

Serializer enforces the 1-5 point limit.

Transaction is saved/updated in the Postgres RewardPointTransaction table, linking the giver, the firestore_post_id, and the denormalized post_author.

#### 2. User Total Points Retrieval (PUBLIC)
    This endpoint retrieves the aggregated total points received by a specific user across all their posts. This information is publicly viewable by any authenticated user.

    Detail	Specification
    Name	profile-points-public
    URL	/api/v1/profile/points/<int:pk>/
    Method	GET
    Authentication	Required (IsAuthenticated)
    Logic	Aggregates the SUM(points) from all RewardPointTransaction records where the post_author matches the requested User ID (pk).


    Request Payload
    No request body is required. The target user is identified via the URL path.

    Success Response (HTTP 200 OK)
    Field	Type	Description
    id	integer	The local ID (pk) of the user whose score is being returned.
    username	string	The username of the user.
    total_points_received	integer	The total number of points received from all rewards across all their posts.


```
JSON

/* Requesting the score for User ID 42 */
/* GET /api/v1/profile/points/42/ */
{
    "id": 42,
    "username": "UserB",
    "total_points_received": 156
}
```

### Social Links Update
This endpoint allows an authenticated user to update their social media and website links. It performs a partial update, meaning only the fields provided in the payload will be changed.

Detail	Specification
Name	user-social-links-update
URL	/api/v1/profile/social-links/
Method	PATCH
Authentication	Required (IsAuthenticated)
Logic	Updates the corresponding fields directly on the authenticated User model instance. Empty strings ("") in the request body are saved as None (clearing the link).
Request Payload (PATCH Body)
Field	Type	Description
linkedin_url	string	The full URL for the user's LinkedIn profile.
instagram_url	string	The full URL for the user's Instagram profile.
twitter_url	string	The full URL for the user's X (Twitter) profile.
website_url	string	The full URL for the user's personal/organization website.
Example Request (PATCH):

```
JSON

{
    "linkedin_url": "https://linkedin.com/in/varsigram_dev",
    "instagram_url": "https://instagram.com/varsigram_official"
}
```

Success Response (HTTP 200 OK)
The response returns the updated social link data for the authenticated user.

```
JSON

{
    "linkedin_url": "https://linkedin.com/in/varsigram_dev",
    "instagram_url": "https://instagram.com/varsigram_official",
    "twitter_url": null,
    "website_url": null
}
```

Error Response Example (HTTP 400 Bad Request)
If an invalid URL format is submitted:

```
JSON

{
    "linkedin_url": [
        "Enter a valid URL."
    ]
}
```

## Leaderboards

This section explains exactly how the frontend should call and render leaderboards, what query parameters are supported, the expected response shape, and operational notes (keys, tasks, backfills).

Base paths (all under `/api/v1/`):

- Weekly: `/api/v1/leaderboard/rewards/weekly/` (name: `reward-weekly-leaderboard`)
- Monthly: `/api/v1/leaderboard/rewards/monthly/` (name: `reward-monthly-leaderboard`)
- Yearly: `/api/v1/leaderboard/rewards/alltime/` (name: `reward-alltime-leaderboard`)

Authentication
- All leaderboard endpoints require authentication (JWT). Include header:

```http
Authorization: Bearer <your_token>
```

Common query parameters
- `limit` — integer. Number of rows to return. Default: 100 (top-100). Maximum: backend may cap; keep requests to <= 500.

Weekly endpoint specifics
- Supported query params:
    - `limit` (optional, default 100)
    - `week_start` (optional) — choose the week by passing either:
        - an ISO date inside the week (YYYY-MM-DD), or
        - an ISO week string like `YYYY-Www` (e.g. `2025-W45`).

- Behavior:
    - If `week_start` is omitted, the server uses the current UTC ISO week.
    - The server reads Redis key `leaderboard:points:weekly:<YYYY>-W<WW>` (example: `leaderboard:points:weekly:2025-W45`).
    - If the requested key is missing, the frontend can either show an empty view or request a backfill via the ops team (see Backfill below).

- Example request (fetch top 10 for the week containing 2025-11-03):

```bash
curl -H "Authorization: Bearer $TOKEN" \
    "https://<api-host>/api/v1/leaderboard/rewards/weekly/?limit=10&week_start=2025-11-03"
```

Monthly endpoint specifics
- Supported query params:
    - `limit` (optional, default 100)
    - `month` (optional) — `YYYY-MM` (e.g. `2025-11`). If omitted, current UTC month is used.

Alltime endpoint specifics
- Supported query params:
    - `limit` (optional, default 100)

- Note: Current implementation returns the ALL-TIME snapshot (Redis key `leaderboard:points:alltime`). If you need calendar-year snapshots, ask the backend to add `yearly` keys or a filtering endpoint.

Response schema (successful 200 OK)
```json
{
    "results": [
        {
            "user_id": "42",
            "score": 4120,
            "name": "Alice",
            "profile_pic_url": "https://...",
        }
        // ... up to `limit` rows
    ]
}
```

Client rendering guidance
- Display rank, name, score, and avatar.
- Use `display_name_slug` to deep-link to profile pages: `/profile/:display_name_slug`.
- For the weekly view allow a week picker UI that sends `week_start` as an ISO date within the selected week. When the user selects a calendar week, compute any date within that week and send it as `week_start`.

Edge cases & fallbacks
- Missing Redis key: If the key for a requested period is not present, show an empty leaderboard and a small help text like "No data for this period yet". If historical data is required, request a backfill.
- Stale data: Redis receives incremental updates via Django signals on each reward save; periodic Celery recomputes reconcile any drift. Assume near-real-time but accept small delays.

Redis keys (for debugging and verification)
- All-time: `leaderboard:points:alltime`
- Daily: `leaderboard:points:daily:<YYYY-MM-DD>`
- Weekly: `leaderboard:points:weekly:<YYYY>-W<WW>` (ISO week)
- Monthly: `leaderboard:points:monthly:<YYYY>-<MM>`

Server-side tasks & backfills (ops)
- Celery tasks in `postMang.tasks`:
    - `recompute_points_daily(date_iso: str)` — recomputes the daily leaderboard for the given date (YYYY-MM-DD)
    - `recompute_points_weekly(date_iso: str)` — recomputes the weekly leaderboard for the ISO week that contains `date_iso` (YYYY-MM-DD)
    - `recompute_points_alltime()` — recomputes the all-time leaderboard

### Posts leaderboard (top users by number of posts)

We also expose leaderboards for users with the highest number of posts. These are updated in near-real-time when posts are created via the API and backed by Redis sorted sets.

Base paths (all under `/api/v1/`):

- Weekly: `/api/v1/leaderboard/posts/weekly/` (name: `posts-weekly-leaderboard`)
- Monthly: `/api/v1/leaderboard/posts/monthly/` (name: `posts-monthly-leaderboard`)
- All-time: `/api/v1/leaderboard/posts/alltime/` (name: `posts-alltime-leaderboard`)

Query parameters
- `limit` — integer. Number of rows to return. Default: 100.
- `week_start` — for weekly endpoint, same formats as rewards (YYYY-MM-DD or YYYY-Www).

Redis keys used
- All-time: `leaderboard:posts:alltime`
- Daily: `leaderboard:posts:daily:<YYYY-MM-DD>`
- Weekly: `leaderboard:posts:weekly:<YYYY>-W<WW>`
- Monthly: `leaderboard:posts:monthly:<YYYY>-<MM>`

Example request (top-10 all-time posters):

```bash
curl -H "Authorization: Bearer $TOKEN" \
    "https://<api-host>/api/v1/leaderboard/posts/alltime/?limit=10"
```

Response schema (200 OK)
```json
{
    "results": [
        {"user_id": "42", "score": 120, "name": "Alice", "profile_pic_url": "https://..."},
        {"user_id": "17", "score": 98, "name": "Bob", "profile_pic_url": null}
    ]
}
```

Operational notes
- Post counts are incremented when posts are created via the API (`POST /api/v1/posts/`). If posts are created outside the API (directly in Firestore), you may need to run a backfill to populate historical counts using the management command.

### Top posters endpoint (fallback & on-demand compute)

We also provide a convenience endpoint to list users with the highest total posts even if you don't run periodic backfills.

- URL: `/api/v1/users/top-posters/` (name: `users-top-posters`)
- Query params:
    - `limit` (optional, default 100)
    - `compute` (optional) — set to `true` to compute counts from Firestore on-demand if no cached Redis data exists. This operation can be slow for large datasets.

- Behavior:
    - If Redis key `leaderboard:posts:alltime` is present, the endpoint returns results from Redis.
    - If Redis key is missing and `compute=true` is provided, the server will synchronously scan Firestore to compute counts and return top-N (and attempt to populate Redis for future calls).
    - If Redis key is missing and `compute` is not provided, the endpoint now enqueues a background Celery backfill task (`recompute_posts_alltime`) and returns `202 Accepted`. Retry after a short while to read cached results.

Example (force compute):

```bash
curl -H "Authorization: Bearer $TOKEN" \
    "https://<api-host>/api/v1/users/top-posters/?limit=10&compute=true"
```


---