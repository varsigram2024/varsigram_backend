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

*   **`GET /users/search/?q=<query>`**  [name='search']

    *   Description: Searches for users based on a query string.
    *   Request: `GET`
    *   Query Parameters:
        *   `q`: The search query.
        *   `type`: "student" or "organization" (optional)
        *   `faculty`, `department`: (optional, for student search)
    *   Response (200 OK): Returns a list of matching users.

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

*   **`GET /posts/`** and **`POST /posts/`**  [name='post-list-create']

    *   **GET**: Retrieves a list of posts.
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

    *   Retrieves comments for a specific post.
    *   Request: GET

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

*   **`GET /users/<str:user_id>/posts/`**  [name='user-posts']

    *   Retrieves all posts by a specific user.
    *   Request: GET
<!-- 
*   **`GET /posts/search/?q=<query>`**  [name='post-search']

    *   Searches for posts based on a query string.
    *   Request: GET
    *   Query Parameters:
        *   `q`: The search query.
    *   Response (200 OK): Returns a list of matching posts. -->

*   **`GET /feed/`**  [name='feed']

    *   Retrieves the authenticated user's feed, including posts from followed organizations, users in the same department/faculty/religion, and the user's own posts and shares.
    *   Authentication: Required
    *   Query Parameters:
        *   `shared`: If present, includes shared posts in the feed.

*   **`GET /trending/`**  [name='trending-posts']

    *   Retrieves trending posts (based on likes, shares, or other criteria).
    *   Request: GET
    *   Response (200 OK): Returns a list of trending posts.

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
