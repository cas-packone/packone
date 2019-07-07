.. image:: pk1/static/logo-large.png
    :width: 200
    :alt: Logo

===================
Introduction
===================
PackOne, inspired by the "serverless" trend in cloud computing and big data processing, has the ambitions to bridge the IaaS to Apache Ambari seamlessly and coordinate Ambari Services into an elastic high-level workspace. 

===================
Install
===================

Choose a linux (Centos 7.5 is verified) host which network can reach the target openstack group resource, and create a postgresql db with its information (db_user, db_passwd, db_host, db_port, db_name) collected. Then run:

pip install pk1

pip install -U pip setuptools

pk1 setup --database db_user:db_passwd:db_host:b_port:db_name

===================
Run
===================
pk1 start [--listening 127.0.0.1:11001]

===================
Stop
===================
pk1 stop

===================
Uninstall 
===================
pk1 uninstall

===================
Acknowledge
===================
National key Research Program of China: Scientific Big Data Management System (No.2016YFB1000600)
