import sys
from kade_drive.client import ClientSession


def start_cli(ip=None, port=8086):
    initial_bootstrap_nodes = [(ip, int(port))] if ip else []
    client_session = ClientSession(initial_bootstrap_nodes)

    response = client_session.connect(use_broadcast_if_needed=True)
    if not response:
        print(
            "Error Connecting to the network, Please check your conectivity and verify that at least one server is online."
        )
        return

    print("Wellcome to CLI interface for distributed Filesystem")
    while True:
        command = input("cli > ").split(" ")
        if command[0] == "exit":
            break

        if command[0] == "help":
            print(
                """Command - args - description\n
put - %key %value - stores %value in the network asociated with %key
get - %key - gets the value asociated with %key
help - * - displays this message
exit - * - close the client
            """
            )
            continue
        args = command[1:] if len(command) >= 1 else []
        func = getattr(ClientSession, command[0], None)
        if func is None or not callable(func) :
            print(
                f'command {command[0]} not found, use "help" to see supported commands'
            )
            continue

        if not response:
            response = client_session.connect(use_broadcast_if_needed=True)
            if response is None:
                print(
                    "Error Connecting to the network, Please check your conectivity and verify that at least one server is online."
                )
                break
        result, response = func(client_session, *args)
        if result is not None:
            print(f"result > {result}")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        ip = sys.argv[1]

    if len(sys.argv) == 3:
        ip, port = sys.argv[1], sys.argv[2]

    start_cli()
