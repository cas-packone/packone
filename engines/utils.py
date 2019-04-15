
import requests
import simplejson

headers = {
    'X-Requested-By': 'ambari',
}

def ambari_request(username,passwd,url,data=None):
    print(url)
    ret=''
    if data:
        print(data)
        ret=requests.put(url, headers=headers, data=data, auth=(username,passwd))
        try:
            return ret.json()
        except simplejson.errors.JSONDecodeError as e:
            return ret
    else:
        ret=requests.get(url, headers=headers, auth=(username,passwd))
        try:
            return ret.json()
        except simplejson.errors.JSONDecodeError as e:
            return ret

#curl -i -u admin:admin -H "X-Requested-By: ambari"  -X GET http://localhost:8080/api/v1/clusters/
def ambari_get_cluster(username,passwd,ambari_server_url):
    cname=ambari_request(username,passwd,ambari_server_url+'/api/v1/clusters/')['items'][0]['Clusters']['cluster_name']
    print(cname)
    return cname

#ref:https://community.hortonworks.com/answers/88215/view.html
#curl -i -u admin:admin -H "X-Requested-By: ambari"  -X PUT  -d '{"RequestInfo":{"context":"_PARSE_.START.ALL_SERVICES","operation_level":{"level":"CLUSTER","cluster_name":"emr"}},"Body":{"ServiceInfo":{"state":"STARTED"}}}' http://localhost:8080/api/v1/clusters/emr/services
def ambari_service_start_all(username,passwd,ambari_server_url):
    cluster_name=ambari_get_cluster(username,passwd,ambari_server_url)
    url="{}/api/v1/clusters/{}/services".format(ambari_server_url,cluster_name)
    data='{"RequestInfo":{"context":"_PARSE_.START.ALL_SERVICES","operation_level":{"level":"CLUSTER","cluster_name":"'
    data+=cluster_name
    data+='"}},"Body":{"ServiceInfo":{"state":"STARTED"}}}'
    return ambari_request(username,passwd,url,data)

#ref:https://community.hortonworks.com/answers/88215/view.html
#curl -i -u admin:admin -H "X-Requested-By: ambari"  -X PUT  -d '{"RequestInfo":{"context":"_PARSE_.STOP.ALL_SERVICES","operation_level":{"level":"CLUSTER","cluster_name":"emr"}},"Body":{"ServiceInfo":{"state":"INSTALLED"}}}'  http://localhost:8080/api/v1/clusters/emr/services
def ambari_service_stop_all(username,passwd,ambari_server_url):
    cluster_name=ambari_get_cluster(username,passwd,ambari_server_url)
    url="{}/api/v1/clusters/{}/services".format(ambari_server_url,cluster_name)
    data='{"RequestInfo":{"context":"_PARSE_.STOP.ALL_SERVICES","operation_level":{"level":"CLUSTER","cluster_name":"'
    data+=cluster_name
    data+='"}},"Body":{"ServiceInfo":{"state":"INSTALLED"}}}'
    return ambari_request(username,passwd,url,data)

#curl -k -u admin:admin -H "X-Requested-By:ambari" -i -X PUT -d '{"RequestInfo":{"context":"Turn on Maintenance for YARN"},"Body":{"ServiceInfo":{"maintenance_state":"ON"}}}' http://localhost:8080/api/v1/clusters/emr/services/YARN
def ambari_service_maintenance_on(username,passwd,ambari_server_url,service_name):
    cluster_name=ambari_get_cluster(username,passwd,ambari_server_url)
    url="{}/api/v1/clusters/{}/services/{}".format(ambari_server_url,cluster_name,service_name)
    data='{"RequestInfo":{"context":"Turn on Maintenance for '+service_name+'"},"Body":{"ServiceInfo":{"maintenance_state":"ON"}}}'
    return ambari_request(username,passwd,url,data)

#curl -k -u admin:admin -H "X-Requested-By:ambari" -i -X PUT -d '{"RequestInfo":{"context":"Turn off Maintenance for YARN"},"Body":{"ServiceInfo":{"maintenance_state":"OFF"}}}' http://localhost:8080/api/v1/clusters/emr/services/YARN
def ambari_service_maintenance_off(username,passwd,ambari_server_url,service_name):
    cluster_name=ambari_get_cluster(username,passwd,ambari_server_url)
    url="{}/api/v1/clusters/{}/services/{}".format(ambari_server_url,cluster_name,service_name)
    data='{"RequestInfo":{"context":"Turn off Maintenance for '+service_name+'"},"Body":{"ServiceInfo":{"maintenance_state":"OFF"}}}'
    return ambari_request(username,passwd,url,data)

#curl -u admin:passwd  -H 'X-Requested-By: ambari' -X PUT -d '{"RequestInfo": {"context" :"Start service"}, "Body": {"ServiceInfo": {"state": "STARTED"}}}' http://<AMBARI_SERVER_HOSTNAME>:8080/api/v1/clusters/<CLUSTER_NAME>/services/<Service_name>
def ambari_service_start(username,passwd,ambari_server_url,service_name):
    cluster_name=ambari_get_cluster(username,passwd,ambari_server_url)
    url="{}/api/v1/clusters/{}/services/{}".format(ambari_server_url,cluster_name,service_name)
    data='{"RequestInfo": {"context" :"Start service"}, "Body": {"ServiceInfo": {"state": "STARTED"}}}'
    return ambari_request(username,passwd,url,data)
    
#curl -u admin:passwd  -H 'X-Requested-By: ambari' -X PUT -d '{"RequestInfo": {"context" :"Stop service "}, "Body": {"ServiceInfo": {"state": "INSTALLED"}}}' http://<AMBARI_SERVER_HOSTNAME>:8080/api/v1/clusters/<CLUSTER_NAME>/services/<Service_name>
def ambari_service_stop(username,passwd,ambari_server_url,service_name):
    cluster_name=ambari_get_cluster(username,passwd,ambari_server_url)
    url="{}/api/v1/clusters/{}/services/{}".format(ambari_server_url,cluster_name,service_name)
    data='{"RequestInfo": {"context" :"Stop service"}, "Body": {"ServiceInfo": {"state": "INSTALLED"}}}'
    return ambari_request(username,passwd,url,data)

#curl -u admin:admin -H "X-Requested-By: ambari" -X GET "http://10.0.88.52:8080/api/v1/clusters/emr/services/YARN?fields=ServiceInfo/state"
def ambari_service_status(username,passwd,ambari_server_url,service_name):
    cluster_name=ambari_get_cluster(username,passwd,ambari_server_url)
    url="{}/api/v1/clusters/{}/services/{}?fields=ServiceInfo/state".format(ambari_server_url,cluster_name,service_name)
    return ambari_request(username,passwd,url)