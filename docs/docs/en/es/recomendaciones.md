# Recomendaciones

- Dada la ca´ıda de un nodo de la red, mantener de alguna manera el id del
nodo anterior para si su informaci´on se mantuviese a´un en disco y actualizada
cargar con este id puede ser m´as eficiente que iniciar como un nodo nuevo y
comanzar nuevamente el proceso de balanceo de la red.
- En la implementaci´on original de kademlia, la comunicaci´on entre nodos
se realiza mediante `UDP`. Dada la limitaci´on de `UDP` para manejar grandes
cantidades de informaci´on se cambi´o a `TCP`, pero esta es menos eficiente para
las tareas que no sean transferencia de datos de almacenamiento. Implementar
un doble protocolo de comunicaci´on entre los nodos deber´ıa representar una
mejor´ıa en el rendimiento de la red.
- Cambiar el algoritmo de hash utilizado de sha1 a sha256 dado q sha1 ya no es considerado
seguro y sus vulnerabilidades hacen mas facil a los atacantes realizar actividades maliciosas
- Implementar un mecanismo de testing automatico distribuido utilizando tecnicas como `chaos testing`
y `swarm testing`
