# Replicación

Para algoritmo de republicaci´on implementado se utiliza un Thread que se
ejecuta cada un intervalo de tiempo i y consiste en lo siguiente:

- Recorrer todas las llaves en el storage cuyo timestamp sea mayor que un
tiempo t y aquellas que tengan republish en True son republicadas por el
nodo.
- Recorrer todas las llaves en el storage y verificar en la red cu´antas r´eplicas
puede encontrar de cada una, aquellas llaves que est´en por debajo del
factor de replicaci´on especificado son republicadas por el nodo.
