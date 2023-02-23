#FROM ubuntu:20.04
FROM python:3.7-buster
#RUN apt-get -y  update 
COPY . /pythonbackend
WORKDIR /pythonbackend
#RUN apt install python3-pip -y
RUN pip3 install -r requirements.txt
RUN pip3 install psycopg2-binary
EXPOSE 80
COPY env_files/dev.env .env
#CMD gunicorn --bind 0.0.0.0:80 wsgi:app --timeout 30000 --workers 2
CMD python3 wsgi.py
