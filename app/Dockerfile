FROM python:3.11-slim
WORKDIR /app
ADD . /app
RUN pip install -r requirements.txt
RUN apt-get update && \
    apt-get install -y supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
EXPOSE 8000 27017 27016 27015
CMD python ./app.py