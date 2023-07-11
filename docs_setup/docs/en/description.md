# System Description

The system utilizes a similar approach to Kademlia, where keys are stored as 160-bit values. Each node in the network has a unique ID, and the (key, value) pairs are stored on nodes with "close" IDs using the XOR metric proposed by Kademlia.

The system treats nodes as leaves of a binary tree, where the position of each node is determined by the shortest unique prefix of its ID. These nodes store contact information to route query messages.

The Kademlia protocol is used, which includes the PING, STORE, FINDNODE, and FIND-VALUE Remote Procedure Calls (RPCs). Additionally, other RPCs are implemented, such as CONTAINS, BOOTSTRAPPABLE-NEIGHBOR, GET, GET-FILE-CHUNKS, UPLOAD-FILE, SET-KEY, CHECK-IF-NEW-VALUE-EXIST, GET-FILE-CHUNK-VALUE, GET-FILE-CHUNK-LOCATION, FIND-CHUNK-LOCATION, and FIND-NEIGHBORS.

The system also includes a persistence module called `PersistentStorage`, which handles data read and write operations. It uses the following paths:

- `static/metadata`: stores the filenames representing the hashes of the data divided into chunks of up to 1000kb. These files contain Python lists saved with pickle, which contain the hashes of each chunk obtained by splitting the data.
- `static/keys`: stores the filenames representing the hashes of the stored data, either complete data or chunks. These files contain the corresponding hashes in bytes.
- `static/values`: stores the filenames representing the hashes of the stored chunks, excluding the hashes of undivided data.
- `timestamps`: stores the filenames representing the hashes of the stored data, similar to the `keys` path, but containing a Python dictionary saved with pickle. This dictionary has keys such as `date` with the value `datetime.now()`, `republish` with a boolean value, and `last_write`, which is a datetime representing the last time the file was overwritten. This information is used to keep track of the last time a key was accessed and to determine whether it is necessary to republish the information in case of frequent accesses or network partition to maintain eventual consistency.

When a `(key, value)` pair is received as bytes, the `PersistentStorage` module encodes the key using `base64.urlsafe_b64encode` to obtain a string that can be used as a filename. Then, a file is written with that name in the `keys` and `values` paths, where the key is saved as bytes in the keys file and the value is saved as bytes in the values file. In the case of storing metadata, the value as bytes is written in the metadata path. In both cases, a corresponding file is also created in the timestamps path.

Routing in the system utilizes a routing table structure similar to Kademlia. The routing table is a binary tree composed of k-buckets. Each k-bucket contains nodes with a common prefix in their IDs, and the prefix determines the position of the k-bucket in the binary tree. The k-buckets cover different parts of the ID space and together cover the entire 160-bit ID space without overlap. Nodes are dynamically assigned to k-buckets as needed.

To ensure data replication, nodes must periodically republish keys. This is because some of the k nodes that initially obtain a key-value pair may leave the network, and new nodes with IDs closer to the key may join the network. Therefore, nodes that store the key-value pair must republish it to ensure it is available on the k nodes closest to the key.

When a client requests a certain value from the system, they are returned a list of locations of the different data chunks, which may be on different PCs. The client then establishes a connection with the PC closest to the information to retrieve the data and unify it. Once a node sends information, it marks the file as pending republishing and updates its timestamp, informing neighbors that they should also replicate the information.

For each key in storage, the system retrieves the k closest nodes. If the new node is closer than the furthest node in that list, and the node for this server is closer than the closest node in that list, then the key/value pair is stored on the new node.
