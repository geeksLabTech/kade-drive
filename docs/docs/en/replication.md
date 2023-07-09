# Replication

The implemented replication algorithm uses a Thread that runs at a specified time interval (i) and performs the following steps:

1. Iterate through all the keys in the storage whose timestamp is greater than a given time (t). Republish the keys that have the "republish" flag set to True.

2. Iterate through all the keys in the storage and check how many replicas of each key can be found in the network. If the number of replicas is below the specified replication factor, the node republishes those keys.
