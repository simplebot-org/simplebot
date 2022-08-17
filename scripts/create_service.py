#!/usr/bin/env python3
"""Script to help creating systemd services for SimpleBot bots.
Example usage:
create_service.py --name "bot1" --user "exampleUser" --cmd "simplebot -a bot1@example.com serve"
"""

import argparse
import subprocess

cfg = """[Unit]
Description={name} service
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=5
## Restart every 24h:
#WatchdogSec=86400
#WatchdogSignal=SIGKILL
User={user}
ExecStart={cmd}

[Install]
WantedBy=multi-user.target
"""


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Simplebot service creator")
    p.add_argument("-n", "--name", help="Service name", required=True)
    p.add_argument("-u", "--user", help="User that will run the service", required=True)
    p.add_argument("-c", "--cmd", help="Command that will start the bot", required=True)
    args = p.parse_args()

    cfg = cfg.format(name=args.name, user=args.user, cmd=args.cmd)

    path = f"/etc/systemd/system/{args.name}.service"
    print(f"\nSERVICE PATH: {path}\nSERVICE CONFIGURATION:\n{cfg}")
    input("[Press enter to processed...]")
    with open(path, "w") as fd:
        fd.write(cfg)

    cmd = ["systemctl", "enable", args.name]
    subprocess.run(cmd)
    cmd[1] = "start"
    subprocess.run(cmd)
