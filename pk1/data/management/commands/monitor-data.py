
from threading import Thread
import datetime, time 
from django.core.management.base import BaseCommand, CommandError
from data.models import Space
class Command(BaseCommand):
    help = 'monitor data instances periodly'
    def handle(self, *args, **options):
        while True:
            for s in Space.objects.all():
                p=s.pilot
                for e in p.engines.all():
                    pes=e.status(p)
                    dis=s.datainstance_set.filter(engine__component__in=e.components.all())
                    for di in dis:
                        di.status=pes
                        di.save()
            time.sleep(300)