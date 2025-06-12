"""
ASGI config for varsigram project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'varsigram.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    # You can add websocket protocols here if you use Channels
})
