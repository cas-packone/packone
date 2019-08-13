from .h3cloudos import Driver as H3CDriver
from .h3cloudos import ImageManager as H3CImageManager
from .h3cloudos import Image
from .h3cloudos import InstanceManager#TODO  for InstanceManager.mountable_status

class Driver(H3CDriver):
    def __init__(self, cloud):
        if not 'nova-availability_zone' in cloud.platform_credential: cloud.platform_credential['nova-availability_zone']="CASCloud01"
        if not 'cinder-availability_zone' in cloud.platform_credential: cloud.platform_credential['cinder-availability_zone']="cstcloud_cinder01"
        cloud.platform_credential['endpoint']='http://159.226.245.2:9000'
        H3CDriver.__init__(self, cloud)
        self.images=ImageManager(self)

class ImageManager(H3CImageManager):
    def list(self):
        images=[]
        for item in self.driver._get('/v2/images')['images']:
            if item['name']=='CentOS7-YouHua':
                item['name']+='-GenericCloud'
            images.append(Image(item))
        return images