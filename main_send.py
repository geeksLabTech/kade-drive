from message_system.message_system import Message_System
import time

if __name__ == "__main__":
    print("starting")
    ms = Message_System()
    ms.add_to_send("testing broadcast", -1)

    while True:
        ms.send()
        time.sleep(0.5)
