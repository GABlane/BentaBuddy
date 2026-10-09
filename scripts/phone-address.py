#!/usr/bin/env python3
"""Print local browser URLs without reading credentials or contacting a service."""
import ipaddress
import re
import subprocess

try:
    result = subprocess.run(['/sbin/ifconfig'], capture_output=True, text=True, check=True)
    addresses = []
    for block in re.split(r'(?=^\S+: flags=)', result.stdout, flags=re.MULTILINE):
        interface = block.split(':', 1)[0]
        if not interface.startswith(('en', 'bridge')) or 'status: inactive' in block:
            continue
        for address in re.findall(r'^\s+inet (\d+\.\d+\.\d+\.\d+)\b', block, re.MULTILINE):
            ip = ipaddress.ip_address(address)
            if not ip.is_loopback and not ip.is_link_local:
                addresses.append((interface, address))
    if addresses:
        for interface, address in addresses:
            print('Open on your phone: http://' + address + ':8000 (' + interface + ')')
    else:
        print('No active LAN address found. Connect the Mac to Wi-Fi/Ethernet first.')
except (OSError, subprocess.SubprocessError):
    print('Find the Mac IP in System Settings → Wi-Fi → Details, then open http://MAC_IP:8000.')
