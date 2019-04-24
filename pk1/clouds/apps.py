from django.apps import AppConfig

class CloudsConfig(AppConfig):
    name = 'clouds'
    def ready(self):
        import clouds.signals
