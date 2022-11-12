from setuptools import setup, find_packages

setup(
    name = "pk1",
    version = "0.3.1",
    keywords = ("pip", "packone"),
    description = "PackOne: Pack clouds, engines and data services into one light stack.",
    long_description = open('README.rst').read(),
    license = "Apache-2.0 Licence",
    url = "https://github.com/cas-bigdatalab/packone",
    author = "Excel Wang",
    author_email = "wanghj@cnic.com",
    packages = find_packages(exclude=['*.migrations']),
    include_package_data = True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    install_requires = ['django-jet-opt==1.0.8','django==2.2.28','uwsgi==2.0.21','ambari==0.1.7','django-admin-auto==0.1.1','djangorestframework==3.10.3','djangorestframework-simplejwt==4.3.0','django-simpleui==4.0.3', 'django-filter==2.4.0', 'psycopg2-binary==2.8.6', 'coreapi==2.3.3', 'paramiko==2.7.2', 'scp==0.14.4', 'django-cors-headers==2.4.0', 'python-novaclient==17.7.0', 'python-cinderclient==7.4.1', 'python-glanceclient==3.6.0', 'django-autocomplete-light==3.8.2'],
    entry_points = {
        'console_scripts': [
            'pk1 = pk1.server:main',
        ]
    }
)
