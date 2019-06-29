import os
import argparse

parser = argparse.ArgumentParser(description='packone cmd line.')
parser.add_argument('--listening', metavar='ip:port', nargs=1,
                    help='the pk1 listening address. default: 127.0.0.1:11001')
parser.add_argument('action', metavar='A', nargs=1, choices=['start', 'stop'],
                    help='the action to be performed on the server.')
args = parser.parse_args()

address=args.listening[0] if args.listening else '127.0.0.1:11001'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    func=globals()['{}'.format(args.action[0])]
    func()

def start():
    os.system('python {BASE_DIR}/manage.py collectstatic --noinput'.format(BASE_DIR=BASE_DIR))
    os.system('uwsgi --http {address} --chdir {BASE_DIR} --ini {BASE_DIR}/conf/uwsgi.ini'.format(address=address,BASE_DIR=BASE_DIR))

def stop():
    os.system('uwsgi --stop /var/tmp/packone.pid')

