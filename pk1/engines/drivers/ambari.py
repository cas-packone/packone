from ambari.client import Client

class Driver(object):
    def __init__(self, portal):
        self.portal=portal
        self.client=Client(portal)
    @property
    def stack_version(self):
        stack=self.client.cluster.stack
        return stack.name+'-'+stack.version
    def get_engine_host(self, engine):
        return self.client.cluster.hosts[-1].name
    @property
    def stack_engines(self):
        return self.client.stack.services
    @property
    def cluster_engines(self):
        return self.client.cluster.services
    def list_components(self, engine):
        return self.client.stack.get_service(engine).components
    @property
    def metrics(self):
        m=[]
        for h in self.client.cluster.hosts:
            m.append({h.name: h.metrics})
        return m
