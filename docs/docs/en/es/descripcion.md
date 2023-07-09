# Descripción del sistema

Al igual que muchos sistemas de tabla de hash distribuida, las llaves se almacenan en 160 bits. Cada uno de los ordenadores participantes en la red tiene un ID, y los pares (llave, valor) son almacenados en nodos con ID "cercanos", tomando como métrica de distancia la métrica `XOR` propuesta por Kademlia.

Al igual que Kademlia, se tratan los nodos como hojas de un árbol binario, en el que la posición de cada nodo viene determinada por el prefijo "único más corto" de su ID. Dichos nodos almacenan información de contacto entre sí para enrutar los mensajes de consulta.

Se usa como base el protocolo de Kademlia que garantiza que cada nodo conoce al menos un nodo de cada uno de sus subárboles (si contiene algún nodo); con esta garantía, cualquier nodo puede localizar a otro nodo por su ID.

Se cuenta con un módulo de persistencia llamado `PersistentStorage` que funciona de la siguiente manera:
Utiliza las rutas:

- `static/metadata`: los nombres de los ficheros en esta ruta representan el hash de unos datos que se dividieron en varios chunks de tamaño máximo 1000kb. Contienen como valor listas de Python guardadas con pickle que tienen los hashes de cada chunk obtenido al picar unos datos determinados.
- `static/keys`: los nombres de los ficheros en esta ruta representan todos los hashes de los datos almacenados, ya sea correspondiente a un dato completo o a un chunk de este. Contienen como valor los hashes correspondientes en bytes.
- `static/values`: los nombres de los ficheros en esta ruta representan los hashes de todos los chunks que se han almacenado, excluyendo hashes de datos sin picar.
- `timestamps`: los nombres de los ficheros en esta ruta representan todos los hashes de los datos almacenados, al igual que la ruta de keys, pero contienen como valor un diccionario de Python guardado con pickle que tiene como llaves `date` con el valor `datetime.now()`, `republish` con un valor booleano y `last_write` que es un datetime que represante la ultima vez q se se sobreescribio el archivo. Esto se usa para llevar un registro de la última vez que se accedió a `una llave, para saber si es necesario que el nodo que la contiene la republique porque es accedida con frecuencia y en caso de particion de la red mantener el valor escrito mas reciente y no la ultima informacion accedida, de este modo garantizando consistencia eventual.
  
- Cuando recibe un par `(llave, valor)`, ambos de tipo bytes, codifica la llave
usando `base64.urlsafeb64encode` para poder obtener un string que se pueda usar como nombre de un fichero, se escribe un fichero con ese nombre en en la ruta de keys y de values, de manera tal que en el de key se escriba
la llave en bytes y en el de values el valor en bytes. En el caso de que se
especifique que el par a guardar es metadata el fichero que contendr´a al
valor en bytes se escribe en la ruta de metadata. En ambos casos se crea
un fichero en la ruta de timestamps con el nombre correspondiente.

El protocolo de Kademlia contiene cuatro RPCs : `PING` , `STORE` , `FINDNODE` y `FIND-VALUE`. Esta propuesta adem´as de usar estos cuatro RPCs,
implementa `CONTAINS`, `BOOTSTRAPPABLE-NEIGHBOR`, `GET`, `GET-FILE-CHUNKS`, `UPLOAD-FILE`, `SET-KEY` `CHECK-IF-NEW-VALUE-EXIST`, `GET-FILE-CHUNK-VALUE`, `GET-FILE-CHUNK-LOCATION`, `FIND-CHUNK-LOCATION` y `FIND-NEIGHBORS`.

El cliente solo utiliza los siguientes rpcs:

- `GET`: Obtiene la informaci´on identificada con la llave de un archivo, devuelve una lista con las llaves de cada chunk
- `UPLOAD-FILE`: Sube el archivo al sitema de ficheros, lo pica en chunks y guarda la metadata del archivo con la forma de unificar todos los chunks.
- `GET-FIND-CHUNK-VALUE`: Devuelve el valor asociado al chunk
- `GET-FIND-CHUNK-LOCATION`: Recibe la llave de un chunk y devuelve una tupla `(ip, puerto)` donde se encuentra.
- `FIND-NEIGHBORS`: Devuelve los vecinos al nodo acorde a la cercania segun la metrica `XOR`

Los servidores ademas de los RPCs anteriores utilizan:

- `CONTAINS`: Detecta si una llave est´a en un nodo, esto se utiliza tanto
para la replicaci´on de la informaci´on como para encontrar si un nodo tiene
la informaci´on que se desea
- `GET-FILE-CHUNKS`: Obtiene la lista de ubicaciones de los chunks de la
informaci´on.
- `SET-KEY`: Guarda un par `(llave, valor)` en el sistema

Se utiliz´o la misma estructura de tablas de enrutamiento que Kademlia, la
tabla de enrutamiento es un ´arbol binario cuyas hojas son k-buckets. Cada kbucket contiene nodos con alg´un prefijo com´un en sus ID. El prefijo es la posici´on
del k-bucket en el ´arbol binario, por lo que cada k-bucket cubre una parte del
espacio de ID y, juntos, los k-buckets cubren todo el espacio de ID de 160 bits
sin solaparse. Los nodos del ´arbol de enrutamiento se asignan din´amicamente,
seg´un sea necesario.
Para garantizar la correcta replicaci´on de los datos, los nodos deben volver a
publicar peri´odicamente las llaves. De lo contrario, dos fen´omenos pueden hacer
que fallen las b´usquedas de llaves v´alidas. En primer lugar, algunos de los k
nodos que obtienen inicialmente un par llave-valor cuando se publica pueden
abandonar la red. En segundo lugar, pueden unirse a la red nuevos nodos con
ID m´as cercanos a alguna llave publicada que los nodos en los que se public´o
originalmente el par llave-valor. En ambos casos, los nodos con el par llave-valor
deben volver a publicar para asegurarse de que est´a disponible en los k nodos
m´as cercanos a la llave.
Una vez que un cliente pide al sistema un determinado valor, se le devuelve
una lista de las ubicaciones de los distintos chunks de datos (no necesariamente
estos se encuentran en la misma PC) y se crea una conexi´on con la PC m´as
cercana a la informaci´on de forma tal que la red no se sature innecesariamente.
Luego el cliente unifica los datos y devuelve el valor almacenado. Una vez que un
nodo env´ıa cierta informaci´on, marca ese archivo como pendiente de republicar
y actualiza su timestamp, de manera que se informa a cada uno de los vecinos
en los que se debe replicar la informaci´on que esta fue accedida y no ha de ser
eliminada
