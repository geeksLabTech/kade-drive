FROM docker.uclv.cu/python:latest

LABEL Mantainer="JOramas"

WORKDIR /usr/app/src

COPY * ./

CMD ["python", "./run_server.py"]
