#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import subprocess


serv_cfg = """[Unit]
Description={name} service
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=5
User={user}
ExecStart={cmd}

[Install]
WantedBy=multi-user.target
"""


if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description='Simplebot service creator')
    p.add_argument('-n', '--name', help='Service name', required=True)
    p.add_argument('-u', '--user', help='User that will run the service',
                   required=True)
    p.add_argument('-c', '--cmd', help='Command that will start the bot',
                   required=True)
    args = p.parse_args()

    serv_cfg = serv_cfg.format(
        name=args.name, user=args.user, cmd=args.cmd)

    serv_path = '/etc/systemd/system/{}.service'.format(args.name)
    print('\nSERVICE PATH: {}'.format(serv_path))
    print('SERVICE CONFIGURATION:\n{}'.format(serv_cfg))
    input('[Press enter to processed...]')
    with open(serv_path, 'w') as fd:
        fd.write(serv_cfg)

    cmd = ['systemctl', 'enable', args.name]
    subprocess.run(cmd)
    cmd[1] = 'start'
    subprocess.run(cmd)
