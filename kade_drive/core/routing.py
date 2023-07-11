import heapq
import time
import logging

from kade_drive.core.protocol import FileSystemProtocol, ServerSession
from itertools import chain
from collections import OrderedDict
from kade_drive.core.utils import shared_prefix, bytes_to_bit_string
from kade_drive.core.node import Node


# Create a file handler
# file_handler = logging.FileHandler("log_file.log")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
# file_handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
# logger.addHandler(file_handler)


class KBucket:
    """
    K is the number of entries in a bucket, their node IDs are expected to be randomly distributed within the ID-range the bucket covers
    Each node is putted in a bucket based on how far away they are from the source node.
    This way when you are looking for some node you don't have to bother all possible nodes
    """

    def __init__(
        self, rangeLower: int, rangeUpper: int, ksize: int, replacementNodeFactor=5
    ):
        self.range = (rangeLower, rangeUpper)
        self.nodes: OrderedDict[bytes, Node] = OrderedDict()
        self.replacement_nodes: OrderedDict[bytes, Node] = OrderedDict()
        self.touch_last_updated()
        self.ksize = ksize
        self.max_replacement_nodes = self.ksize * replacementNodeFactor

    def touch_last_updated(self):
        self.last_updated = time.monotonic()

    def get_nodes(self):
        return list(self.nodes.values())

    def split(self):
        midpoint: int = (self.range[0] + self.range[1]) // 2
        one = KBucket(self.range[0], midpoint, self.ksize)
        two = KBucket(midpoint + 1, self.range[1], self.ksize)
        nodes = chain(self.nodes.values(), self.replacement_nodes.values())
        for node in nodes:
            bucket = one if node.long_id <= midpoint else two
            bucket.add_node(node)

        return (one, two)

    def remove_node(self, node: Node):
        if node.id in self.replacement_nodes:
            del self.replacement_nodes[node.id]

        if node.id in self.nodes:
            del self.nodes[node.id]

            if self.replacement_nodes:
                newnode_id, newnode = self.replacement_nodes.popitem()
                self.nodes[newnode_id] = newnode

    def has_in_range(self, node: Node):
        return self.range[0] <= node.long_id <= self.range[1]

    def is_new_node(self, node: Node):
        return node.id not in self.nodes

    def add_node(self, node):
        """
        Add a C{Node} to the C{KBucket}.  Return True if successful,
        False if the bucket is full.

        If the bucket is full, keep track of node in a replacement list,
        per section 4.1 of the paper.
        """
        if node.id in self.nodes:
            del self.nodes[node.id]
            self.nodes[node.id] = node
        elif len(self) < self.ksize:
            self.nodes[node.id] = node
        else:
            if node.id in self.replacement_nodes:
                del self.replacement_nodes[node.id]
            self.replacement_nodes[node.id] = node
            while len(self.replacement_nodes) > self.max_replacement_nodes:
                self.replacement_nodes.popitem(last=False)
            return False
        return True

    def depth(self):
        vals = self.nodes.values()
        sprefix = shared_prefix([bytes_to_bit_string(n.id) for n in vals])
        return len(sprefix)

    def head(self):
        return list(self.nodes.values())[0]

    def __getitem__(self, node_id):
        return self.nodes.get(node_id, None)

    def __len__(self):
        return len(self.nodes)


class TableTraverser:
    def __init__(self, table: "RoutingTable", startNode):
        index = table.get_bucket_for(startNode)
        logger.debug(f"table.buckets, {table.buckets}, {index}")
        table.buckets[index].touch_last_updated()
        logger.debug("nodes in bucket %s", table.buckets[index].nodes.values())
        self.current_nodes = table.buckets[index].get_nodes()
        logger.debug("current nodes %s", self.current_nodes)
        self.left_buckets = table.buckets[:index]
        self.right_buckets = table.buckets[(index + 1):]
        self.left = True

    def __iter__(self):
        return self

    def __next__(self) -> Node:
        """
        Pop an item from the left subtree, then right, then left, etc.
        """

        logger.debug(self.current_nodes)
        if self.current_nodes and len(self.current_nodes) > 0:
            return self.current_nodes.pop()

        logger.debug(self.__dict__)
        if self.left and self.left_buckets:
            self.current_nodes = self.left_buckets.pop().get_nodes()
            logger.debug(self.current_nodes)
            self.left = False
            return next(self)

        if self.right_buckets:
            self.current_nodes = self.right_buckets.pop(0).get_nodes()
            self.left = True
            logger.debug(self.current_nodes)

            return next(self)
        logger.debug("Not found")
        raise StopIteration


