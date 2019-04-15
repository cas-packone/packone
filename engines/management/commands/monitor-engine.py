from threading import Thread
import time 
from django.core.management.base import BaseCommand, CommandError
from engines.models import Cluster, COMPONENT_STATUS
class Command(BaseCommand):
    help = 'monitor engines periodly'
    def handle(self, *args, **options):
        while True:
            for c in Cluster.objects.all():
                c.status=COMPONENT_STATUS.running.value
                for e in c.engines.all():
                    if e.status(c)!=COMPONENT_STATUS.running.value:
                        c.status=COMPONENT_STATUS.stop.value
                        break
                c.save()
            time.sleep(300)