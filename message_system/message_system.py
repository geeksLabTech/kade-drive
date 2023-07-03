import socket
import struct
import time
import select
import threading
from socket import SHUT_RDWR
import sys
from core.utils import get_ips
import logging
logger = logging.getLogger(__name__)

class Message_System:

    def __init__(self, host_ip=None, broadcast_addr=None):
        self.host_ip = host_ip
        self.broadcast_addr = broadcast_addr

        self.pendig_send = []
        self.pendig_receive = [
            {'port': "0.0.0.0", "times": -1}
        ]

    def _mc_send(self, hostip, mcgrpip, mcport, msgbuf):
        # This creates a UDP socket
        sender = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM,
                               proto=socket.IPPROTO_UDP, fileno=None)
        # This defines a multicast end point, that is a pair
        #   (multicast group ip address, send-to port nubmer)
        mcgrp = (mcgrpip, mcport)

        # This defines how many hops a multicast datagram can travel.
        # The IP_MULTICAST_TTL's default value is 1 unless we set it otherwise.
        sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # This defines to which network interface (NIC) is responsible for
        # transmitting the multicast datagram; otherwise, the socket
        # uses the default interface (ifindex = 1 if loopback is 0)
        # If we wish to transmit the datagram to multiple NICs, we
        # ought to create a socket for each NIC.
        sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                          socket.inet_aton(hostip['addr']))

        # Transmit the datagram in the buffer
        sender.sendto(msgbuf, mcgrp)
        # print("sending", msgbuf, mcgrp)

        # release the socket resources
        sender.close()

    @staticmethod
    def is_socket_open(sock: socket.socket):
        try:
            sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            return True  # Socket is open
        except socket.error:
            return False  # Socket is closed

    def stop_listening(self, sock, duration=3):
        threading.Timer(duration, self.close_sock, [sock]).start()

    def close_sock(self, sock: socket.socket):
        if Message_System.is_socket_open(sock):
            
            logger.debug(f"closing socket, {str(sock)}")
            try:
                if sys.platform.startswith('linux'):
                    sock.shutdown(SHUT_RDWR)
                sock.close()
            except OSError:
                pass

    def _mc_recv(self, fromnicip, mcgrpip, mcport):
        # print("inside rec")
        bufsize = 1024
        

        # This creates a UDP socket
        receiver = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM,
                                 proto=socket.IPPROTO_UDP, fileno=None)
        receiver.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # This configure the socket to receive datagrams sent to this multicast
        # end point, i.e., the pair of
        #   (multicast group ip address, mulcast port number)
        # that must match that of the sender
        # print((mcgrpip, mcport))
        bindaddr = (mcgrpip, mcport)
        logger.debug(f"listening {mcgrpip}, {mcport}")
        receiver.bind(bindaddr)

        # This joins the socket to the intended multicast group. The implications
        # are two. It specifies the intended multicast group identified by the
        # multicast IP address.  This also specifies from which network interface
        # (NIC) the socket receives the datagrams for the intended multicast group.
        # It is important to note that socket.INADDR_ANY means the default network
        # interface in the system (ifindex = 1 if loopback interface present). To
        # receive multicast datagrams from multiple NICs, we ought to create a
        # socket for each NIC. Also note that we identify a NIC by its assigned IP
        # address.
        if fromnicip == '0.0.0.0':
            mreq = struct.pack("=4sl", socket.inet_aton(
                mcgrpip), socket.INADDR_ANY)
        else:
            mreq = struct.pack("=4s4s",
                               socket.inet_aton(mcgrpip), socket.inet_aton(fromnicip['addr']))
        # receiver.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        # receiver.timeout(5)
        # ready_to_read, _, _ = select.select([receiver], [], [], 10)

        # print("Listening now...")
        self.stop_listening(receiver)
        # receiver.shutdown(1)
        try:
            buf, senderaddr = receiver.recvfrom(1024)
        except OSError:
            return None, None

        # receiver.close()
        # print("GOT IT...")
        # if buf:
        msg = buf.decode()
        logger.debug("msg: %s", msg)
        # msg = senderaddr = None
        # Release resources
        receiver.close()
        # print(msg, senderaddr)
        return msg, senderaddr

    def add_to_send(self, msg, times=1, dest=None):
        package = {'message': msg,
                   'times': times}

        if dest == None:
            package['ip'] = None
            package['port'] = None

        self.pendig_send.append(package)

    def send(self):
        if self.host_ip == None:
            self_host = socket.gethostname()
            self.host_ip = socket.gethostbyname(self_host)
        # self.host_ip = "192.168.26.1"

        for i in self.pendig_send:
            if i['ip'] == None:
                # print("sending")
                for nic_ip in get_ips():
                    self._mc_send(nic_ip, self.broadcast_addr, 50001,
                                  i['message'].encode())

    def send_heartbeat(self):
        

        while True:
            try:
                self.send()
                time.sleep(0.3)
            except Exception as e:
                logger.error(f"Exception in heartbeat {str(e)}")
                # print("Thrown Exception", e)
                pass

    def receive(self):
        

        to_remove = []
        if self.host_ip == None:
            self_host = socket.gethostname()
            self.host_ip = socket.gethostbyname(self_host)
        # self.host_ip = "192.168.26.1"
        for idx, i in enumerate(self.pendig_receive):
            if i['times'] > 0:
                i -= 1
            logger.debug(f"listening in {self.host_ip}")
            for nic_ip in get_ips():
                logger.debug(f"NIC {nic_ip}")
                if 'broadcast' in nic_ip:
                    msg, ip = self._mc_recv(nic_ip, nic_ip['broadcast'], 50001)
                    if msg:
                        logger.info(f">>> Message from {ip}: {msg}\n")
                        break

                        # process message

                        if i['times'] == 0:
                            to_remove.append(idx)

        for i in to_remove:
            self.pendig_receive.pop(i)

        return msg
