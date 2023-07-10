# Autodescubrimiento

Para el mecanismo de autodescubrimiento, también se crea un hilo (Thread) que emite un latido en las direcciones de broadcast de cada una de las NICs del host, con un identificador de la fuente del broadcast, la IP y el puerto "dfs ip puerto". Cada vez que un nuevo nodo se une a la red, escucha los mensajes de difusión (broadcast) para encontrar vecinos. Este mecanismo es accesible desde el cliente, lo que hace que la conexión sea transparente para el usuario.

## Desventajas de este enfoque

Una desventaja de este enfoque es que se utiliza el broadcast para el autodescubrimiento, lo que solo es posible en una red local o mediante el uso de una (o varias) PC como puentes entre diferentes subredes. Esto significa que si no existe una forma de conectar las computadoras localmente, no podrán descubrirse entre sí. Sin embargo, dado que el sistema está diseñado para la conexión de diferentes estaciones de trabajo, se asume que estarán en la misma red local, lo que hace factible este enfoque.
