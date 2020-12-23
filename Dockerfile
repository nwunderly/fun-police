FROM python:3.8

RUN mkdir /funpolice

WORKDIR /funpolice

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

ENTRYPOINT ["python3", "launcher.py"]