# Descripción del sistema

El sistema utiliza un enfoque similar a Kademlia, donde las claves se almacenan como valores de 160 bits. Cada nodo en la red tiene un ID único y los pares (clave, valor) se almacenan en nodos con ID "cercanos" utilizando la métrica XOR propuesta por Kademlia.

El sistema trata los nodos como hojas de un árbol binario, donde la posición de cada nodo se determina por el prefijo único más corto de su ID. Estos nodos almacenan información de contacto para enrutar los mensajes de consulta.

Se utiliza el protocolo de Kademlia, que incluye los RPCs (Remote Procedure Calls) PING, STORE, FINDNODE y FIND-VALUE. Además, se implementan otros RPCs como CONTAINS, BOOTSTRAPPABLE-NEIGHBOR, GET, GET-FILE-CHUNKS, UPLOAD-FILE, SET-KEY, CHECK-IF-NEW-VALUE-EXIST, GET-FILE-CHUNK-VALUE, GET-FILE-CHUNK-LOCATION, FIND-CHUNK-LOCATION y FIND-NEIGHBORS, etc. A continuación se explica el funcionamiento de los mismos.

- `GET` : Obtiene la información identificada con la llave de un archivo, devuelve una lista con las llaves de cada chunk.
- `UPLOAD-FILE` : Sube el archivo al sistema de ficheros, lo divide en chunks
y guarda la metadata del archivo con la forma de unificar todos los chunks.
- `GET-FIND-CHUNK-VALUE` : Devuelve el valor asociado al chunk.
- `GET-FIND-CHUNK-LOCATION` : Recibe la llave de un chunk y devuelvemuna tupla (ip, puerto) donde se encuentra.
- `FIND-NEIGHBORS` : Devuelve los vecinos al nodo acorde a la cercanía según la métrica XOR.
Además, los servidores utilizan los siguientes RPCs:
- `CONTAINS` : Detecta si una llave está en un nodo, esto se utiliza tanto para la replicación de la información como para encontrar si un nodo tiene la información que se desea.
- `GET-FILE-CHUNKS` : Obtiene la lista de ubicaciones de los chunks de la información.
- `SET-KEY`: Guarda un par (llave, valor) en el sistema
- `DELETE`: Elimina un fichero de la red
- `GET-ALL-FILE-NAMES`: Realiza la función del comando `ls` en linux, devuelve una lista con todos los ficheros en el sistema(todas las llaves de metadata)

El sistema también cuenta con un módulo de persistencia llamado `PersistentStorage`, que maneja la escritura y lectura de datos. Utiliza las siguientes rutas:

- `static/metadata`: se almacenan los nombres de los archivos que representan los hash de los datos divididos en chunks de máximo 1000kb. Estos archivos contienen listas de Python guardadas con pickle, que contienen los hashes de cada chunk obtenido al dividir los datos.
- `static/keys`: se almacenan los nombres de los archivos que representan los hashes de los datos almacenados, ya sea de datos completos o de chunks. Estos archivos contienen los hashes correspondientes en bytes.
- `static/values`: se almacenan los nombres de los archivos que representan los hashes de los chunks almacenados, excluyendo los hashes de datos sin dividir.
- `timestamps`: se almacenan los nombres de los archivos que representan los hashes de los datos almacenados, al igual que en la ruta de `keys`, pero contienen un diccionario de Python guardado con pickle. Este diccionario tiene como claves `date` con el valor `datetime.now()`, `republish` con un valor booleano. Esta información se utiliza para llevar un registro de la última vez que se accedió a una llave y para determinar si es necesario republicar la información para mantener la propiedad del sistema de que los nodos mas cercanos a ella sean los q la tengan.

Cuando se recibe un par `(clave, valor)` en formato bytes, el módulo `PersistentStorage` codifica la clave utilizando `base64.urlsafe_b64encode` para obtener un string que se puede utilizar como nombre de archivo. Luego, se escribe un archivo con ese nombre en las rutas de `keys` y `values`, donde se guarda la clave en bytes en el archivo de keys y el valor en bytes en el archivo de values. En el caso de que el par a almacenar sea metadata, el valor en bytes se escribe en la ruta de metadata. En ambos casos, también se crea un archivo en la ruta de timestamps con el nombre correspondiente.

Antes de escribir un valor o metadata, se crea un diccionario con las llaves:

- `integrity`: Se utiliza para saber si el fichero esta corrupto, en caso de ser así, no se devuelve nunca.
- `value`: Valor a escribir
- `integrity_date`: Momento en q se setea por primera vez la integridad. En caso de que pase un tiempo determinado desde esta fecha e integrity este en False, se borra automáticamente el fichero.
- `key_name`: String de la llave q representa un fichero, se utiliza para poder devolver los nombres originales de los ficheros si se ejecuta el comando `ls` en el cliente
- `last_write`: Momento en el que se escribió por última vez el fichero. Se utiliza para manejar los casos en que luego de una partición, si se escribió en las dos particiones, valores con iguales llaves, al recuperarse la red, se mantengan los valores escritos más recientemente.

El enrutamiento en el sistema utiliza una estructura de tablas de enrutamiento similar a Kademlia. La tabla de enrutamiento es un árbol binario compuesto por k-buckets. Cada k-bucket contiene nodos con un prefijo común en sus ID, y el prefijo determina la posición del k-bucket en el árbol binario. Los k-buckets cubren diferentes partes del espacio de ID y, juntos, cubren todo el espacio de ID de 160 bits sin solaparse. Los nodos se asignan dinámicamente según sea necesario.

Para garantizar la replicación de datos, los nodos deben republicar periódicamente las claves. Esto se debe a que algunos de los k nodos que inicialmente obtienen un par clave-valor pueden abandonar la red, y nuevos nodos con IDs más cercanos a la clave pueden unirse a la red. Por lo tanto, los nodos que almacenan el par clave-valor deben republicarlo para asegurarse de que esté disponible en los k nodos más cercanos a la clave.

Cuando un cliente solicita un determinado valor al sistema, se le devuelve una lista de las ubicaciones de los distintos chunks de datos, que pueden estar en diferentes PCs. Luego, el cliente establece una conexión con la PC más cercana a la información para obtener los datos y unificarlos. Una vez que un nodo envía información, marca el archivo como pendiente de republicar y actualiza su timestamp, informando a los vecinos que también deben replicar la información.

Cuando un servidor descubre un nuevo nodo, para cada clave almacenada, el sistema recupera los k nodos más cercanos. Si el nuevo nodo está más cerca que el nodo más alejado de esa lista, y el nodo para este servidor está más cerca que el nodo más cercano de esa lista, entonces el par clave/valor se almacena en el nuevo nodo.

Cuando un servidor inicia una conexión nueva con un cliente, inicia un Thread nuevo para manejar dicha conexión.

Cuando el cliente comienza a subir un archivo, los datos se dividen en chunks de máximo 1000kb y se almacenan en el sistema de ficheros con `integrity` en `False`. Luego, se almacena la metadata del archivo, que contiene la información necesaria para unificar los chunks y reconstruir el archivo original también con `integrity` en `False`. Una vez que se confirma que se pudieron almacenar todos los chunks y la metadata, comienza a confirmarse la integridad de cada chunk en la red y después la de la metadata. En caso de ocurrir algún error en cualquier parte del proceso, se borra todo lo almacenado, haciendo el efecto de un rollback.
