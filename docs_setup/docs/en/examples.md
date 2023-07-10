# 1.2 - Examples 

## Store a Value in the server

### Note: Make sure that there exist at least a server in the local network

``` py
from kade_drive.cli import ClientSession

client = ClientSession()
client.connect()
client.put(4, 5)
value = client.get(4)
assert value == 5
```

## Storing a Dataframe
``` py
from sklearn.datasets import load_diabetes
import pandas as pd
import pickle
from client import ClientSession
from time import sleep

X, y = load_diabetes(return_X_y=True)
X = pd.DataFrame(X)
y = pd.DataFrame(y)
X_pickle = pickle.dumps(X)

initial_bootstrap_nodes = []

client_session = ClientSession(initial_bootstrap_nodes)
client_session.connect(use_broadcast_if_needed=True)
client_session.put("dataset_diabetes", X_pickle)

sleep(5)
value_getted = client_session.get("dataset_diabetes")

assert X.equals(value_getted)

```