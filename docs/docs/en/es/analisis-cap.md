# Análisis del teorema CAP
El teorema CAP, tambi´en conocido como el teorema de Brewer, es un concepto fundamental en los sistemas distribuidos que establece que es imposible
que un almac´en de datos distribuido proporcione simult´aneamente consistencia
(C), disponibilidad (A) y tolerancia a particiones (P).

- Consistencia (C): La consistencia se refiere a que todos los nodos en un
sistema distribuido tengan la misma visi´on de los datos al mismo tiempo. En este
sistema, lograr una consistencia estricta en todos los nodos no es una prioridad.
En cambio, se garantiza en la consistencia eventual, lo que significa que con el
tiempo, todos los nodos converger´an al mismo estado. Los nodos intercambian
peri´odicamente informaci´on y actualizan sus tablas de enrutamiento para lograr
esta convergencia.

- Disponibilidad (A): La disponibilidad implica que el sistema permanezca
receptivo y accesible para los usuarios incluso en presencia de fallos de nodos
o particiones de red. EL sistema prioriza la disponibilidad asegurando que los
nodos puedan seguir operando y proporcionando servicios incluso cuando algunos nodos est´en no disponibles o inalcanzables. Esto se logra a trav´es de la
redundancia y la replicaci´on de datos, donde se almacenan m´ultiples copias de
datos en diferentes nodos.

- Tolerancia a particiones (P): La tolerancia a particiones se refiere a
la capacidad del sistema para continuar funcionando y proporcionar servicios
a pesar de particiones o fallos en la red. El sistema est´a dise˜nado para ser
tolerante a particiones, lo que permite que la red siga operando y mantenga su
funcionalidad incluso cuando los nodos est´en temporalmente desconectados o
aislados debido a problemas de red.

Todos estos puntos se analizan asumiendo que no se sobrepasa la capacidad
de recuperaci´on del sistema, si se superase dicho punto el sistema comenzar´a
a ver afectada la disponibilidad. Pero esto solo Ocurrir´ıa en caso de fallos simult´aneos, puesto que el sistema es capaz de recuperarse de fallos eventuales
sin ning´un problema.
