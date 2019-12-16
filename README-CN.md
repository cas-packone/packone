![](https://img.shields.io/pypi/l/pk1?color=green) ![](https://img.shields.io/pypi/v/pk1) ![](https://img.shields.io/pypi/dm/pk1) ![](https://img.shields.io/pypi/pyversions/pk1)

<img src="pk1/static/logo-large.png" width = "50%" />

# 简介
PackOne致力于简化大数据软件在各类云上的弹性部署流程。通过对云API和Apache Ambari API的联合调用，完成Hadoop、Spark、NiFi、PiFlow、Kylin、MangoDB、Neo4J、Redis等流行的大数据管理/处理软件在云端的一键快速部署和一键伸缩。PackOne目前已支持**OpenStack**、H3CloudOS、EVCloud等私有云系统，以及公有云中国科技云（CSTCloud）。
主要特性包括：
1. 以一致的方式在同一个界面上对来自不同云的虚拟机、存储卷、镜像、模版等进行CURD操作。
2. 支持在空白虚拟机上完成大数据处理集群的全自动部署。
3. 通过将模版集群物化为系统镜像，实现新集群的分钟级快速部署。
4. 通过Apache Ambari对已部署的大数据软件进行状态监控、配置管理。
5. 通过集群节点的全自动增删，实现各类大数据软件的分钟级弹性伸缩。

PackOne的长期目标是实现serverless式云端大数据处理，即在用户不直接管理云主机实例的前提下，实现大数据软件集群的自动部署和弹性伸缩（集群层）、多源异构数据资源的自动汇聚与自动入库（数据层）、数据库实例的函数式交互分析与流水线分析（space层）。

# 安装
1. 选择一个linux云主机 (推荐Centos 7.5)，该主机能够与目标云平台进行通信；
2. `yum install python36-pip and python36-devel`；
3. 创建一个postgresql数据库实例，并准备好该实例的以下信息：db_user、db_passwd、db_host、db_port、db_name。
然后运行：

`pip3.6 install pk1`

`pip3.6 install -U pip setuptools`

`pk1 setup --database $db_user:$db_passwd:$db_host:$db_port:$db_name`($db_*替换为实际值)

# 启动PackOne服务
`pk1 start [--listening 127.0.0.1:11001]`

# Step 1: 接入云资源(以OpenStack为例)
访问 http://127.0.0.1:11001/clouds/cloud/add/, 填写Openstack相关账户信息，如下图：
<img src="pk1/static/intro-cloud.png"/>

# Step 2: 初始化一个Ambari大数据集群
访问 http://127.0.0.1:11001/engines/cluster/add/, 选择集群的规格（Scale），如下图所示:
<img src="pk1/static/intro-bootstrap.png"/>

# Step 3: 物化/伸缩一个集群
访问 http://127.0.0.1:11001/engines/cluster/, 选择目标集群，在下拉操作列表中选择materialize.../scale... 链接，如下图所示:
<img src="pk1/static/intro-materialize.png"/>

# Step 4: 快速创建集群
与 **Step 2** 类似, 访问 http://127.0.0.1:11001/clouds/cloud/add/。区别在于，此处选择的规格（scale）名字不带'boostrap'。

# 停止PackOne服务
`pk1 stop`

# 卸载 
`pk1 uninstall`

# 致谢
国家重点研发计划: 科学大数据管理系统(No.2016YFB1000600)
