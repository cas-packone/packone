from setuptools import setup, find_packages

setup(
    name = "pk1",
    version = "0.2.1",
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
    install_requires = ['django>=2.3','uwsgi','ambari','django-admin-auto','djangorestframework','djangorestframework-simplejwt','django-simpleui', 'django-filter', 'psycopg2-binary', 'coreapi', 'paramiko', 'scp', 'django-cors-headers==2.4.0', 'python-novaclient', 'python-cinderclient', 'python-glanceclient', 'django-autocomplete-light'],
    entry_points = {
        'console_scripts': [
            'pk1 = pk1.server:main',
        ]
    }
)