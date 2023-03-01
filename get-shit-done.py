#!/usr/bin/env python3

from configparser import ConfigParser
import sys
import subprocess
import getpass
import re
from typing import List

restart_network_command = {
        "linux": ["systemctl", "restart", "NetworkManager"],
        "darwin": ["dscacheutil", "-flushcache"],
        "win32": ["ipconfig", "/flushdns"]
    }


def restart_network():
    if restart_network_command[sys.platform]:
        subprocess.check_call(restart_network_command[sys.platform])
    else:
        # Intention isn't to exit, as it still works, but just requires some
        # intervention on the user's part.
        message = '"Please contribute DNS cache flush command on GitHub."'
        subprocess.check_call(['echo', message])


class Sites:

    config = ConfigParser()

    def __init__(self, sites_file: str):
        self.config.read(sites_file)
        self.modes = self.config.sections()

    def get(self, mode: str) -> List[str]:
        if mode not in self.modes:
            KeyError()
        return self.config.get(mode, 'sites').strip().split(',')

    def get_for_hosts(self, mode: str) -> List[str]:
        hosts = []
        sites = self.get(mode)
        for site in set(sites):
            site = site.strip()
            hosts.append("127.0.0.1\t" + site)
            hosts.append("127.0.0.1\twww." + site)
        return hosts

    def __repr__(self) -> str:
        sites = {}
        for mode in self.modes:
            sites[mode] = self.config.items(mode)
        return str(sites)

class Hosts:

    # Start token indicating start of lines get-shit-done is adding
    start_token = "## start gsd"
    # End token indicating end of lines get-shit-done is adding
    end_token = "## end gsd"

    def __init__(self):
        # Host file that the network manager reads to block sites
        if "win32" in sys.platform:
            self.file = '/Windows/System32/drivers/etc/hosts'
        else:
            self.file = '/etc/hosts'

    def update(self, sites: List[str], mode: str = None):
        mode_start_token = '%s %s' % (self.start_token, mode)
        with open(self.file, 'r+') as file:
            content = file.read()
            if mode_start_token in content and self.end_token in content:
                exit_error(mode + " mode already set")
            else:
                new_hosts: List[str] = [self._remove(content)]
                if mode:
                    new_hosts.append(mode_start_token)
                    new_hosts.extend(sites)
                    new_hosts.append(self.end_token)
                file.seek(0)
                file.write('\n'.join(new_hosts))
                file.truncate()

    def _remove(self, file_content: str):
        return re.sub(f'(\n){self.start_token}((.|\n)*){self.end_token}(.*|\n)', '', file_content)

    def clean(self):
        self.update([], mode=None)


def check_args():
    if len(sys.argv) != 2:
        exit_error('usage: ' + sys.argv[0] + ' [%s]' % modes_prompt)


def exit_error(error):
    print(error, file=sys.stderr)
    exit(1)


def is_root_user():
    if getpass.getuser() != 'root' and 'win32' not in sys.platform:
        exit_error('Please run script as root.')


if __name__ == "__main__":
    sites = Sites('./sites.ini')
    modes = sites.modes + ['play']
    modes_prompt = '|'.join(modes)
    hosts = Hosts()

    is_root_user()
    try:
        check_args()
        mode = sys.argv[1]
        if mode == 'play':
            hosts.clean()
            restart_network()
        else:
            hosts.update(sites.get_for_hosts(mode), mode)
            restart_network()
    except KeyError:
        exit_error('usage: ' + sys.argv[0] + ' [%s]' % modes_prompt)
