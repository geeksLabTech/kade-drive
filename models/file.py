
from odmantic import Field, Model

class File(Model):
    """
    Model to represent a file stored in a mongodb instance, can be a whole file or a chunk

    id field must be a hash of the data
    """
    id: bytes = Field(primary_field=True)
    data: bytes
    # index: int