from twisted.internet import reactor, protocol
import netifaces
import struct
import socket
import random


# Clase para manejar la creación del servidor
class FileServerFactory(protocol.Factory):
    def __init__(self):
        self.known_ips = set()

    def buildProtocol(self, addr):
        return FileServer(self)

    def add_known_ip(self, ip):
        self.known_ips.add(ip)

    def remove_known_ip(self, ip):
        self.known_ips.remove(ip)

    def send_response(self, ip, response):
        if ip in self.known_ips:
            # Aquí puedes implementar la lógica para enviar la respuesta a la dirección IP designada
            # Puedes utilizar una conexión adicional a través de sockets, por ejemplo
            print('Respuesta enviada a:', ip)
        else:
            print('Dirección IP desconocida:', ip)

    def get_connected_ips(self):
        connected_ips = []
        interfaces = netifaces.interfaces()

        for interface in interfaces:
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    connected_ips.append(addr['addr'])

        return connected_ips

    def send_data(self, ip, data):
        # Enviar los datos a la PC destino
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, 12346))
            sock.sendall(data)
            response = sock.recv(1024)
            sock.close()
            return response
        except socket.error as e:
            print('Error al enviar los datos:', e)
            return b'Error en la conexion'

# Configuración del servidor
HOST = 'localhost'
PORT = 12345

# Iniciar el servidor
print('Servidor en espera de conexiones...')
reactor.listenTCP(PORT, FileServerFactory())
reactor.run()

# Clase para manejar la conexión del cliente
class FileServer(protocol.Protocol):
    def __init__(self, factory : FileServerFactory):
        self.factory = factory

    def connectionMade(self):
        print('Cliente conectado:', self.transport.getPeer())

        # Agregar la dirección IP del cliente a la lista de IPs conocidas
        client_ip = self.transport.getPeer().host
        self.factory.add_known_ip(client_ip)

        # Obtener las direcciones IP de las PCs conectadas en la red
        connected_ips = self.factory.get_connected_ips()
        print('Direcciones IP en la red:', connected_ips)

    def dataReceived(self, data):
        # Obtener la dirección IP del cliente
        client_ip = self.transport.getPeer().host

        # Procesar la solicitud y generar la respuesta
        request = data  # Aquí se asume que los datos recibidos ya son binarios
        responses = self.procesar_solicitud(request)

        # Enviar las respuestas al cliente
        for response in responses:
            self.factory.send_response(client_ip, response)

    def connectionLost(self, reason):
        print('Cliente desconectado:', self.transport.getPeer())

        # Eliminar la dirección IP del cliente de la lista de IPs conocidas
        client_ip = self.transport.getPeer().host
        self.factory.remove_known_ip(client_ip)

    def procesar_solicitud(self, request):
        # Dividir la data en fragmentos de tamaño k
        k = 100  # Tamaño del fragmento
        fragments = [request[i:i+k] for i in range(0, len(request), k)]

        # Obtener las direcciones IP de las PCs conectadas en la red
        connected_ips = self.factory.get_connected_ips()

        # Replicar los fragmentos tres veces en direcciones IP aleatorias de la red
        responses = []

        for fragment in fragments:
            # Seleccionar una dirección IP de destino de manera aleatoria
            if connected_ips:
                destination_ip = random.choice(connected_ips)
                print('IP de destino seleccionada:', destination_ip)
            else:
                print('No hay IPs conectadas en la red')
                break

            # Enviar el fragmento a la IP de destino
            response = self.factory.send_data(destination_ip, fragment)
            responses.append(response)

        return responses

