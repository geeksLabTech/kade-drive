FROM docker.uclv.cu/python:3.10.10

LABEL Mantainer="JOramas"

WORKDIR /usr/app/src

COPY kademlia .
COPY models .
COPY requirements.txt .
COPY main.py .
RUN pip install -r requirements.txt

CMD ["python", "./main.py"]
