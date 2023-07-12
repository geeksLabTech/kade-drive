# Recommendations

- In the event of a node failure in the network, it is recommended to somehow keep the ID of the previous node. If its information is still stored and updated on disk, loading with this ID can be more efficient than starting as a new node and going through the network rebalancing process again.

- In the original implementation of Kademlia, node communication was done using UDP. However, due to UDP's limitations in handling large amounts of information, it was changed to TCP. Nevertheless, TCP is less efficient for tasks other than storage data transfer. Implementing a dual communication protocol between nodes should improve network performance.

- Consider changing the hash algorithm used from SHA1 to SHA256, as SHA1 is no longer considered secure and its vulnerabilities facilitate malicious activities.

- Implement a distributed automatic testing mechanism using techniques like "chaos testing" and "swarm testing".

- Implement an authentication system so that only authorized clients can connect to the servers and these only have access to the necessary RPCs.
