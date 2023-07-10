# Tolerancia a Fallas

Los nodos mantienen informaci´on sobre otros nodos cercanos en la red, almacenando estos nodos en su tabla de enrutamiento. Cada nodo tiene una lista
de `k-buckets` que contienen los detalles de contacto de otros nodos en la red,
clasificados seg´un su proximidad en el espacio de identificaci´on.
Cuando un nodo deja de responder o se desconecta, los otros nodos de la red
detectan la falta de respuesta despu´es de un per´ıodo de tiempo determinado.
En ese momento, se considera que el nodo fallido est´a inactivo.
Cuando un nodo detecta la inactividad de otro nodo, actualiza su tabla de
enrutamiento eliminando la entrada del nodo fallido. Adem´as, el nodo realiza
una serie de acciones para mantener la conectividad y la redundancia en la red.

- Replicaci´on de datos: Si el nodo fallido almacenaba datos, otros nodos
de la red pueden tomar la responsabilidad de mantener r´eplicas de esos
datos. De esta manera, los datos permanecen disponibles incluso si el nodo
original se desconecta. Los nodos que asumir´an esta responsabilidad ser´an
los que est´en m´as cercanos utilizando la misma m´etrica de XOR con los
IDs para mantener la red lo m´as optimizada posible.

- Actualizaci´on de informaci´on de enrutamiento: Los nodos que ten´ıan
al nodo fallido en su tabla de enrutamiento actualizan esa entrada elimin´andola. De esta manera, los nodos evitan enviar mensajes o realizar
acciones hacia un nodo que ya no está disponible.

- La expiraci´on de contacto garantiza que la informaci´on almacenada en la red
permanezca accesible incluso cuando los nodos individuales fallan. Al eliminar
los nodos inactivos de los buckets, se asegura de que las rutas de enrutamiento
se actualicen y se mantengan eficientes
