# Autodescubrimiento

Para el mecanismo de auto descubrimiento se crea tambi´en un Thread que
emite un latido en las direcciones de broadcast de cada una de las NICs del host,
con un identificador de la fuente del broadcast e ip y puerto ”dfs ip puerto”.
Cada vez que un nuevo nodo entra a la red escucha los broadcast para encontrar
vecinos. El mecanismo es accesible desde el cliente, haciendo transparente la
conexi´on para el usuario.

## Desventajas de este enfoque
Como se utiliza broadcast para el autodescubrimiento esto solo es posible
en una red local, o utilizando una (o varias) PC como puente entre distintas
subredes, haciendo que si por alguna raz´on no existiese una forma de conectar
localmente las computadoras, estas no ser´an capaces de encontrarse, no obstante
como el sistema est´a pensado para conexi´on de distintas estaciones de trabajo
se asume que estas estar´an en la misma red local haciendo factible este enfoque.
