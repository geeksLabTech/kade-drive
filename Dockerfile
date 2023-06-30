FROM docker.uclv.cu/python:3.10.10

LABEL Mantainer="JOramas"

WORKDIR /home/app/

COPY kademlia /home/app/kademlia/
COPY message_system /home/app/message_system/
COPY requirements.txt /home/app/
COPY server.py /home/app/
COPY client.py /home/app/
RUN pip install -r requirements.txt

CMD ["python3", "server.py"]
