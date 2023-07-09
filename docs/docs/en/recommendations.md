# Recommendations

- In the event of a node failure, it is recommended to keep track of the ID of the previous node. If its information is still available on disk and up to date, loading it with this ID can be more efficient than starting as a new node and going through the network rebalancing process again.

- In the original implementation of Kademlia, node communication was done using UDP. However, UDP has limitations in handling large amounts of data. It was changed to TCP, which is less efficient for tasks other than data storage transfer. Implementing a dual communication protocol between nodes could improve network performance.
