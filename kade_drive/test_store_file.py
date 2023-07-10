from sklearn.datasets import load_diabetes
import pandas as pd
import pickle
from kade_drive.client import ClientSession
from time import sleep


def test_store_df():
    X, y = load_diabetes(return_X_y=True)

    X = pd.DataFrame(X)
    y = pd.DataFrame(y)

    X_pickle = pickle.dumps(X)

    initial_bootstrap_nodes = []
    client_session = ClientSession(initial_bootstrap_nodes)

    client_session.connect(use_broadcast_if_needed=True)

    client_session.put("dataset_diabetes", X_pickle)

    print("DONE, Getting")
    print()
    print()
    sleep(5)
    value_getted, conn = client_session.get("dataset_diabetes")

    print("value getted ", value_getted)
    print('original value', X)
    assert value_getted is not None
    assert X.equals(value_getted)

