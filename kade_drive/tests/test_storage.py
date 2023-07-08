# from kademlia.storage import PersistentStorage
# import os
# from kademlia.utils import digest
# from pathlib import Path
# from time import sleep


# def test_set_value():
#     storage = PersistentStorage()

#     storage.set_value('a', ('a').encode())
#     val = storage.get_value('a')
#     print(val)
#     assert val == 'a'
#     os.remove(Path(os.path.join(storage.db_path, str('a'))))
#     os.remove(Path(os.path.join(storage.timestamp_path, str('a'))))

#     storage.stop_thread()


# def test_delete_old():
#     storage = PersistentStorage(ttl=4)

#     storage["a"] = "b"
#     sleep(6)
#     assert storage.get('a') is None

#     storage['c'] = 'b'
#     sleep(3)
#     storage.get('c')
#     sleep(3)
#     assert storage.get('c') == 'b'

#     storage.stop_thread()


# def test_unexpected_delete():
#     storage = PersistentStorage(ttl=2)
#     storage['1aaa'] = 'a'
#     os.remove(Path(os.path.join(storage.db_path, str('1aaa'))))
#     os.remove(Path(os.path.join(storage.timestamp_path, str('1aaa'))))
#     assert storage.get('1aaa') is None

#     storage.stop_thread()


# def test_contain_value():
#     storage = PersistentStorage(ttl = 2)
#     storage['a'] = 'b'
#     sleep(1)
#     assert storage.contains('a') == True
#     sleep(1)
#     assert storage.contains('a') == True
#     sleep(1)
#     assert storage.contains('a') == True
#     sleep(5)
#     assert storage.contains('a') == False

#     storage.stop_thread()