class VoidNodeException(Exception):
    pass


class RoutingTable:
    def __init__(self, ksize: int, node: Node):
        """
        @param node: The node that represents this server.  It won't
        be added to the routing table, but will be needed later to
        determine which buckets to split or not.

        """
        self.node = node
        self.ksize = ksize
        self.flush()

    def flush(self):
        self.buckets = [KBucket(0, 2**160, self.ksize)]

    def split_bucket(self, index: int):
        one, two = self.buckets[index].split()
        self.buckets[index] = one
        self.buckets.insert(index + 1, two)

    def lonely_buckets(self):
        """
        Get all of the buckets that haven't been updated in over
        an hour.
        """
        hrago = time.monotonic() - 20
        return [b for b in self.buckets if b.last_updated < hrago]

    def remove_contact(self, node: Node):
        index = self.get_bucket_for(node)
        self.buckets[index].remove_node(node)

    def is_new_node(self, node: Node):
        index = self.get_bucket_for(node)
        return self.buckets[index].is_new_node(node)

    def add_contact(self, node: Node):
        index = self.get_bucket_for(node)
        bucket = self.buckets[index]

        logger.debug(
            f"previous nodes in bucket of index {index}, {bucket.get_nodes()}")
        # this will succeed unless the bucket is full
        if bucket.add_node(node):
            logger.debug(f"Bucket nodes:  {bucket.get_nodes()}")
            return

        # Per section 4.2 of paper, split if the bucket has the node
        # in its range or if the depth is not congruent to 0 mod 5
        if bucket.has_in_range(self.node) or bucket.depth() % 5 != 0:
            self.split_bucket(index)
            self.add_contact(node)
        else:
            node_to_ask = bucket.head()
            addr = (node_to_ask.ip, node_to_ask.port)
            logger.critical(f"node_to_ask {node_to_ask}, addr {addr}")
            with ServerSession(addr[0], addr[1]) as conn:
                FileSystemProtocol.call_ping(conn, node_to_ask)

    def get_bucket_for(self, node: Node):
        """
        Get the index of the bucket that the given node would fall into.
        """

        node_index: int | None = None
        for index, bucket in enumerate(self.buckets):
            logger.debug(f"node.long_id {node.long_id}")
            logger.debug(f"bucket.range[1] {bucket.range[1]}")
            if node.long_id >= bucket.range[1]:
                continue

            node_index = index
            break
        # we should never be here, but make linter happy
        if node_index is None:
            logger.critical(
                f"VoidNodeException {node} does not have any bucket to fall into"
            )
            raise VoidNodeException(
                f"The node {node} does not have any valid bucket to fall into"
            )

        return node_index

    def find_neighbors(
        self, node: Node, k: int | None = None, exclude: Node | None = None
    ):
        k = k or self.ksize
        nodes: list[tuple[int, Node]] = []
        for neighbor in TableTraverser(self, node):
            if exclude:
                logger.debug(
                    f"Comparing {neighbor.ip} {neighbor.port} and {exclude.ip} {exclude.port}"
                )
            not_excluded = exclude is None or not neighbor.same_home_as(
                exclude)
            logger.debug(f"not excluded {not_excluded}")
            if neighbor.id != node.id and not_excluded:
                heapq.heappush(nodes, (node.distance_to(neighbor), neighbor))
            if len(nodes) == k:
                break

        return [item[1] for item in heapq.nsmallest(k, nodes)]
