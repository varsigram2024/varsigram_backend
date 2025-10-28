from celery import shared_task
from .utils import send_push_notification
from users.models import User

@shared_task
def notify_all_users_new_post(author_id, author_name, post_content, post_id, author_profile_pic_url=None, **kwargs):
    """Notify all users about a new post.

    The task accepts an optional `author_profile_pic_url` and extra kwargs to
    remain compatible with previously queued tasks that may include different
    argument sets.
    """
    users = User.objects.exclude(id=author_id)
    for user in users:
        data_payload = {"type": "new_post", "post_id": post_id}
        if author_profile_pic_url:
            data_payload["author_profile_pic_url"] = author_profile_pic_url

        send_push_notification(
            user=user,
            title="New Post",
            body=f"{author_name} just posted: {post_content[:50]}...",
            data=data_payload
        )