from threading import Thread
import time 
from django.core.management.base import BaseCommand
from clouds.models import Instance

class Command(BaseCommand):
    help = 'monitor cloud resource periodly'
    def handle(self, *args, **options):
        while True:
            for instance in Instance.objects.exclude(uuid=None):
                Thread(target=instance.monitor).start()
                time.sleep(0.1)
            time.sleep(300)