# syntax=docker/dockerfile:1
FROM huggingface/transformers-pytorch-cpu

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV k=20
ENV server_address="mongodb:27017"
ENV TOKENIZERS_PARALLELISM=true 

COPY requirements.txt requirements.txt

RUN apt-get update -y && \
    apt-get install -y enchant && \
    /usr/bin/python3 -m pip install --upgrade pip && \
    pip3 install -r requirements.txt

COPY . .

CMD python3 ./config.py --k $k --server_address $server_address && \
    python3 -m flask run --host=0.0.0.0
