![Python Version](https://img.shields.io/badge/Python-3.10-blue)
![Code Style](https://img.shields.io/badge/Code%20Style-Black-black)
![Poetry Version](https://img.shields.io/badge/Poetry-1.3.1-blue)
![Docker Support](https://img.shields.io/badge/Docker-Supported-brightgreen?logo=docker)
![Docker Build Status](https://img.shields.io/docker/build/geekslabtech/kade-drive)
![Visits](https://badges.pufler.dev/visits/geeksLabTech/kade-drive)
![Contributors](https://img.shields.io/github/contributors/geeksLabTech/kade-drive)
![Release Version](https://img.shields.io/github/v/release/geeksLabTech/kade-drive)
![Documentation](https://img.shields.io/badge/docs-available-brightgreen)
![Package Version](https://img.shields.io/pypi/v/kade-drive)
![Downloads](https://img.shields.io/pypi/dm/kade-drive)
![Release Date](https://img.shields.io/github/release-date/geeksLabTech/kade-drive)
![Code Size](https://img.shields.io/github/languages/code-size/geeksLabTech/kade-drive)

Distributed file system based on <https://github.com/bmuller/kademlia> for the final project of distributed systems

## Documentation

<https://geekslabtech.github.io/kade-drive/>

## Basic Usage

- Clone the repo and run `poetry install`
- Run `poetry run server` in one pc or several pc in a local network
- Run `poetry run cli` in any pc of the network and start playing with the system

### Usage with docker

- Build the image with `make docker`
- Run `make shell` to start the Docker container with an interactive Bash shell
- Now you can run `poetry run server` to start a server or `poetry run cli`

## Installation

```console
pip install kade-drive
```

## Server

```Python
from kade_drive.server import start_server

start_server()
```

## Client

### Note: Make sure that there exist at least a server in the local network

```Python
from kade_drive.cli import ClientSession

client = ClientSession()
client.connect()
response, _ = client.put(4, 5)
# If true, it means that the value was setted correctly, false otherwise
assert response is True
value, _ = client.get(4)
assert value == 5
```

### Tests

To run tests make shure that there is at least one server in the network.
