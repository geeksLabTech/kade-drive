"""
General catchall for functions that don't make sense as methods.
"""
import hashlib
import operator
import netifaces as ni

def digest(string):
    if not isinstance(string, bytes):
        string = str(string).encode('utf8')
    return hashlib.sha1(string).digest()


def shared_prefix(args):
    """
    Find the shared prefix between the strings.

    For instance:

        sharedPrefix(['blahblah', 'blahwhat'])

    returns 'blah'.
    """
    i = 0
    while i < min(map(len, args)):
        if len(set(map(operator.itemgetter(i), args))) != 1:
            break
        i += 1
    return args[0][:i]


def bytes_to_bit_string(bites):
    bits = [bin(bite)[2:].rjust(8, '0') for bite in bites]
    return "".join(bits)

def get_ips():
    # Get all network interfaces
    interfaces = ni.interfaces()
    # print(interfaces)

    # Sort the interfaces by preference: LAN, WLAN, and localhost
    interfaces = sorted(interfaces, key=lambda x: ("wl" in x, "eth" in x, "en" in x),reverse=True)

    ips = []
    for interface in interfaces:
        try:
            # Get the IP address for the current interface
            # print(ni.ifaddresses(interface)[ni.AF_INET][0])
            ip = ni.ifaddresses(interface)[ni.AF_INET][0]
            if ip:
                ips.append(ip)
        except:
            pass

    return ips
