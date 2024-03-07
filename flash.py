# SPDX-License-Identifier: Unlicense
# originally written 2023 by equinox
# ABSOLUTELY NO WARRANTY, ESPECIALLY FOR BRICKED DEVICES

import sys
import time
import logging
import argparse
import hashlib
import socket
import urllib.parse

import requests
import json
import paramiko

try:
    import socks
except ImportError:
    socks = None


# default login on factory fresh devices
username = 'admin'
password = 'admin'
# temporary password (cannot proceed without setting one)
newpass = 'frobnicate'

def pwhash(s):
    return hashlib.md5(s.encode('UTF-8')).hexdigest().upper()

class TPLException(Exception):
    pass

class TPLSession(requests.Session):
    # HTTP headers expected by the device
    def __init__(self, *args, proxy=None, ipaddr=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.headers_get = {
            'Referer': f'http://{ipaddr}/',
            'Origin': f'http://{ipaddr}',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
        }

        self.headers_post_file = self.headers_get | {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
        }

        self.headers_post = self.headers_post_file | {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }

        self._proxy = proxy
        if proxy is not None:
            self.proxies['http'] = proxy
            self.proxies['https'] = proxy

    def get(self, *args, **kwargs):
        headers = kwargs.setdefault("headers", {})
        headers.update(self.headers_get)
        return super().get(*args, **kwargs)

    def post_check(self, *args, **kwargs):
        if "files" in kwargs:
            _headers = {} | self.headers_post_file
        else:
            _headers = {} | self.headers_post
        kwargs.setdefault("headers", _headers)
        response = self.post(*args, **kwargs)
        response.raise_for_status()

        # returns no proper content-type...
        if not response.text.lstrip().startswith("{"):
            return response

        data = response.json()
        if data.get("success", True) != True:
            raise TPLException("operation failed (success=false)")
        if data.get("error", 0) != 0:
            raise TPLException("operation failed (error!=0)")

        return response


def main():
    argp = argparse.ArgumentParser(description = 'EAP615-Wall flash tool')
    argp.add_argument('--proxy', metavar = 'URL', type = str, help = "use SOCKS5 proxy, specify as socks5:// URL")
    argp.add_argument('--openwrt', type=argparse.FileType('rb'))
    argp.add_argument('--debug', action="store_true", help="enable debug logging")
    argp.add_argument('ipaddr', metavar = 'IPADDR', type = str,
            help = 'current IP address of EAP615')
    args = argp.parse_args()

    logging.basicConfig()
    requests_log = logging.getLogger("requests.packages.urllib3")

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    ipaddr = args.ipaddr

    openwrt = None
    if args.openwrt:
        openwrt = args.openwrt.read()

    session = TPLSession(proxy=args.proxy, ipaddr=ipaddr)

    def ssh_get_sock():
        if args.proxy:
            proxyurl = urllib.parse.urlparse(args.proxy)
            assert proxyurl.scheme == 'socks5'

            if socks is None:
                raise ValueError("python socks5 support requested but not available")

            sock = socks.socksocket()
            sock.set_proxy(
                proxy_type=socks.SOCKS5,
                addr=proxyurl.hostname,
                port=proxyurl.port,
            )
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        return sock

    ts = int(time.time() * 1000)

    def step1():
        ts = int(time.time() * 1000)

        g1 = session.get(f'http://{ipaddr}/')
        print(g1)
        g2 = session.get(f'http://{ipaddr}/data/managedMode.json?_=%d' % (ts))
        print(g2, g2.text)
        g3 = session.post_check(f'http://{ipaddr}/data/login.json', data={'operation': 'read'})
        print(g3, g3.text)

        time.sleep(5.1)
        ts = int(time.time() * 1000)

        g4 = session.post_check(f'http://{ipaddr}/', data={'username': username, 'password': pwhash(password)})
        print(g4)
        print(session.cookies)
        g5 = session.get(f'http://{ipaddr}/')
        print(g5)

        time.sleep(0.2)
        ts = int(time.time() * 1000)

        g6 = session.get(f'http://{ipaddr}/data/sysmod.json?operation=read&_=%d' % (ts + 1))
        print(g6, g6.text)

        time.sleep(0.5)
        ts = int(time.time() * 1000)

        acctdata = {
            'account': {
                'newUserName': 'admin',
                'newPwd': pwhash(newpass),
                'confirmPwd': pwhash(newpass),
            },
            'date': time.strftime('%m/%d/%Y', time.gmtime(ts)),
            'time': time.strftime('%H:%M:%S', time.gmtime(ts)),
            'timeZone': '0',
        }
        g7 = session.post_check(f'http://{ipaddr}/data/wizard.json', data={
            'operation': 'skip',
            'data': json.dumps(acctdata),
        })
        print(g7, g7.text)

        #g8 = session.post(f'http://{ipaddr}/data/login.json', data={'operation': 'read'}, headers=headers)
        #print(g8, g8.text)
        #g9 = session.post(f'http://{ipaddr}/', data={'username': username, 'password': pwhash(newpass)}, headers=headers)
        #print(g9)

    def step2():
        h1 = session.get(f'http://{ipaddr}/')
        print(h1)
        h2 = session.post_check(f'http://{ipaddr}/data/login.json', data={'operation': 'read'})
        print(h2, h2.text)
        h3 = session.post_check(f'http://{ipaddr}/', data={'username': username, 'password': pwhash(newpass)})
        print(h3)
        h3 = session.post_check(f'http://{ipaddr}/data/sshServer.json', data={'operation': 'read'})
        print(h3, h3.text)
        h4 = session.post_check(f'http://{ipaddr}/data/sshServer.json', data={
            'operation': 'write',
            'remoteEnable': 'false',
            'serverPort': '22',
            'sshServerEnable': 'true',
        })
        print(h4, h4.text)

    def step3():
        sock = ssh_get_sock()
        sock.connect((args.ipaddr, 22))

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('hostkey ignored', username='admin', password=newpass, sock=sock)
        ssh.exec_command('cliclientd stopcs')
        ssh.close()

        sock.close()

    def step4():
        assert openwrt is not None

        h1 = session.get(f'http://{ipaddr}/')
        print(h1)
        h2 = session.post_check(f'http://{ipaddr}/data/login.json', data={'operation': 'read'})
        print(h2, h2.text)
        h3 = session.post_check(f'http://{ipaddr}/', data={'username': username, 'password': pwhash(newpass)})
        print(h3)

        time.sleep(0.5)

        files = {
            'image': (
                'openwrt-fwu.bin', openwrt, 'application/octet-stream', {},
            ),
        }

        h4 = session.post_check(f'http://{ipaddr}/data/firmware.set.json', files=files)
        print(h4, h4.text)

        time.sleep(0.5)

        h5 = session.get(f'http://{ipaddr}/data/firmware.set.json?operation=update&_=%d' % (ts))
        print(h5, h5.text)
        fwu_err = h5.json().get("errCode")
        if fwu_err == 0:
            print("EAP615 accepted firmware image")
            # test device took 135s, but flash speed will vary across production runs
            print("install takes about 2 min 30s, please be patient.  For convenience, this script will sleep now.")
            time.sleep(150)
        elif fwu_err == 50008:
            print("EAP615 rejected the image, probably <= 23.05.2.  use OpenWRT snapshot.")
        else:
            print(f"EAP615 rejected update with unknown error {fwu_err}")

    # TODO: add some way to run only specific steps
    step1()
    step2()
    step3()
    step4()


if __name__ == "__main__":
    main()
