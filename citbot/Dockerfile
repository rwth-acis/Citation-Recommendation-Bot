# syntax=docker/dockerfile:1

FROM huggingface/transformers-pytorch-cpu

ENV LC_ALL=C.UTF-8

ENV LANG=C.UTF-8

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

ARG k
ARG server_address

COPY . .

CMD [ "python3", "./config.py" , "--k", k, "server_address", server_address]
CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]