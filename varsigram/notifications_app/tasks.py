from celery import shared_task
from .utils import send_push_notification
from users.models import User

@shared_task
def notify_all_users_new_post(author_id, author_name, post_content, post_id, author_profile_pic_url):
    users = User.objects.exclude(id=author_id)
    for user in users:
        send_push_notification(
            user=user,
            title="New Post",
            body=f"{author_name} just posted: {post_content[:50]}...",
            data={"type": "new_post", "post_id": post_id, "author_profile_pic_url": author_profile_pic_url}
        )