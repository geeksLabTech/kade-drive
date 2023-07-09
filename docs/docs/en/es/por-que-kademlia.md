# ¿Por qué Kademlia?
Una de las ventajas de Kademlia es la eficiencia de su algoritmo de enrutamiento, lo que permite una comunicaci´on eficiente entre los nodos de la red. El
prefijo binario de los ID de kademlia hace que se env´ıe la informaci´on hacia el
nodo m´as cercano, minimizando la cantidad de saltos entre nodos y la latencia
de la red en general.
Otra de las ventajas de este protocolo es la capacidad de manejar fallos de
nodos y particionado de la red. El mecanismo de refrescado de Kademlia garantiza que se mantengan actualizadas las tablas de ruta de los nodos, manteniendo
as´ı la conectividad en la red y evitando la p´erdida de datos dentro de lo posible.
Los datos pueden estar dispersos en m´ultiples nodos de la red. Kademlia
utiliza una tabla hash distribuida para mantener un registro de la ubicaci´on de
los datos en la red. Esto permite que los nodos encuentren de manera eficiente la
ubicaci´on de los datos que necesitan procesar o analizar. Adem´as, la arquitectura
de Kademlia garantiza la tolerancia a fallos, lo que significa que si un nodo se
desconecta o falla, los datos todav´ıa estar´an disponibles en otros nodos de la
red. Esta capacidad de almacenamiento y recuperaci´on distribuida de datos de
Kademlia es especialmente ´util para los sistemas que suelen manejar grandes
vol´umenes de datos que necesitan ser procesados en paralelo. Al distribuir los
datos entre varios nodos, se puede lograr un procesamiento y an´alisis m´as r´apido
y eficiente.

## Ejemplos reales del uso de kademlia

Entre las compa˜n´ıas que utilizan este protocolo se encuentran:
- Storj: Plataforma de almacenamiento en la nube que en su versi´on 3
utiliz´o una versi´on modificada del protocolo para la implementaci´on de un
sistema con capacidades similares a un DNS
- Protocolo Ethereum: El protocolo Ethereum utiliza una versi´on ligeramente modificada de kademlia, manteniendo el m´etodo de identificaci´on con XOR y los K-buckets
- The InterplanetaryFileSystem: En la implementaci´on de IPFS, el NodeID contiene un mapa directo hacia los hash de archivos de IPFS. Cada nodo tambi´en almacena informaci´on sobre d´onde obtener el archivo o
recurso.
