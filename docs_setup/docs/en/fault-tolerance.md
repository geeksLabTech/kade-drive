# 08 - Fault Tolerance

Nodes maintain information about other nodes in the network by storing them in their routing table. Each node has a list of "k-buckets" that contain the contact details of other nodes in the network, classified based on their proximity in the ID space.

When a node becomes unresponsive or disconnects, other nodes in the network detect the lack of response after a certain period of time. At that point, the failed node is considered inactive.

When a node detects the inactivity of another node, it updates its routing table by removing the entry of the failed node. Additionally, the node performs a series of actions to maintain connectivity and redundancy in the network.

- Data Replication: If the failed node was storing data, other nodes in the network can take the responsibility of maintaining replicas of that data. This ensures that the data remains available even if the original node disconnects. The nodes that will assume this responsibility are those that are closest using the same XOR metric with IDs to keep the network as optimized as possible.

- Responsibility Transfer: If the failed node was responsible for certain identifiers in the network, other nodes take over the responsibility of handling them. This ensures that access to the data or resources is not lost.

- Routing Information Update: Nodes that had the failed node in their routing table update that entry by removing it. This way, nodes avoid sending messages or performing actions towards a node that is no longer available.

The expiration of contact ensures that the information stored in the network remains accessible even when individual nodes fail. By removing inactive nodes from the buckets, it ensures that routing paths are updated and kept efficient.
