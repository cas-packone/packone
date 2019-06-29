import os, shutil
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def setup(args):
    os.system('python {BASE_DIR}/manage.py collectstatic --noinput'.format(BASE_DIR=BASE_DIR))
    database=args.database[0] if args.database else 'packone:packone:localhost:5432:packone'
    (db_user, db_passwd, db_host, db_port, db_name)=database.split(':')
    with open(BASE_DIR+"/conf/settings.py") as f:
        newText=f.read().replace(
            "'USER': 'rabbit'", "'USER': '"+db_user+"'"
            ).replace(
                "'PASSWORD': 'rabbit'", "'PASSWORD': '"+db_passwd+"'"
            ).replace(
                'rabbit-db-host', db_host
            ).replace(
                '5432', db_port
            ).replace(
                'packone_new', db_name
            )
    with open(BASE_DIR+"/conf/settings.py", "w") as f:
        f.write(newText)
    
def start(args):
    address=args.listening[0] if args.listening else '127.0.0.1:11001'
    os.system('uwsgi --http {address} --chdir {BASE_DIR} --ini {BASE_DIR}/conf/uwsgi.ini'.format(address=address,BASE_DIR=BASE_DIR))

def stop(args):
    os.system('uwsgi --stop /var/tmp/packone.pid')

def uninstall(args):
    shutil.rmtree(BASE_DIR+'/static')
    os.system('pip uninstall pk1')

parser = argparse.ArgumentParser(description='packone cmd line.')
subparsers = parser.add_subparsers()

parser_setup = subparsers.add_parser('setup')
parser_setup.add_argument('--database', metavar='user:password:host:port:db_name', nargs=1,
                    help='the pk1 postgresql database configuration. default: packone:packone:localhost:5432:packone')
parser_setup.set_defaults(func=setup)

parser_start = subparsers.add_parser('start')
parser_start.add_argument('--listening', metavar='ip:port', nargs=1,
                    help='the pk1 listening address. default: 127.0.0.1:11001')
parser_start.set_defaults(func=start)

parser_stop = subparsers.add_parser('stop')
parser_stop.set_defaults(func=stop)

parser_uninstall = subparsers.add_parser('uninstall')
parser_uninstall.set_defaults(func=uninstall)

def main():
    args = parser.parse_args()
    try: #https://stackoverflow.com/a/54161510/4444459
        args.func(args)
    except AttributeError:
        parser.parse_args(['--help'])
    