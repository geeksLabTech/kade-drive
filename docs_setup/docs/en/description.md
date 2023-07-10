# Client

A client has been developed with the following features:

- It can receive entry points to the network, known as **bootstrap nodes**, to establish a direct connection with the file system.
- It has a self-discovery mechanism that listens for broadcast messages on all NICs of the PC. If it doesn't receive any **bootstrap node** or can't establish a connection with any, it can use this functionality to automatically find a node.
- It has the ability to automatically discover other nodes by connecting to an existing node and obtaining information about its neighbors.
- It handles errors related to network instability or unexpected node failures. The user can set the number of connection retries when the connection to a node is lost. It also maintains a queue of known nodes. When the connection retries with a node are exhausted, it is removed from the queue and the next one is tried. It is also possible to specify whether to use the self-discovery mechanism when the queue is empty.
