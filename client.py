from http import server
import typer 
import socket
from typing import Optional, List
from kademlia.storage import PersistentStorage
from kademlia.network import Server
import time
import threading

app = typer.Typer()
running_server: Server|None = None



@app.command()
def get(key: str):
    server = Server()
    result = server.get(key)
    assert result is not None
    print(f'value is {result.decode()}')

@app.command()
def put(key: str, value: str):
    server = Server()
    result = server.set(key, value)
    print(f'info saved')




if __name__ == "__main__":
    app()
    # print('cli started')
