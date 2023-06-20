import os
import time
import operator
from datetime import datetime
from time import sleep
from collections import OrderedDict
from abc import abstractmethod, ABC
from pathlib import Path
import threading


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

    # @abstractmethod
    # def iter_older_than(self, seconds_old):
    #     """
    #     Return the an iterator over (key, value) tuples for items older
    #     than the given secondsOld.
    #     """

    @abstractmethod
    def __iter__(self):
        """
        Get the iterator for this storage, should yield tuple of (key, value)
        """
        while False:
            yield None


class PersistentStorage(IStorage):
    """
    This class allows to persist files on disk using mongodb.
    The class acts as an OrderedDict that his keys are the hash of an
    specific file chunk and the value is the (ip, port) of the node that
    has the chunk in his mongodb instance. In the current implementation
    the values of the dict are not used. The get method directly access to
    mongodb and retrieve the data that correspond to the given dict
    """

    def __init__(self, ttl=120):
        """
        By default, max age is a week.
        """
        self.db_path = 'static'
        self.timestamp_path = 'timestamps'
        self.db = []
        self.data = OrderedDict()
        self.ttl = ttl
        self.stop_del_thread = False
        # self.timedelta = ttl

        self.del_thread = threading.Thread(target=self.delete_old)
        self.del_thread.start()

        if not os.path.exists(os.path.join(self.db_path)):
            os.mkdir(self.db_path)

        self.ensure_timestamp_path()
        # if os.path.exists(os.path.join(self.db_path)):
        #     try:
        #         with open(os.path.join(self.db_path, "data_dict.json"), 'rb') as file:
        #             print("loading orderedDict")
        #             self.data = pickle.load(file)
        #         print(self.data)
        #     except:
        #         pass
        # self.address = (ip, port)

    def stop_thread(self):
        self.stop_del_thread = True
        self.del_thread.join()

    def ensure_timestamp_path(self):
        # if not os.path.exists(os.path.join(self.timestamp_path)):
        os.makedirs(self.timestamp_path, exist_ok=True)

    def update_dict(self):
        if not os.path.exists(os.path.join(self.db_path)):
            os.mkdir(self.db_path)

        # with open(os.path.join(self.db_path, "data_dict.json"), 'wb') as f:
        #     pickle.dump(self.data, f)
    def update_timestamp(self, filename: str):
        self.ensure_timestamp_path()
        with open(os.path.join(self.timestamp_path, str(filename)), "w") as f:
            f.write(datetime.now().strftime("%d/%m/%Y, %H:%M:%S"))

    def delete_old(self):

        self.ensure_timestamp_path()
        while True:
            if self.stop_del_thread:
                return
            for path, dir, files in os.walk(self.timestamp_path):
                for file in files:
                    if Path(os.path.join(self.timestamp_path, str(file))).exists():
                        with open(os.path.join(self.timestamp_path, str(file))) as f:
                            sleep(0.1)
                            data = datetime.strptime(
                                f.read(), "%d/%m/%Y, %H:%M:%S")

                        if (datetime.now() - data).seconds > self.ttl:
                            print(
                                f"Removing file {file}, beacuse it has not been accessed in {self.ttl/60} minutes")
                            if Path(os.path.join(self.db_path, str(file))).exists():
                                os.remove(os.path.join(self.db_path, file))
                            os.remove(os.path.join(self.timestamp_path, file))
        sleep(10)

    def get_value(self, key):
        with open(os.path.join(self.db_path, key), "rb") as f:
            result = f.read().decode()
        if result is not None:
            self.update_timestamp(key)
            # result = self.db.find_one(File, File.id == key)
        assert result is not None, 'Tried to get data that is not in db'
        return result

    def set_value(self, key, value):
        self.update_timestamp(str(key))
        self.data[key] = (time.monotonic())
        with open(os.path.join(self.db_path, str(key)), "wb") as f:
            try:
                f.write(value)
            except TypeError:
                f.write(value.encode("unicode_escape"))

    def __setitem__(self, key, value):
        if key in self.data:
            del self.data[key]
            os.remove(os.path.join(self.db_path, str(key)))
            # self.db.remove(File, File.id == key)``

        self.data[key] = (time.monotonic())
        self.update_dict()
        # file_to_save = File(id=key, data=value)
        self.set_value(key, value)
        # self.db.save(file_to_save)
        self.cull()

    def cull(self):
        """
        Check if there exist data older that {self.ttl} and remove it.
        """
        # for _ in self.iter_older_than(self.ttl):
        #     key, _ = self.data.popitem(last=False)
        #     self.db.remove(File, File.id == key)

    def get(self, key, default=None):
        self.cull()
        self.update_timestamp(key)
        path = Path(os.path.join(self.db_path, str(key)))
        if not path.exists():
            return None

        result = self.get_value(key)
        return result

    def contains(self, key):
        self.cull()
        self.update_timestamp(key)
        path = Path(os.path.join(self.db_path, str(key)))
        if not path.exists():
            return False
        return True
    
    
    def __getitem__(self, key):
        self.cull()
        result = self.get_value(key)
        if result is None:
            raise KeyError()
        return result

    def __repr__(self):
        self.cull()
        return repr(self.data)

    # def iter_older_than(self, seconds_old):
        #     # log.warning("iterating")
    #     min_birthday = time.monotonic() - seconds_old
    #     zipped = self._triple_iter()
    #     matches = takewhile(lambda r: min_birthday >= r[1], zipped)
    #     print(matches)
    #     try:
    #         return list(matches)
    #     except TypeError:
    #         return [matches]

    def _triple_iter(self):
        ikeys = os.listdir(os.path.join(self.db_path))
        ibirthday = map(operator.itemgetter(0), self.data.values())
        return zip(ikeys, ibirthday)

    def __iter__(self):
        self.cull()
        print(' ')
        print('calling iter')
        ikeys = os.listdir(os.path.join(self.db_path))
        # ivalues = map(operator.itemgetter(1), self.data.values())
        print('ikeys: ', ikeys)
        ivalues = []

        for ik in ikeys:
            ivalues.append(self.get_value(ik))
        return zip(ikeys, ivalues)
