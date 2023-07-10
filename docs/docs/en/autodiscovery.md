# 06 - Autodiscovery

For the autodiscovery mechanism, a `Thread` is also created that sends a heartbeat to the broadcast addresses of each NIC (Network Interface Card) on the host, with a broadcast source identifier and the IP and port "`dfs ip port`". Whenever a new node joins the network, it listens to the broadcasts to discover neighbors. This mechanism is accessible from the client, making the connection transparent to the user.

### Disadvantages of this approach

Since broadcast is used for autodiscovery, it is only possible within a local network or by using one (or multiple) PCs as a bridge between different subnets. If, for some reason, there is no way to connect computers locally, they will not be able to discover each other. However, since the system is designed for connecting different workstations, it is assumed that they will be on the same local network, making this approach feasible.
