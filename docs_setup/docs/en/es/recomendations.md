# Recomendaciones

- Dada la caída de un nodo de la red, mantener de alguna manera el ID del nodo anterior. Si su información aún se mantiene en disco y actualizada, cargar con este ID puede ser más eficiente que iniciar como un nodo nuevo y comenzar nuevamente el proceso de balanceo de la red.

- En la implementación original de Kademlia, la comunicación entre nodos se realiza mediante UDP. Sin embargo, debido a las limitaciones de UDP para manejar grandes cantidades de información, se cambió a TCP. No obstante, TCP es menos eficiente para tareas que no sean transferencia de datos de almacenamiento. Implementar un doble protocolo de comunicación entre los nodos debería representar una mejora en el rendimiento de la red.

- Cambiar el algoritmo de hash utilizado de SHA1 a SHA256, dado que SHA1 ya no es considerado seguro y sus vulnerabilidades facilitan actividades maliciosas.

- Implementar un mecanismo de testing automático distribuido utilizando técnicas como "chaos testing" y "swarm testing".

- Implementar un sistema de autenticación para que a los servidores solo se puedan conectar clientes autorizados y estos solamente tengan acceso a los RPC necesarios
