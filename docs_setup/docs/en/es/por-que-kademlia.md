# ¿Por qué Kademlia?

Una de las ventajas de Kademlia es la eficiencia de su algoritmo de enrutamiento, lo que permite una comunicación eficiente entre los nodos de la red. El prefijo binario de los ID de Kademlia hace que se envíe la información hacia el nodo más cercano, minimizando la cantidad de saltos entre nodos y la latencia de la red en general.

Otra de las ventajas de este protocolo es la capacidad de manejar fallos de nodos y particionado de la red. El mecanismo de republicación de Kademlia garantiza que se mantengan actualizadas las tablas de ruta de los nodos, manteniendo así la conectividad en la red y evitando la pérdida de datos dentro de lo posible.

Los datos pueden estar dispersos en múltiples nodos de la red. Kademlia utiliza una tabla hash distribuida para mantener un registro de la ubicación de los datos en la red. Esto permite que los nodos encuentren de manera eficiente la ubicación de los datos que necesitan procesar o analizar. Además, la arquitectura de Kademlia garantiza la tolerancia a fallos, lo que significa que si un nodo se desconecta o falla, los datos todavía estarán disponibles en otros nodos de la red.

Esta capacidad de almacenamiento y recuperación distribuida de datos de Kademlia es especialmente útil para los sistemas que suelen manejar grandes volúmenes de datos que necesitan ser procesados en paralelo. Al distribuir los datos entre varios nodos, se puede lograr un procesamiento y análisis más rápido y eficiente. En comparación con alternativas como Chord, Kademlia es una mejor opción para aplicaciones que requieran un enrutamiento eficiente y frecuentes actualizaciones de información, lo cual se cree que será el principal caso de uso de este sistema posterior a su integración con [Autogoal](https://github.com/autogoal/autogoal).

## Ejemplos reales del uso de Kademlia

Entre las compañías que utilizan este protocolo se encuentran:

- Storj: Plataforma de almacenamiento en la nube que en su versión 3 utilizó una versión modificada del protocolo para la implementación de un sistema con capacidades similares a un DNS.
- Protocolo Ethereum: El protocolo Ethereum utiliza una versión ligeramente modificada de Kademlia, manteniendo el método de identificación con XOR y los K-buckets.
- The Interplanetary FileSystem: En la implementación de IPFS, el NodeID contiene un mapa directo hacia los hash de archivos de IPFS. Cada nodo también almacena información sobre dónde obtener el archivo o recurso.
