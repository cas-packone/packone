from django.apps import AppConfig

class DataConfig(AppConfig):
    name = 'data'
    def ready(self):
        import data.signals
