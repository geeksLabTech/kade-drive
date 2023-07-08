import pickle
import pandas as pd
from sklearn.datasets import load_diabetes
from kade_drive.core.network import Server


def test_split_data():
    mytext = None
    with open("tests/data_to_split.txt", "rb") as txtfile:
        mytext = txtfile.read()

    assert mytext is not None
    chunks = Server.split_data(mytext, 1)
    assert len(chunks) > 1
    check = b"".join(chunks)
    assert mytext == check


def test_split_dataframe():
    X, y = load_diabetes(return_X_y=True)

    X = pd.DataFrame(X)
    y = pd.DataFrame(y)

    X_pickle = pickle.dumps(X)

    assert X_pickle is not None
    chunks = Server.split_data(X_pickle, 10000)
    assert len(chunks) > 1
    check = b"".join(chunks)
    assert len(X_pickle) == len(check)
    assert X_pickle == check
