from .h3cloudos import Driver as H3CDriver
from .h3cloudos import Image as H3CImage
from .h3cloudos import InstanceManager#TODO  for InstanceManager.mountable_status

class Driver(H3CDriver):
    def __init__(self, cloud):
        cloud.platform_credential['endpoint']='http://159.226.245.2:9000'
        H3CDriver.__init__(self, cloud)

class Image(H3CImage):
    def __init__(self, info):
        if info['name']=='CentOS7-YouHua':
            info['name']+='-GenericCloud'
        H3CImage.__init__(self, info)