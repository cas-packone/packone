def remedy_scale_ambari_bootstrap(vdf_url=None):
    script="sed -i 's/hostname=localhost/hostname=master1.packone/g' /etc/ambari-agent/conf/ambari-agent.ini\n\n" \
        "ambari-agent start 2>&1\n\n" \
        'if [ `hostname` == "master1.packone" ]; then\n' \
        'yum -q -y install epel-release 2>&1\n' \
        'yum -q -y install python-pip 2>&1\n' \
        'pip -qq install ambari\n' \
        "fi\n\n" \
        'if [ `hostname` == "master1.packone" ]; then\n' \
        'yum -q -y install nmap-ncat 2>&1\n' \
        'while ! echo exit | nc localhost 8080; do sleep 3; done 2>&1\n' \
        'ambari localhost:8080 cluster create'
    if vdf_url: script+='_from_vdf '+vdf_url
    script+=' packone typical_triple master1.packone master2.packone slave.packone\nfi'
    return script

def remedy_scale_ambari_fast_init():
    return 'rm -rf /hadoop\n' \
        'mkdir -p /data/hadoop\n' \
        'ln -sf /data/hadoop /hadoop\n' \
        '#env\n' \
        "echo 'JAVA_HOME=/usr/jdk64/default'>>/etc/profile.d/packone-java.sh\n" \
        "echo 'JRE_HOME=/usr/jdk64/default/jre'>>/etc/profile.d/packone-java.sh\n" \
        "echo 'CLASS_PATH=.:$JAVA_HOME/lib:$JRE_HOME/lib'>>/etc/profile.d/packone-java.sh\n" \
        "echo 'PATH=$JAVA_HOME/bin:$JRE_HOME/bin:$PATH'>>/etc/profile.d/packone-java.sh\n" \
        'reboot\n' \
        'if [ `hostname` == "master1.packone" ]; then\n' \
        '    while ! echo exit | nc localhost 8080; do sleep 3; done 2>&1\n' \
        '    pip -qq install -U ambari\n' \
        '    ambari master1.packone:8080 service start\n' \
        'fi'

def remedy_scale_ambari_fast_scale_out():
    return "rm -rf /hadoop\n" \
        "mkdir -p /data/hadoop\n" \
        "ln -sf /data/hadoop /hadoop\n" \
        "#env\n" \
        "echo 'JAVA_HOME=/usr/jdk64/default'>>/etc/profile.d/packone-java.sh\n" \
        "echo 'JRE_HOME=/usr/jdk64/default/jre'>>/etc/profile.d/packone-java.sh\n" \
        "echo 'CLASS_PATH=.:$JAVA_HOME/lib:$JRE_HOME/lib'>>/etc/profile.d/packone-java.sh\n" \
        "echo 'PATH=$JAVA_HOME/bin:$JRE_HOME/bin:$PATH'>>/etc/profile.d/packone-java.sh\n" \
        "reboot\n" \
        "pip -qq install -U ambari\n" \
        'yum -q -y install nmap-ncat 2>&1\n' \
        'while ! echo exit | nc master1.packone 8080; do sleep 3; done 2>&1\n' \
        "ambari master1.packone:8080 host clone slave.packone `hostname`\n" \
        'ambari master1.packone:8080 service start'

def remedy_scale_ambari_fast_scale_in():
    return '#ambari master1.packone:8080 host delete `hostname`'