from ambari.client import Client

def get_engine_host(portal, engine):
    c=Client(portal)
    return c.cluster.hosts[-1].name

def list_engines(portal):
    c=Client(portal)
    engines=[]
    for s in c.stack_services():
        engines.append({
            'name':s['StackServices']['service_name'],
            'description':s['StackServices']['comments']
        })
    return engines

def list_components(portal,engine):
    c=Client(portal)
    components=[]
    for cpn in c.stack_service_components(service_name=engine):
        components.append({
            'name':cpn['StackServiceComponents']['component_name'],
            'type':cpn['StackServiceComponents']['component_category'].lower()
        })
    return components