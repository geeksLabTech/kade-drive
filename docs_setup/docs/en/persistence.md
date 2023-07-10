# Persistence

By default, the information is configured to persist in the system for 1 week if it is not accessed. However, for demonstration purposes, a time of 2 minutes is used to evaluate the proper functioning of the system. In production, the time interval for removing data should be analyzed according to the system requirements.

It is important to note that this file system is designed for the interaction of different nodes in the network and not as a long-term information persistence system. Therefore, it is decided to remove information that is not being used to ensure that new data can be stored by the training algorithms.

This removal mechanism is implemented through a thread whose sole purpose is to check the timestamps of the files and delete those that fall outside the predefined time window.
