import time
from itertools import takewhile
import operator
from collections import OrderedDict
from abc import abstractmethod, ABC
from odmantic import SyncEngine
from models.file import File

class IStorage(ABC):
    """
    Local storage for this node.
    IStorage implementations of get must return the same type as put in by set
    """

    @abstractmethod
    def __setitem__(self, key, value):
        """
        Set a key to the given value.
        """

    @abstractmethod
    def __getitem__(self, key):
        """
        Get the given key.  If item doesn't exist, raises C{KeyError}
        """

    @abstractmethod
    def get(self, key, default=None):
        """
        Get given key.  If not found, return default.
        """

    @abstractmethod
    def iter_older_than(self, seconds_old):
        """
        Return the an iterator over (key, value) tuples for items older
        than the given secondsOld.
        """

    @abstractmethod
    def __iter__(self):
        """
        Get the iterator for this storage, should yield tuple of (key, value)
        """
        while False:
            yield None

class ForgetfulStorage(IStorage):
    def __init__(self, ttl=604800):
        """
        By default, max age is a week.
        """
        self.data = OrderedDict()
        self.ttl = ttl

    def __setitem__(self, key, value):
        if key in self.data:
            del self.data[key]
        self.data[key] = (time.monotonic(), value)
        self.cull()

    def cull(self):
        """
        Check if there exist data older that {self.ttl} and remove it.
        """
        for _, _ in self.iter_older_than(self.ttl):
            self.data.popitem(last=False)

    def get(self, key, default=None):
        self.cull()
        if key in self.data:
            return self[key]
        return default

    def __getitem__(self, key):
        self.cull()
        return self.data[key][1]

    def __repr__(self):
        self.cull()
        return repr(self.data)

    def iter_older_than(self, seconds_old):
        min_birthday = time.monotonic() - seconds_old
        zipped = self._triple_iter()
        matches = takewhile(lambda r: min_birthday >= r[1], zipped)
        return list(map(operator.itemgetter(0, 2), matches))

    def _triple_iter(self):
        ikeys = self.data.keys()
        ibirthday = map(operator.itemgetter(0), self.data.values())
        ivalues = map(operator.itemgetter(1), self.data.values())
        return zip(ikeys, ibirthday, ivalues)

    def __iter__(self):
        self.cull()
        ikeys = self.data.keys()
        ivalues = map(operator.itemgetter(1), self.data.values())
        return zip(ikeys, ivalues)


class PersistentStorage(IStorage):
    """
    This class allows to persist files on disk using mongodb.
    The class acts as an OrderedDict that his keys are the hash of an 
    specific file chunk and the value is the (ip, port) of the node that 
    has the chunk in his mongodb instance. In the current implementation
    the values of the dict are not used. The get method directly access to
    mongodb and retrieve the data that correspond to the given dict
    """
    def __init__(self, db_name='file_system', ttl=604800):
        """
        By default, max age is a week.
        """
        self.db = SyncEngine(database=db_name)
        self.data = OrderedDict()
        self.ttl = ttl
        # self.address = (ip, port)


    # def get_data_from_db(self, key: bytes):
    #     data = self.db.find_one(File, File.id == key)
    #     assert data is not None, 'Tried to get data that is not in db'
    #     return data

    def __setitem__(self, key, value):
        if key in self.data:
            del self.data[key]
            self.db.remove(File, File.id == key)

        self.data[key] = (time.monotonic())
        file_to_save = File(id=key, data=value)
        self.db.save(file_to_save)
        self.cull()

    def cull(self):
        """
        Check if there exist data older that {self.ttl} and remove it.
        """
        for _, _ in self.iter_older_than(self.ttl):
            key, _ = self.data.popitem(last=False)
            self.db.remove(File, File.id == key)

    def get(self, key, default=None):
        self.cull()
        if key in self.data:
            result = self.db.find_one(File, File.id == key)
            assert result is not None, 'Tried to get data that is not in db'
            return result.data
        return default

    def __getitem__(self, key):
        self.cull()
        result = self.db.find_one(File, File.id == key)
        if result is None:
            raise KeyError()
        return result

    def __repr__(self):
        self.cull()
        return repr(self.data)

    def iter_older_than(self, seconds_old):
        min_birthday = time.monotonic() - seconds_old
        zipped = self._triple_iter()
        matches = takewhile(lambda r: min_birthday >= r[1], zipped)
        return list(map(operator.itemgetter(0, 2), matches))

    def _triple_iter(self):
        ikeys = self.data.keys()
        ibirthday = map(operator.itemgetter(0), self.data.values())
        ivalues = map(operator.itemgetter(1), self.data.values())
        return zip(ikeys, ibirthday, ivalues)

    def __iter__(self):
        self.cull()
        ikeys = self.data.keys()
        # ivalues = map(operator.itemgetter(1), self.data.values())
        ivalues = self.db.find(File)
        return zip(ikeys, ivalues)
    
