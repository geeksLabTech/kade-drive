from kademlia.network import Server


def test_split_data():
    print('entre')
    mytext = None
    with open('tests/data_to_split.txt', 'rb') as txtfile:
        mytext = txtfile.read()
    assert mytext is not None
    chunks = Server.split_data(mytext, 1)
    assert len(chunks) > 1
    check = b''.join(chunks)
    assert mytext == check
