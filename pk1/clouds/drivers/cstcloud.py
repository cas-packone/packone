from .h3cloudos import Driver as H3CDriver
from .h3cloudos import ImageManager as H3CImageManager
from .h3cloudos import Image


class Driver(H3CDriver):
    def __init__(self, cloud):
        cloud.platform_credential['endpoint']='http://159.226.245.2:9000'
        H3CDriver.__init__(self, cloud)
        self.images=ImageManager(self)

class ImageManager(H3CImageManager):
    def list(self):
        images=[]
        for item in self.driver._tenant_get('/images')['images']:
            if item['name']=='CentOS7-YouHua':
                item['name']+='-GenericCloud'
            images.append(Image(item))
        return images