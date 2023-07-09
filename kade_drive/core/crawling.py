from collections import Counter
import logging
import rpyc
from kade_drive.core.node import Node, NodeHeap
from kade_drive.core.protocol import FileSystemProtocol, ServerSession


# Create a file handler
# file_handler = logging.FileHandler("log_file.log")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
# file_handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
# logger.addHandler(file_handler)


class SpiderCrawl:
    """
    Crawl the network and look for given 160-bit keys.
    """

    def __init__(self, node: Node, peers, ksize: int, alpha):
        """
        Create a new C{SpiderCrawl}er.

        Args:
            node: A :class:`~kademlia.node.Node` representing the key we're
                  looking for
            peers: A list of :class:`~kademlia.node.Node` instances that
                   provide the entry point for the network
            ksize: The value for k based on the paper
            alpha: The value for alpha based on the paper
        """
        self.ksize = ksize
        self.alpha = alpha
        self.node = node
        self.nearest = NodeHeap(self.node, self.ksize)
        self.last_ids_crawled = []
        ("creating spider with peers: %s", peers)
        self.nearest.push(peers)

    def _find(self, rpcmethod, is_metadata: None | bool):
        """
        Get either a value or list of nodes.

        Args:
            rpcmethod: The protocol's callfindValue or call_find_node.

        The process:
          1. calls find_* to current ALPHA nearest not already queried nodes,
             adding results to current nearest list of k nodes.
          2. current nearest list needs to keep track of who has been queried
             already sort by nearest, keep KSIZE
          3. if list is same as last time, next call should be to everyone not
             yet queried
          4. repeat, unless nearest list has all been queried, then ur done
        """

        logger.debug("crawling network with nearest: %s", str(tuple(self.nearest)))
        # define the alpha based on the latest crawled nodes
        count = self.alpha
        if self.nearest.get_ids() == self.last_ids_crawled:
            count = len(self.nearest)
        # uodate latest crawled nodes
        self.last_ids_crawled = self.nearest.get_ids()

        response_dict = {}
        # for each peer in the alpha not visited nodes
        # perform the rpc protocol method call
        # return the info from those nodes
        for peer in self.nearest.get_uncontacted()[:count]:
            logger.debug("Peer %s %s", type(peer), peer)
            if peer.ip == "192.168.133.1":
                continue
            try:
                session = rpyc.connect(host=peer.ip, port=peer.port)
                conn = session.root
            except ConnectionError as e:
                logger.warning(f"Failed to connect to {peer.id} {peer.ip}, e: {e}")
                session = None
                conn = None

            logger.debug(
                f"Connection is {conn is not None} and self.node is {self.node is not None}"
            )
            logger.debug(f"Calling : {rpcmethod}")
            if is_metadata is None:
                response = rpcmethod(conn, peer, self.node)
            else:
                response = rpcmethod(conn, peer, self.node, is_metadata)
            response_dict[peer.id] = response
            self.nearest.mark_contacted(peer)
            logger.debug("mark contacted successful")
        logger.debug("response %s", response_dict)
        return self._nodes_found(response_dict)

    def _nodes_found(self, response_dict):
        raise NotImplementedError

    def _handle_contacts(self):
        raise NotImplementedError


