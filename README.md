Distributed file system based on <https://github.com/bmuller/kademlia> for the final project of distributed systems

## Basic Usage

- Clone the repo and run poetry install
- Run server.py in one pc or several pc in a local network
- Run cli.py in any pc of the network and start playing with the system

## Installation

```console
- pip install kade-drive
```

## Server

```Python
from kade_drive.server import start_server

start_server()
```

## Client

### Note: Make shure that there exist at least a server in the local network

```Python
from kade_drive.cli import ClientSession

client = ClientSession()
client.connect()
client.put(4, 5)
value = client.get(4)
assert value == 5
```

### Tests

To run tests make shure that there is at least one server in the network.
