# 03 - Description

The system follows the approach of many distributed hash table systems, where keys are stored as 160-bit values. Each participating computer in the network has an ID, and the (key, value) pairs are stored on nodes with "close" IDs, using the XOR metric proposed by Kademlia as the distance metric.

Similar to Kademlia, nodes are treated as leaves in a binary tree, where the position of each node is determined by the "shortest unique prefix" of its ID. These nodes store contact information for each other to route query messages.

The system is based on the Kademlia protocol, which guarantees that each node knows at least one node from each of its subtrees (if they contain any nodes). With this guarantee, any node can locate another node by its ID.

There is a persistence module called PersistentStorage that operates as follows:
It uses the following paths:

- static/metadata: The file names in this path represent the hash of data that has been divided into multiple chunks with a maximum size of 1000kb. Each file contains a Python list stored with pickle, which holds the hashes of each chunk obtained from the data.
- static/keys: The file names in this path represent the hashes of stored data, whether it corresponds to a complete data or a chunk of it. Each file contains the corresponding hashes in bytes.
- static/values: The file names in this path represent the hashes of all the chunks that have been stored, excluding hashes of unchunked data.
- timestamps: The file names in this path represent the hashes of stored data, similar to the keys path. However, each file contains a Python dictionary stored with pickle, which has keys "date" with the value "datetime.now()" and "republish" with a boolean value. This is used to keep track of the last access time of a key and to determine if the node holding the key needs to republish it because it is frequently accessed.

When receiving a (key, value) pair, both of type bytes, the key is encoded using base64.urlsafeb64encode to obtain a string that can be used as a file name. A file is then written with that name in the keys and values paths. In the keys file, the key is written as bytes, and in the values file, the value is written as bytes. If the pair to be stored is metadata, the file containing the value as bytes is written in the metadata path. In both cases, a file is created in the timestamps path with the corresponding name.

The Kademlia protocol includes four RPCs: PING, STORE, FINDNODE, and FINDVALUE. In addition to using these four RPCs, this proposal implements the following:

- CONTAINS: Determines if a key exists in a node. This is used for both information replication and to find out if a node has the desired information.
- BOOTSTRAPPABLE-NEIGHBOR
- GET: Retrieves the information identified by the key of a chunk.
- GET-FILE-CHUNKS: Retrieves the list of locations of the chunks that make up the information.
- UPLOAD-FILE: Uploads a file to the file system, divides it into chunks, and stores the metadata of the file to unify all the files.
- SET-KEY
- FIND-NEIGHBORS

The same routing table structure as Kademlia is used. The routing table is a binary tree whose leaves are k-buckets. Each k-bucket contains nodes with a common prefix in their IDs. The prefix represents the position of the k-bucket in the binary tree, so each k-bucket covers a portion of the 160-bit ID space, and together, the k-buckets cover the entire ID space without overlap. The nodes of the routing tree are dynamically assigned as needed.

To ensure proper data replication, nodes need to periodically republish keys. Otherwise, two phenomena can cause valid key searches to fail. First, some of the k nodes that initially obtain a key-value pair when it is published may leave the network. Second, new nodes may join the network with IDs closer to a published key than the nodes on which the key-value pair was originally published. In both cases, nodes with the key-value pair need to republish to ensure it is available on the k nodes closest to the key.

When a client requests a specific value from the system, it receives a list of locations of the different data chunks (which may not be on the same PC). A connection is established with the PC closest to the information to avoid unnecessary network congestion. The client then combines the data and returns the stored value. Once a node sends certain information, that file is marked as pending for republication, and its timestamp is updated. This ensures that each of the neighboring nodes that need to replicate the information is informed that it has been accessed and should not be deleted.
