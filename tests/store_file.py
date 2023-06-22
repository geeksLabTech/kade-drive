from sklearn.datasets import load_diabetes
import pandas as pd
import pickle

X, y = load_diabetes(return_X_y=True)

X = pd.DataFrame(X)
y = pd.DataFrame(y)

X_pickle = pickle.dumps(X)
y_pickle = pickle.dumps(y)

client_session = ClientSession(initial_bootstrap_nodes)
    