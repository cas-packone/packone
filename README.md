![](https://img.shields.io/pypi/l/pk1?color=green) ![](https://img.shields.io/pypi/v/pk1) ![](https://img.shields.io/pypi/dm/pk1) ![](https://img.shields.io/pypi/pyversions/pk1)

<img src="pk1/static/logo-large.png" width = "50%" />

# Introduction
PackOne provides a set of consistent interfaces of resources management of heterogeneous clouds.  Resources include virtual machines, containers, storage volumes, etc. Clouds include **OpenStack**, H3CloudOS, EVCloud, CSTCloud, etc. It can **bootstrap** a big data cluster from scratch in a few clicks, and **materialize** the cluster into cloud images to boost following cluster creating procedures. Besides, PackOne can **scale-out**/**in** clusters by only one click.

This software is inspired by the "serverless" trend in cloud computing and big data processing, with the ambitions to bridge the IaaS to Apache Ambari seamlessly and coordinate Ambari Services into an elastic high-level workspace. Currently, It support to deploy and scale out Hadoop, Spark, Hive, Neo4j, MongoDB, Kylin, Redis and many other clustering software in several clicks or api callings.

# Install method 1：Native
1. Python 3.6, postgresql 10;
2. yum install python36-pip and python36-devel;
3. Create a postgresql db with its information (db_user, db_passwd, db_host, db_port, db_name) collected.

Then run:

`pip3.6 install pk1`

`pip3.6 install -U pip setuptools`

`pk1 setup --database db_user:db_passwd:db_host:db_port:db_name`

# Install method 2：Docker
`docker-compose up`

`docker exec -it pk1-app /bin/bash`

`pk1 setup --database pk1:pk1:pk1-pg:5432:pk1`

# Start Service
pk1 start [--listening 127.0.0.1:11001]

# Access Service
https://127.0.0.1:11001/admin

# Step 1: Add Cloud (OpenStack, for example)
open http://127.0.0.1:11001/clouds/cloud/add/, and fill the form like:
<img src="pk1/static/intro-cloud.png"/>

# Step 2: Bootstrap an Ambari cluster
open http://127.0.0.1:11001/engines/cluster/add/, and fill the form like:
<img src="pk1/static/intro-bootstrap.png"/>

# Step 3: Materialize/Scale clusters
open http://127.0.0.1:11001/engines/cluster/, select the target clusters, and click the following materialize.../scale... link:
<img src="pk1/static/intro-materialize.png"/>

# Step 4: Boost cluster creation
Similar to **Step 2**, open http://127.0.0.1:11001/clouds/cloud/add/, but choose a scale whose name without 'boostrap'.

# Stop
pk1 stop

# Uninstall 
pk1 uninstall

# Acknowledge
National Key Research Program of China: Scientific Big Data Management System (No.2016YFB1000600)
