"""
General catchall for functions that don't make sense as methods.
"""
import datetime
import hashlib
import operator
import logging
import socket

logger = logging.getLogger(__name__)



def digest(string):
    if not isinstance(string, bytes):
        string = str(string).encode("utf8")
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
    bits = [bin(bite)[2:].rjust(8, "0") for bite in bites]
    return "".join(bits)


def is_port_in_use(host, port):
    try:
        # Create a socket object
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set a timeout value for the socket
        sock.settimeout(1)

        # Try to connect to the host and port
        result = sock.connect_ex((host, port))

        # If the connection was successful, the port is in use
        if result == 0:
            return True
        else:
            return False

    except socket.error as e:
        print(f"Error: {e}")

    finally:
        # Close the socket
        sock.close()


def it_is_necessary_to_write(local_last_write, contains, date):
    valid_data = False
    if date is not None:
        str_date = date.strftime("%m/%d/%y %H:%M:%S")
        date = datetime.datetime.strptime(str_date, '%m/%d/%y %H:%M:%S')
        valid_data = True
    if (
        local_last_write is None
        or date is None
        or (valid_data and date < local_last_write)
        or not contains
    ):
        logger.critical("VA A ESCRIBIR")
        logger.info(f" date {date} local_last_write {local_last_write},contains {contains}")
        if valid_data and local_last_write:
            logger.info("comp %s", date < local_last_write)
        return True
    return False