class ValueSpiderCrawl(SpiderCrawl):
    def __init__(self, node, peers, ksize, alpha):
        SpiderCrawl.__init__(self, node, peers, ksize, alpha)
        # keep track of the single nearest node without value - per
        # section 2.3 so we can set the key there if found
        self.nearest_without_value = NodeHeap(self.node, 1)

    def find(self, is_metadata=True):
        """
        Find either the closest nodes or the value requested.
        """
        return self._find(FileSystemProtocol.call_find_value, is_metadata)

    def _nodes_found(self, response_dict: dict):
        """
        Handle the result of an iteration in _find.
        """
        logger.debug("entry node Found Value Spider")
        toremove = []
        found_values = []
        for peer_id, response in response_dict.items():
            response = RPCFindResponse(response)
            if not response.happened():
                toremove.append(peer_id)
            elif response.has_value():
                found_values.append(response.get_value())
            else:
                peer = self.nearest.get_node(peer_id)
                self.nearest_without_value.push(peer)
                self.nearest.push(response.get_node_list())
        self.nearest.remove(toremove)
        logger.debug(f"found values in _nodes_found {found_values}")
        if len(found_values) > 0:
            return self._handle_found_values(found_values)
        if self.nearest.have_contacted_all():
            # not found!
            return None
        return self.find()

    def _handle_contacts(self):
        # if all nodes were visited but no values were found, return None
        return None

    def _handle_found_values(self, values):
        """
        We got some values!  Exciting.  But let's make sure
        they're all the same or freak out a little bit.  Also,
        make sure we tell the nearest node that *didn't* have
        the value to store it.
        """
        # create a counter for each value found

        value_counts = Counter(values)
        # if more than one value is found for a key raise a warning
        if len(value_counts) != 1:
            logger.debug(
                "Got multiple values for key %i: %s", self.node.long_id, str(values)
            )
        # get the most common item in the network
        # this is, if there were more than one value
        # for the key, choose the most replicated one
        value = value_counts.most_common(1)[0][0]

        # choose the closest node who doesnt had the value
        # and tell it to store the value
        # finally return the value
        peer = self.nearest_without_value.popleft()
        if peer:
            with ServerSession(peer.ip, peer.port) as conn:
                FileSystemProtocol.call_store(conn, peer, self.node.id, value)
        return value


class NodeSpiderCrawl(SpiderCrawl):
    def find(self):
        """
        Find the closest nodes.
        """
        return self._find(FileSystemProtocol.call_find_node, None)

    def _nodes_found(self, response_dict: dict):
        """
        Handle the result of an iteration in _find.
        """

        logger.debug("entering nodes found Node Spider")
        logger.debug(f"response dict is {response_dict}")

        toremove = []
        for peer_id, response in response_dict.items():
            response = RPCFindResponse(response)
            if not response.happened():
                toremove.append(peer_id)
            else:
                self.nearest.push(response.get_node_list())
        self.nearest.remove(toremove)

        if self.nearest.have_contacted_all():
            return list(self.nearest)
        return self.find()

    def _handle_contacts(self):
        # if all nearest nodes are visited, return them
        return list(self.nearest)


class ChunkLocationSpiderCrawl(SpiderCrawl):
    def find(self):
        return self._find(FileSystemProtocol.call_find_chunk_location, None)

    def _nodes_found(self, response_dict: dict):
        """
        Handle the result of an iteration in _find.
        """

        logger.debug("entry ChunkLocationSpiderCrawl")
        toremove = []
        found_values = []
        for peer_id, response in response_dict.items():
            response = RPCFindResponse(response)
            if not response.happened():
                toremove.append(peer_id)
            elif response.has_value():
                found_values.append(response.get_value())
            else:
                self.nearest.push(response.get_node_list())
        self.nearest.remove(toremove)

        if len(found_values) > 0:
            return found_values
        if self.nearest.have_contacted_all():
            # not found!
            return None
        return self.find()


class RPCFindResponse:
    def __init__(self, response):
        """
        A wrapper for the result of a RPC find.

        Args:
            response: This will be a tuple of (<response received>, <value>)
                      where <value> will be a list of tuples if not found or
                      a dictionary of {'value': v} where v is the value desired
        """
        self.response = response

    def happened(self):
        """
        Did the other host actually respond?
        """
        return self.response

    def has_value(self):
        # verify the data in the node is a dict
        return isinstance(self.response, dict)

    def get_value(self):
        # return the 'value' from the dict
        return self.response["value"]

    def get_node_list(self):
        """
        Get the node list in the response.  If there's no value, this should
        be set.
        """
        nodelist = self.response or []
        return [Node(*nodeple) for nodeple in nodelist]
