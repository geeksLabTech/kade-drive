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
        self.values_path = 'static/values'
        self.metadata_path = 'static/metadata'
        self.keys_path = 'static/keys'
        self.timestamp_path = 'timestamps'
        self.db = []
        # self.data = OrderedDict()
        self.ttl = ttl
        self.stop_del_thread = False
        # self.timedelta = ttl

        self.del_thread = threading.Thread(target=self.delete_old)
        self.del_thread.start()

        self.ensure_dir_paths()

    def stop_thread(self):
        self.stop_del_thread = True
        self.del_thread.join()

    def ensure_dir_paths(self):
        os.makedirs(self.db_path, exist_ok=True)

        os.makedirs(self.values_path, exist_ok=True)

        os.makedirs(self.metadata_path, exist_ok=True)

        os.makedirs(self.keys_path, exist_ok=True)

        os.makedirs(self.timestamp_path, exist_ok=True)

    def update_timestamp(self, filename: str):
        self.ensure_dir_paths()
        # print('timestamp for',filename)
        with open(os.path.join(self.timestamp_path, str(filename)), "w") as f:
            f.write(datetime.now().strftime("%d/%m/%Y, %H:%M:%S"))

    def delete_old(self):
        self.ensure_dir_paths()
        while True:
            print("checking")
            if self.stop_del_thread:
                return
            for path, dir, files in os.walk(self.timestamp_path):
                for file in files:
                    if Path(os.path.join(self.timestamp_path, str(file))).exists():
                        with open(os.path.join(self.timestamp_path, str(file))) as f:
                            data = datetime.strptime(
                                f.read(), "%d/%m/%Y, %H:%M:%S")

                        if (datetime.now() - data).seconds > self.ttl:
                            print(
                                f"Removing file {file}, beacuse it has not been accessed in {self.ttl/60} minutes")
                            if Path(os.path.join(self.values_path, str(file))).exists():
                                os.remove(os.path.join(
                                    self.metadata_path, file))
                            if Path(os.path.join(self.values_path, str(file))).exists():
                                os.remove(os.path.join(
                                    self.metadata_path, file))
                            if Path(os.path.join(self.keys_path, str(file))).exists():
                                os.remove(os.path.join(self.keys_path, file))
                            os.remove(os.path.join(self.timestamp_path, file))
            sleep(self.ttl)

    def get_value(self, key, update_timestamp=True, metadata=True):
        self.ensure_dir_paths()
        if metadata:
            path = os.path.join(self.metadata_path, str(key))
        else:
            path = os.path.join(self.values_path, str(key))
        with open(path, "rb") as f:
            result = f.read()

        if result is not None:
            if update_timestamp:
                self.update_timestamp(key)
            # result = self.db.find_one(File, File.id == key)
        assert result is not None, 'Tried to get data that is not in db'
        return result

    def set_value(self, key, value, metadata=True):
        self.ensure_dir_paths()
        self.update_timestamp(str(key))
        if metadata:
            path = os.path.join(self.metadata_path, str(key))
        else:
            path = os.path.join(self.values_path, str(key))
        with open(path, "wb") as f:
            try:
                print('escribiendo')
                f.write(value)
            except TypeError:
                print('unicode_escape')
                f.write(value.encode("unicode_escape"))

        with open(os.path.join(self.keys_path, str(key)), "wb") as f:
            try:
                f.write(key)
            except TypeError:
                f.write(key.encode("unicode_escape"))

    def set_metadata(self, key, value):
        self.ensure_dir_paths()
        self.set_value(key, value, True)
        self.cull()

    def __setitem__(self, key, value):
        self.ensure_dir_paths()
        # if key in self.data:
        #     del self.data[key]
        #     os.remove(os.path.join(self.values_path, str(key)))
        #     os.remove(os.path.join(self.keys_path, str(key)))
        # self.db.remove(File, File.id == key)``

        # self.data[key] = (time.monotonic())
        # file_to_save = File(id=key, data=value)
        self.set_value(key, value, False)
        # self.db.save(file_to_save)
        self.cull()

    def cull(self):
        """
        Check if there exist data older that {self.ttl} and remove it.
        """
        # for _ in self.iter_older_than(self.ttl):
        #     key, _ = self.data.popitem(last=False)
        #     self.db.remove(File, File.id == key)

    def get(self, key, default=None, update_timestamp=True, metadata=True):
        self.ensure_dir_paths()
        if metadata:
            path = Path(os.path.join(self.metadata_path, str(key)))
        else:
            path = Path(os.path.join(self.values_path, str(key)))
        if not path.exists():
            return None

        result = self.get_value(
            key, update_timestamp=update_timestamp, metadata=metadata)
        return result

    def get_key_in_bytes(self, key: str):
        path = Path(os.path.join(self.keys_path, str(key)))
        if not path.exists():
            return None

        with open(os.path.join(self.keys_path, str(key)), "rb") as f:
            result = f.read()
            return result, os.path.exists(os.path.join(self.metadata_path, str(result)))

    def contains(self, key):
        self.cull()
        # self.update_timestamp(key)
        path = Path(os.path.join(self.values_path, str(key)))
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
        # return repr(self.data)

    def iter_older_than(self, seconds_old):
        # log.warning("iterating")
        self.ensure_dir_paths()
        for path, dir, files in os.walk(self.timestamp_path):
            for file in files:
                if Path(os.path.join(self.timestamp_path, str(file))).exists():
                    with open(os.path.join(self.timestamp_path, str(file))) as f:
                        sleep(0.1)
                        data = datetime.strptime(
                            f.read(), "%d/%m/%Y, %H:%M:%S")

                    if (datetime.now() - data).seconds >= seconds_old:
                        key, is_metadata = self.get_key_in_bytes(str(file))
                        value = self.get(
                            str(file), update_timestamp=False, metadata=is_metadata)
                        assert value is not None
                        yield key, value, is_metadata

    # def _triple_iter(self):
    #     ikeys = os.listdir(os.path.join(self.db_path))
    #     ibirthday = map(operator.itemgetter(0), self.data.values())
    #     return zip(ikeys, ibirthday)

    def __iter__(self):
        self.ensure_dir_paths()
        print(' ')
        print('calling iter')
        ikeys_files = os.listdir(os.path.join(self.keys_path))
        ikeys = []
        imetadata = []
        for key_name in ikeys_files:
            k, m = self.get_key_in_bytes(key_name)
            ikeys.append(k)
            imetadata.append(m)
        # ivalues = map(operator.itemgetter(1), self.data.values())
        print('ikeys: ', ikeys)
        ivalues = []

        for ik in ikeys:
            ivalues.append(self.get_value(ik, update_timestamp=False))
        return zip(ikeys, ivalues, imetadata)
