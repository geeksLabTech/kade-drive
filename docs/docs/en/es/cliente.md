# Cliente

Se desarrolló un cliente que cuenta con las siguientes características:

- Puede recibir puntos de entrada a la red, conocidos como bootstrap nodes
para una conexi´on directa con el sistema de ficheros
- Posee un mecanismo de auto-descubrimiento recibiendo broadcast por todas las NICs de la pc, si no recibe ning´un bootstrap node o no es capaz de
conectar con ninguno puede usar esta funcionalidad para encontrar alg´un
nodo autom´aticamente.
- Tiene la capacidad de al conectar con alg´un nodo descubir otros nodos a
partir de los vecinos de este de manera autom´atica.
- Maneja errores relacionados con inestabilidad de la red o ca´ıdas inesperadas de un nodo, permitiendo que el usuario establezca el n´umero de
reintentos que se debe hacer cuando se pierde la conexi´on con un nodo,
posee un cola con los nodos conocidos que al agotarse el n´umero de reintentos de conexi´on con un nodo, este es removido de la cola y se pasa
al siguiente, es posible especificar tambi´en si se quiere que se utilice el
mecanismo de auto-descubribimiento al quedarse la cola vac´ıa.
