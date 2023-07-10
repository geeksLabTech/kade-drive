# Replication

For the implemented replication algorithm, a thread is used to execute the following steps at a given time interval (i):

- Iterate through all keys in the storage whose timestamp is greater than a specified time (t). If the keys have the `republish` property set to True, the node republishes them.
- Iterate through all keys in the storage and check how many replicas can be found in the network for each key. If the number of replicas is below the specified replication factor, the node republishes them.
