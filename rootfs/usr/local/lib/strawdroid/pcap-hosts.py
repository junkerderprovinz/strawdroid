#!/usr/bin/env python3
"""Lists the hosts an app talked to in a PCAPdroid capture: DNS names, TLS
server names and the addresses it connected to."""
import ipaddress
import struct
import sys
from collections import Counter

LINK_ETHERNET, LINK_RAW, LINK_SLL, LINK_IPV4, LINK_IPV6 = 1, 101, 113, 228, 229


def packets(path):
    with open(path, "rb") as f:
        header = f.read(24)
        magic = header[:4]
        if magic in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1"):
            order = "<"
        elif magic in (b"\xa1\xb2\xc3\xd4", b"\xa1\xb2\x3c\x4d"):
            order = ">"
        else:
            sys.exit(f"{path} is not a pcap file")
        link = struct.unpack(order + "I", header[20:24])[0]
        while True:
            record = f.read(16)
            if len(record) < 16:
                return
            length = struct.unpack(order + "I", record[8:12])[0]
            data = f.read(length)
            if link == LINK_ETHERNET:
                data = data[14:]
            elif link == LINK_SLL:
                data = data[16:]
            elif link not in (LINK_RAW, LINK_IPV4, LINK_IPV6):
                sys.exit(f"link type {link} is not supported")
            yield data


def transport(ip):
    """Returns protocol, source and destination address, source and destination
    port, and payload, or None for anything that is not TCP or UDP."""
    version = ip[0] >> 4
    if version == 4:
        start = (ip[0] & 0x0F) * 4
        proto = ip[9]
        src, dst = ipaddress.ip_address(ip[12:16]), ipaddress.ip_address(ip[16:20])
    elif version == 6:
        start, proto = 40, ip[6]
        src, dst = ipaddress.ip_address(ip[8:24]), ipaddress.ip_address(ip[24:40])
    else:
        return None
    seg = ip[start:]
    if proto == 6 and len(seg) >= 20:
        return "tcp", src, dst, *struct.unpack(">HH", seg[:4]), seg[(seg[12] >> 4) * 4:]
    if proto == 17 and len(seg) >= 8:
        return "udp", src, dst, *struct.unpack(">HH", seg[:4]), seg[8:]
    return None


def dns_question(payload):
    labels, pos = [], 12
    while pos < len(payload) and payload[pos]:
        size = payload[pos]
        labels.append(payload[pos + 1:pos + 1 + size].decode("ascii", "replace"))
        pos += size + 1
    return ".".join(labels) or None


def tls_server_name(payload):
    # A TLS record that carries a ClientHello: type 22, handshake type 1.
    if len(payload) < 44 or payload[0] != 22 or payload[5] != 1:
        return None
    pos = 43
    pos += 1 + payload[pos]
    pos += 2 + struct.unpack(">H", payload[pos:pos + 2])[0]
    pos += 1 + payload[pos]
    end = pos + 2 + struct.unpack(">H", payload[pos:pos + 2])[0]
    pos += 2
    while pos + 4 <= end:
        kind, size = struct.unpack(">HH", payload[pos:pos + 4])
        if kind == 0:
            name_size = struct.unpack(">H", payload[pos + 7:pos + 9])[0]
            return payload[pos + 9:pos + 9 + name_size].decode("ascii", "replace")
        pos += 4 + size
    return None


def main(path):
    segments = []
    for ip in packets(path):
        try:
            seg = transport(ip)
        except (IndexError, struct.error, ValueError):
            continue
        if seg:
            segments.append(seg)

    # The capture holds both directions. Packets to port 53 or 443 come from
    # the device, so their sources tell which addresses are its own.
    own = {src for _, src, _, _, dport, _ in segments if dport in (53, 443)}

    names, remotes = Counter(), Counter()
    for proto, src, dst, sport, dport, payload in segments:
        try:
            if proto == "udp" and dport == 53:
                name = dns_question(payload)
                if name:
                    names[name] += 1
            elif proto == "tcp" and payload:
                name = tls_server_name(payload)
                if name:
                    names[name] += 1
        except (IndexError, struct.error, ValueError):
            pass
        if 53 in (sport, dport):
            continue
        remote = f"{proto} {src}:{sport}" if dst in own else f"{proto} {dst}:{dport}"
        remotes[remote] += 1

    print("Names looked up or contacted:")
    for name in sorted(names) or ["(none)"]:
        print(f"  {name}")
    print("Remote addresses:")
    if not remotes:
        print("  (none)")
    for remote, count in remotes.most_common():
        print(f"  {remote}  ({count} packets)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: pcap-hosts.py <capture.pcap>")
    main(sys.argv[1])
