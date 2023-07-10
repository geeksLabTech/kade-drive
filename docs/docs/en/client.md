# 05 - Client

A client has been developed with the following features:

- It can receive entry points to the network, known as bootstrap nodes, for a direct connection to the file system.
- It has an autodiscovery mechanism that listens to broadcasts on all NICs (Network Interface Cards) of the PC. If it doesn't receive any bootstrap node or is unable to connect to any, it can use this functionality to automatically discover a node.
- It has the ability to discover other nodes automatically by connecting to a node and exploring its neighbors.
- It handles errors related to network instability or unexpected node failures. The user can specify the number of connection retries when a connection to a node is lost. It maintains a queue of known nodes, and when the maximum number of connection retries is reached for a node, it is removed from the queue and the next node is used. It is also possible to specify whether the autodiscovery mechanism should be used when the queue becomes empty.
