## MessageSystem Dependency

`kade_drive` relies on the `MessageSystem` package as a side dependency for communication between new nodes and the network. `MessageSystem` provides a messaging system using multicast and broadcast, allowing for efficient message exchange.

The `MessageSystem` package is a separate Python package that needs to be installed as a prerequisite for using `kade_drive`. It handles the low-level communication aspects required for the functioning of `kade_drive`.

To install `MessageSystem`, you can use pip. Run the following command in your terminal:

```console
pip install message-system
```

## Usage

Once MessageSystem is installed, you can use kade_drive as described in this doc. It will automatically utilize the `MessageSystem` package for autodiscovery.
