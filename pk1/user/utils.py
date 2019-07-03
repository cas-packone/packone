from threading import local
from engines.models import Cluster

_user = local()

class CurrentUserMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        _user.value = request.user
        _user.space=None
        # if not request.user.is_anonymous:# TODO a workaround to allow drf anonymous user to access current space
        parts=request.get_full_path().split('/')
        if len(parts)>2 and parts[1]=='space':
            _user.space=Cluster.objects.get(pk=parts[2])
        request.space=_user.space
        return self.get_response(request)

def get_current_user():
    return _user.value

def get_space():
    return _user.space