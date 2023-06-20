from kademlia.storage import PersistentStorage
import os
from kademlia.utils import digest
from pathlib import Path

def test_set_value():
    storage = PersistentStorage()

    storage.set_value('a', ('a').encode())
    val = storage.get_value('a')
    print(val)
    assert val == 'a'
    os.remove(Path(os.path.join(storage.db_path, str('a'))))


def test_unexpected_delete():
    storage = PersistentStorage()
    storage['1aaa'] = 'a'
    os.remove(Path(os.path.join(storage.db_path, str('1aaa'))))
    assert storage.get('1aaa') == None