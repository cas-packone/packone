from .h3cloudos import Driver as H3CDriver

class Driver(H3CDriver):
    def __init__(self, cloud, credential):
        credential['endpoint']='http://159.226.245.2:9000'
        H3CDriver.__init__(self, cloud, credential)