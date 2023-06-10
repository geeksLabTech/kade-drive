
from odmantic import Field, Model

class File(Model):
    id: bytes = Field(primary_field=True)
    data: bytes
