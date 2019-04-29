from pk1.remedy.ambari.client import APIClient

init_script='wget -q http://public-repo-1.hortonworks.com/ambari/centos7/2.x/updates/2.7.3.0/ambari.repo -O /etc/yum.repos.d/ambari.repo\n'
init_script+='wget -q http://public-repo-1.hortonworks.com/HDP/centos7/3.x/updates/3.1.0.0/hdp.repo -O /etc/yum.repos.d/hdp.repo\n'
init_script+='wget -q http://public-repo-1.hortonworks.com/HDP-GPL/centos7/3.x/updates/3.1.0.0/hdp.gpl.repo -O /etc/yum.repos.d/hdp.gpl.repo\n\n'
init_script+='yum -qy install ambari-server >/dev/null 2>&1\n\n'
init_script+='ambari-server setup -s >/dev/null\n'
init_script+='ambari-server start'

repo_script=''#TODO

def setup_images():
    scripts={
        'master1.packone':init_script
    }
    return scripts

def list_engines(host):
    c=APIClient('http://{}:8080'.format(host))
    engines=[]
    for s in c.stack_services():
        engines.append({
            'name':s['StackServices']['service_name'],
            'description':s['StackServices']['comments']
        })
    return engines

def list_components(host,engine):
    c=APIClient('http://{}:8080'.format(host))
    components=[]
    for cpn in c.stack_service_components(service_name=engine):
        components.append({
            'name':cpn['StackServiceComponents']['component_name'],
            'type':cpn['StackServiceComponents']['component_category'].lower()
        })
    return components