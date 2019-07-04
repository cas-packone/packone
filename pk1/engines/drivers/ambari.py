from ambari.client import Client

def get_engine_host(portal, engine):
    c=Client(portal)
    return c.cluster.hosts[-1].name

def list_engines(portal):
    return Client(portal).stack.services

def list_components(portal,engine):
    c=Client(portal)
    return c.stack.get_service(engine).components

def get_metrics(portal):
    c=Client(portal)
    m={}
    for h in c.cluster.hosts:
        m[h.name]=h.metrics
    return m
