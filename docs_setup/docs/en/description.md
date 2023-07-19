# System Description

The system utilizes a similar approach to Kademlia, where keys are stored as 160-bit values. Each node in the network has a unique ID, and the (key, value) pairs are stored on nodes with "close" IDs using the XOR metric proposed by Kademlia.

The system treats nodes as leaves of a binary tree, where the position of each node is determined by the shortest unique prefix of its ID. These nodes store contact information to route query messages.

The Kademlia protocol is used, which includes the PING, STORE, FINDNODE, and FIND-VALUE Remote Procedure Calls (RPCs). Additionally, other RPCs are implemented, such as CONTAINS, BOOTSTRAPPABLE-NEIGHBOR, GET, GET-FILE-CHUNKS, UPLOAD-FILE, SET-KEY, CHECK-IF-NEW-VALUE-EXIST, GET-FILE-CHUNK-VALUE, GET-FILE-CHUNK-LOCATION, FIND-CHUNK-LOCATION, and FIND-NEIGHBORS.

- `GET`: Retrieves information identified by the key of a file, returns a list with the keys of each chunk.
- `UPLOAD-FILE`: Uploads the file to the file system, divides it into chunks, and saves the file's metadata in a way that unifies all the chunks.
- `GET-FIND-CHUNK-VALUE`: Returns the value associated with the chunk.
- `GET-FIND-CHUNK-LOCATION`: Receives the key of a chunk and returns a tuple (IP, port) where it is located.
- `FIND-NEIGHBORS`: Returns the neighbors to the node according to proximity based on the XOR metric. Additionally, the servers use the following RPCs:
- `CONTAINS`: Determines if a key is in a node. This is used for both information replication and to find if a node has the desired information.
- `GET-FILE-CHUNKS`: Retrieves the list of chunk locations for the information.
- `SET-KEY`: Stores a key-value pair in the system.
- `DELETE`: Deletes a file from the network.
- `GET-ALL-FILE-NAMES`: Performs the function of the `ls` command in Linux, returns a list of all files in the system (all metadata keys).

The system also includes a persistence module called `PersistentStorage`, which handles data read and write operations. It uses the following paths:

- `static/metadata`: stores the filenames representing the hashes of the data divided into chunks of up to 1000kb. These files contain Python lists saved with pickle, which contain the hashes of each chunk obtained by splitting the data.
- `static/keys`: stores the filenames representing the hashes of the stored data, either complete data or chunks. These files contain the corresponding hashes in bytes.
- `static/values`: stores the filenames representing the hashes of the stored chunks, excluding the hashes of undivided data.
- `timestamps`: The file names representing the hashes of the stored data are stored, similar to the keys path, but they contain a Python dictionary saved with Pickle. This dictionary has keys such as date with the value datetime.now() and republish with a boolean value. This information is used to keep track of the last time a key was accessed and to determine if it is necessary to republish the information in order to maintain the system's property that the closest nodes to it are the ones that have it.

When a `(key, value)` pair is received as bytes, the `PersistentStorage` module encodes the key using `base64.urlsafe_b64encode` to obtain a string that can be used as a filename. Then, a file is written with that name in the `keys` and `values` paths, where the key is saved as bytes in the keys file and the value is saved as bytes in the values file. In the case of storing metadata, the value as bytes is written in the metadata path. In both cases, a corresponding file is also created in the timestamps path.

Before writing a value or metadata, a dictionary is created with the following keys:

- `integrity`: Used to determine if the file is corrupt. If it is, it is never returned.
- `value`: Value to be written.
- `integrity_date`: The moment when the integrity is first set. If a certain amount of time has passed since this date and integrity is still False, the file is automatically deleted.
- `key_name`: String representing the file's key. It is used to retrieve the original file names if the `ls` command is executed on the client.
- `last_write`: The moment when the file was last written. It is used to handle cases where, after a partition, if the same keys were written in both partitions, the most recently written values are maintained after network recovery.

Routing in the system utilizes a routing table structure similar to Kademlia. The routing table is a binary tree composed of k-buckets. Each k-bucket contains nodes with a common prefix in their IDs, and the prefix determines the position of the k-bucket in the binary tree. The k-buckets cover different parts of the ID space and together cover the entire 160-bit ID space without overlap. Nodes are dynamically assigned to k-buckets as needed.

To ensure data replication, nodes must periodically republish keys. This is because some of the k nodes that initially obtain a key-value pair may leave the network, and new nodes with IDs closer to the key may join the network. Therefore, nodes that store the key-value pair must republish it to ensure it is available on the k nodes closest to the key.

When a client requests a certain value from the system, they are returned a list of locations of the different data chunks, which may be on different PCs. The client then establishes a connection with the PC closest to the information to retrieve the data and unify it. Once a node sends information, it marks the file as pending republishing and updates its timestamp, informing neighbors that they should also replicate the information.

When a server discovers a new node, for each key in storage, the system retrieves the k closest nodes. If the new node is closer than the furthest node in that list, and the node for this server is closer than the closest node in that list, then the key/value pair is stored on the new node.

The server spawns a thread for each connection, supporting multiple clients.

When the client starts uploading a file, the data is divided into chunks of a maximum size of 1000kb, and they are stored in the file system with integrity set to False. Then, the metadata of the file is stored, which contains the necessary information to unify the chunks and reconstruct the original file, also with integrity set to False. Once it is confirmed that all the chunks and metadata could be successfully stored, the integrity of each chunk in the network is verified, followed by the integrity of the metadata. In case an error occurs at any point in the process, everything stored is deleted, mimicking a rollback effect.