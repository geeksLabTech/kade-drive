# Cliente

Se desarrolló un cliente que cuenta con las siguientes características:

- Puede recibir puntos de entrada a la red, conocidos como **bootstrap nodes**, para establecer una conexión directa con el sistema de archivos.
- Posee un mecanismo de autodescubrimiento que recibe mensajes de difusión (broadcast) en todas las NICs de la PC. Si no recibe ningún **bootstrap node** o no puede establecer conexión con ninguno, puede utilizar esta funcionalidad para encontrar automáticamente algún nodo.
- Tiene la capacidad de descubrir otros nodos automáticamente al conectarse con un nodo existente y obtener información sobre sus vecinos.
- Maneja errores relacionados con la inestabilidad de la red o caídas inesperadas de un nodo. Permite al usuario establecer el número de reintentos cuando se pierde la conexión con un nodo. Además, posee una cola con los nodos conocidos. Cuando se agotan los reintentos de conexión con un nodo, se elimina de la cola y se pasa al siguiente. También es posible especificar si se desea utilizar el mecanismo de autodescubrimiento cuando la cola está vacía.
