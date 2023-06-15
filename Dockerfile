FROM docker.uclv.cu/python:3.10.10

LABEL Mantainer="JOramas"

WORKDIR /home/app/

COPY kademlia /home/app/kademlia
COPY models /home/app/models
COPY requirements.txt /home/app/
COPY main.py /home/app/
RUN pip install -r requirements.txt

CMD ["python", "./main.py"]
