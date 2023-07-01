import os
import pickle
import time
import operator
from datetime import datetime
from time import sleep
from collections import OrderedDict
from abc import abstractmethod, ABC
from pathlib import Path
import threading
import base64
import logging
logger = logging.getLogger(__name__)

class PersistentStorage:
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

    def update_timestamp(self, filename: str, republish_data=False):
        self.ensure_dir_paths()
        # print('timestamp for',filename)
        data = {"date": datetime.now(), "republish": republish_data}
        

        logger.debug('mira ruta %s %s', os.path.join(self.timestamp_path, str(filename)))
        with open(os.path.join(self.timestamp_path, str(filename)), "wb") as f:
            pickle.dump(data, f)

    def update_republish(self, key: bytes):
        str_key = str(base64.urlsafe_b64encode(key))
        with open(os.path.join(self.timestamp_path, str_key), "rb") as f:
            data = pickle.load(f)
        with open(os.path.join(self.timestamp_path, str_key), "wb") as f:
            data["republish"] = False
            pickle.dump(data, f)

    def delete_old(self):
        self.ensure_dir_paths()
        

        while True:
            logger.debug("checking")
            if self.stop_del_thread:
                return
            for path, dir, files in os.walk(self.timestamp_path):
                for file in files:
                    if Path(os.path.join(self.timestamp_path, str(file))).exists():
                        with open(os.path.join(self.timestamp_path, str(file)), "rb") as f:
                            data = pickle.load(f)

                        if (datetime.now() - data['date']).seconds > self.ttl:
                            logger.info(
                                f"Removing file {file}, beacuse it has not been accessed in {self.ttl/60} minutes")
                            if Path(os.path.join(self.values_path, str(file))).exists():
                                os.remove(os.path.join(
                                    self.values_path, str(file)))
                            if Path(os.path.join(self.metadata_path, str(file))).exists():
                                os.remove(os.path.join(
                                    self.metadata_path, str(file)))
                            if Path(os.path.join(self.keys_path, str(file))).exists():
                                os.remove(os.path.join(
                                    self.keys_path, str(file)))

                            os.remove(os.path.join(
                                self.timestamp_path, str(file)))
            sleep(self.ttl)

    def get_value(self, str_key: str, update_timestamp=True, metadata=True):
        

        self.ensure_dir_paths()
        if metadata:
            path = os.path.join(self.metadata_path, str_key)
        else:
            path = os.path.join(self.values_path, str_key)
        with open(path, "rb") as f:
            result = f.read()

        if result is not None:
            if update_timestamp:
                self.update_timestamp(str_key, republish_data=True)
            # result = self.db.find_one(File, File.id == key)
        if not result: 
            logger.error(f"tried to get non existing data with key {str_key}")
            print('Tried to get data that is not in db')
        return result

    def set_value(self, key: bytes, value, metadata=True, republish_data=False):
        
        str_key = str(base64.urlsafe_b64encode(key))
        self.ensure_dir_paths()
        self.update_timestamp(str_key, republish_data)
        if metadata:
            path = os.path.join(self.metadata_path, str_key)
        else:
            path = os.path.join(self.values_path, str_key)
        with open(path, "wb") as f:
            try:
                logger.debug('writting data  to file')
                f.write(value)
            except TypeError:
                logger.warning('writting with unicode_escape')
                f.write(value.encode("unicode_escape"))

        with open(os.path.join(self.keys_path, str_key), "wb") as f:
            f.write(key)
            # try:
            #     f.write(key)
            # except TypeError:
            #     f.write(key.encode("unicode_escape"))

    def set_metadata(self, key, value, republish_data: bool):
        self.ensure_dir_paths()
        self.set_value(key, value, True, republish_data)
        self.cull()

    def cull(self):
        """
        Check if there exist data older that {self.ttl} and remove it.
        """
        # for _ in self.iter_older_than(self.ttl):
        #     key, _ = self.data.popitem(last=False)
        #     self.db.remove(File, File.id == key)

    def get(self, key: bytes, default=None, update_timestamp=True, metadata=True):
        str_key = str(base64.urlsafe_b64encode(key)) 
        result = self.get_value(
            str_key, update_timestamp=update_timestamp, metadata=metadata)
        return result

    def get_key_in_bytes(self, key: str):
        path = Path(os.path.join(self.keys_path, key))
        if not path.exists():
            return None

        with open(os.path.join(self.keys_path, key), "rb") as f:
            result = f.read()
            return result, os.path.exists(os.path.join(self.metadata_path, key))

    def contains(self, key: bytes):
        str_key = str(base64.urlsafe_b64encode(key)) 
        self.cull()
        # self.update_timestamp(key)
        path = Path(os.path.join(self.values_path, str_key))
        if not path.exists():
            return False

        self.update_timestamp(str_key)
        return True

    def __getitem__(self, key: bytes):
        self.cull()
        str_key = str(base64.urlsafe_b64encode(key)) 
        result = self.get_value(str_key)
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
                if Path(os.path.join(self.timestamp_path, file)).exists():
                    with open(os.path.join(self.timestamp_path, file), "rb") as f:
                        sleep(0.1)
                        data = pickle.load(f)
                    if (datetime.now() - data['date']).seconds >= seconds_old or data['republish']:
                        key, is_metadata = self.get_key_in_bytes(str(file))
                        value = self.get_value(str(file), update_timestamp=False, metadata=is_metadata)
                        assert value is not None
                        yield key, value, is_metadata

    def keys(self):
        ikeys_files = os.listdir(os.path.join(self.keys_path))
        ikeys = []
        imetadata = []
        for key_name in ikeys_files:
            k, m = self.get_key_in_bytes(key_name)
            ikeys.append(k)
            imetadata.append(m)
        return zip(ikeys, imetadata)

    def __iter__(self):
        self.ensure_dir_paths()
        

        logger.debug('calling iter')
        ikeys_files = os.listdir(os.path.join(self.keys_path))
        ikeys: list[bytes] = []
        imetadata: list[bool] = []
        for key_name in ikeys_files:
            k, m = self.get_key_in_bytes(key_name)
            ikeys.append(k)
            imetadata.append(m)
        # ivalues = map(operator.itemgetter(1), self.data.values())
        logger.debug('ikeys: %s', ikeys)
        ivalues: list[bytes] = []

        for i, ik in enumerate(ikeys):
            ivalues.append(self.get(ik, update_timestamp=False, metadata=imetadata[i]))
        return zip(ikeys, ivalues, imetadata)
