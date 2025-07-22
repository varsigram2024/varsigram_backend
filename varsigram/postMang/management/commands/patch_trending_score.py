from django.core.management.base import BaseCommand
from postMang.apps import get_firestore_db

class Command(BaseCommand):
    help = 'Patch posts missing trending_score in Firestore'

    def handle(self, *args, **kwargs):
        db = get_firestore_db()
        patched = 0
        for doc in db.collection('posts').stream():
            data = doc.to_dict()
            if 'trending_score' not in data:
                doc.reference.update({'trending_score': 0})
                patched += 1
        self.stdout.write(self.style.SUCCESS(f'Patched {patched} posts.'))
