# syntax=docker/dockerfile:1

FROM huggingface/transformers-pytorch-cpu

ENV LC_ALL=C.UTF-8

ENV LANG=C.UTF-8

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]