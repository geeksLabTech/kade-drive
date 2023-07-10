# Descripción del sistema

El sistema utiliza un enfoque similar a Kademlia, donde las claves se almacenan como valores de 160 bits. Cada nodo en la red tiene un ID único y los pares (clave, valor) se almacenan en nodos con ID "cercanos" utilizando la métrica XOR propuesta por Kademlia.

El sistema trata los nodos como hojas de un árbol binario, donde la posición de cada nodo se determina por el prefijo único más corto de su ID. Estos nodos almacenan información de contacto para enrutar los mensajes de consulta.

Se utiliza el protocolo de Kademlia, que incluye los RPCs (Remote Procedure Calls) PING, STORE, FINDNODE y FIND-VALUE. Además, se implementan otros RPCs como CONTAINS, BOOTSTRAPPABLE-NEIGHBOR, GET, GET-FILE-CHUNKS, UPLOAD-FILE, SET-KEY, CHECK-IF-NEW-VALUE-EXIST, GET-FILE-CHUNK-VALUE, GET-FILE-CHUNK-LOCATION, FIND-CHUNK-LOCATION y FIND-NEIGHBORS.

El sistema también cuenta con un módulo de persistencia llamado `PersistentStorage`, que maneja la escritura y lectura de datos. Utiliza las siguientes rutas:

- `static/metadata`: se almacenan los nombres de los archivos que representan los hash de los datos divididos en chunks de máximo 1000kb. Estos archivos contienen listas de Python guardadas con pickle, que contienen los hashes de cada chunk obtenido al dividir los datos.
- `static/keys`: se almacenan los nombres de los archivos que representan los hashes de los datos almacenados, ya sea de datos completos o de chunks. Estos archivos contienen los hashes correspondientes en bytes.
- `static/values`: se almacenan los nombres de los archivos que representan los hashes de los chunks almacenados, excluyendo los hashes de datos sin dividir.
- `timestamps`: se almacenan los nombres de los archivos que representan los hashes de los datos almacenados, al igual que en la ruta de `keys`, pero contienen un diccionario de Python guardado con pickle. Este diccionario tiene como claves `date` con el valor `datetime.now()`, `republish` con un valor booleano y `last_write`, que es un datetime que representa la última vez que se sobrescribió el archivo. Esta información se utiliza para llevar un registro de la última vez que se accedió a una llave y para determinar si es necesario republicar la información en caso de frecuentes accesos o en caso de partición de la red para mantener la consistencia eventual.

Cuando se recibe un par `(clave, valor)` en formato bytes, el módulo `PersistentStorage` codifica la clave utilizando `base64.urlsafe_b64encode` para obtener un string que se puede utilizar como nombre de archivo. Luego, se escribe un archivo con ese nombre en las rutas de `keys` y `values`, donde se guarda la clave en bytes en el archivo de keys y el valor en bytes en el archivo de values. En el caso de que el par a almacenar sea metadata, el valor en bytes se escribe en la ruta de metadata. En ambos casos, también se crea un archivo en la ruta de timestamps con el nombre correspondiente.

El enrutamiento en el sistema utiliza una estructura de tablas de enrutamiento similar a Kademlia. La tabla de enrutamiento es un árbol binario compuesto por k-buckets. Cada k-bucket contiene nodos con un prefijo común en sus ID, y el prefijo determina la posición del k-bucket en el árbol binario. Los k-buckets cubren diferentes partes del espacio de ID y, juntos, cubren todo el espacio de ID de 160 bits sin solaparse. Los nodos se asignan dinámicamente según sea necesario.

Para garantizar la replicación de datos, los nodos deben republicar periódicamente las claves. Esto se debe a que algunos de los k nodos que inicialmente obtienen un par clave-valor pueden abandonar la red, y nuevos nodos con IDs más cercanos a la clave pueden unirse a la red. Por lo tanto, los nodos que almacenan el par clave-valor deben republicarlo para asegurarse de que esté disponible en los k nodos más cercanos a la clave.

Cuando un cliente solicita un determinado valor al sistema, se le devuelve una lista de las ubicaciones de los distintos chunks de datos, que pueden estar en diferentes PCs. Luego, el cliente establece una conexión con la PC más cercana a la información para obtener los datos y unificarlos. Una vez que un nodo envía información, marca el archivo como pendiente de republicar y actualiza su timestamp, informando a los vecinos que también deben replicar la información.
