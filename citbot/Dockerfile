# syntax=docker/dockerfile:1
FROM huggingface/transformers-pytorch-cpu

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV k=20
ENV server_address="mongodb:27017"
ENV TOKENIZERS_PARALLELISM=true 


RUN apt-get update -y && \
    apt-get install -y enchant 
# update to python 3.9 and set this as default
RUN apt-get install -y --no-install-recommends software-properties-common 
RUN add-apt-repository -y 'ppa:deadsnakes/ppa' && \
    apt-get update -y 
# https://stackoverflow.com/a/63944890/665159
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get install -y python3.9 python3.9-venv
RUN python3.9 -m venv /venv && \
    PATH=/venv/bin:$PATH
# update pip
RUN curl https://bootstrap.pypa.io/get-pip.py | python3.9
RUN python3.9 -m pip install --upgrade pip && \
    pip3 install --upgrade setuptools

# install python requirements.txt
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

CMD python3 ./config.py --k $k --server_address $server_address && \
    python3 -m flask run --host=0.0.0.0
