from queue import Queue
from copy import deepcopy


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class BGPUpdateMessageQueue(Queue, metaclass=Singleton):
    def send_message(self,msg):
        self.put(msg)

    def get_message(self):
        return self.get()


class BGPUpdateMessage():
    def __init__(self,  *, as_path, from_asn, local_perf, as_len, origin_asn, prefix, to_asn = None):
        self.as_path = as_path
        self.as_len = as_len

        self.to_asn = to_asn
        self.from_asn = from_asn
        self.local_perf = local_perf
        self.origin_asn = origin_asn
        self.prefix = prefix

    def is_from_provider(self):
        return self.local_perf == BGPUpdateMessageType.FROM_PROVIDER

    def is_from_peer(self):
        return self.local_perf == BGPUpdateMessageType.FROM_PEER

    def is_from_customer(self):
        return self.local_perf == BGPUpdateMessageType.FROM_CUSTOMER

    def send(self, queue):
        queue.put(deepcopy(self))

class BGPUpdateMessageType():
    FROM_PROVIDER = 10
    FROM_PEER = 20
    FROM_CUSTOMER = 30

