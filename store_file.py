from sklearn.datasets import load_diabetes
import pandas as pd
import pickle
from client import ClientSession

X, y = load_diabetes(return_X_y=True)

X = pd.DataFrame(X)
y = pd.DataFrame(y)

X_pickle = pickle.dumps(X)
y_pickle = pickle.dumps(y)

initial_bootstrap_nodes = []
client_session = ClientSession(initial_bootstrap_nodes)

client_session.ensure_connection(use_broadcast_if_needed=True)


client_session.put("dataset_diabetes",X)


