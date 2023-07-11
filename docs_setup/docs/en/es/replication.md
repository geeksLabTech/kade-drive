# Replicación

Para el algoritmo de replicación implementado se utiliza un hilo (Thread) que se ejecuta en un intervalo de tiempo (i) y consiste en lo siguiente:

- Recorrer todas las llaves en el almacenamiento (storage) cuyo timestamp sea mayor que un tiempo (t). Aquellas llaves que tengan la propiedad `republish` en True son republicadas por el nodo.
- Recorrer todas las llaves en el almacenamiento y verificar en la red cuántas réplicas se pueden encontrar de cada una. Aquellas llaves que estén por debajo del factor de replicación especificado son republicadas por el nodo.
