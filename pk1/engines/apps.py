from django.apps import AppConfig

class EnginesConfig(AppConfig):
    name = 'engines'
    def ready(self):
        import engines.signals
