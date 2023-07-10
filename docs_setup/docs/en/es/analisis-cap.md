# Análisis del teorema CAP

El teorema CAP, también conocido como el teorema de Brewer, es un concepto fundamental en los sistemas distribuidos que establece que es imposible que un almacén de datos distribuido proporcione simultáneamente consistencia (C), disponibilidad (A) y tolerancia a particiones (P).

- Consistencia (C): La consistencia se refiere a que todos los nodos en un sistema distribuido tengan la misma visión de los datos al mismo tiempo. En este sistema, lograr una consistencia estricta en todos los nodos no es una prioridad. En cambio, se garantiza la consistencia eventual, lo que significa que con el tiempo, todos los nodos convergerán al mismo estado. Los nodos intercambian periódicamente información y actualizan sus tablas de enrutamiento para lograr esta convergencia.

- Disponibilidad (A): La disponibilidad implica que el sistema permanezca receptivo y accesible para los usuarios incluso en presencia de fallos de nodos o particiones de red. El sistema prioriza la disponibilidad asegurando que los nodos puedan seguir operando y proporcionando servicios incluso cuando algunos nodos estén no disponibles o inalcanzables. Esto se logra a través de la redundancia y la replicación de datos, donde se almacenan múltiples copias de datos en diferentes nodos.

- Tolerancia a particiones (P): La tolerancia a particiones se refiere a la capacidad del sistema para continuar funcionando y proporcionar servicios a pesar de particiones o fallos en la red. El sistema está diseñado para ser tolerante a particiones, lo que permite que la red siga operando y mantenga su funcionalidad incluso cuando los nodos estén temporalmente desconectados o aislados debido a problemas de red.

Todos estos puntos se analizan asumiendo que no se sobrepasa la capacidad de recuperación del sistema. Si se superase dicho punto, el sistema comenzaría a verse afectada la disponibilidad. Pero esto solo ocurriría en caso de un cierto número de fallos simultáneos, puesto que el sistema es capaz de recuperarse de fallos eventuales sin ningún problema.
