# Tolerancia a Fallas

Los nodos mantienen información sobre otros nodos cercanos en la red, almacenando estos nodos en su tabla de enrutamiento. Cada nodo tiene una lista de `k-buckets` que contienen los detalles de contacto de otros nodos en la red, clasificados según su proximidad en el espacio de identificación.

Cuando un nodo deja de responder o se desconecta, los otros nodos de la red detectan la falta de respuesta después de un período de tiempo determinado. En ese momento, se considera que el nodo fallido está inactivo.

Cuando un nodo detecta la inactividad de otro nodo, actualiza su tabla de enrutamiento eliminando la entrada del nodo fallido. Además, el nodo realiza una serie de acciones para mantener la conectividad y la redundancia en la red.

- Replicación de datos: Si el nodo fallido almacenaba datos, otros nodos de la red pueden asumir la responsabilidad de mantener réplicas de esos datos. De esta manera, los datos permanecen disponibles incluso si el nodo original se desconecta. Los nodos que asumirán esta responsabilidad serán aquellos que estén más cercanos utilizando la misma métrica de XOR con los IDs para mantener la red lo más optimizada posible.

- Actualización de información de enrutamiento: Los nodos que tenían al nodo fallido en su tabla de enrutamiento actualizan esa entrada eliminándola. De esta manera, los nodos evitan enviar mensajes o realizar acciones hacia un nodo que ya no está disponible.

- La expiración de contacto garantiza que la información almacenada en la red permanezca accesible incluso cuando los nodos individuales fallan. Al eliminar los nodos inactivos de los buckets, se asegura de que las rutas de enrutamiento se actualicen y se mantengan eficientes.
