FROM python:3.9.16-alpine
COPY . /pythonbackend
WORKDIR /pythonbackend
RUN pip3 install -r requirements.txt
EXPOSE 80
COPY env_files/dev.env .env
CMD gunicorn --bind 0.0.0.0:80 wsgi:app --timeout 30000 --workers 4