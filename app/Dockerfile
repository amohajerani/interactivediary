FROM python:3.11-slim
WORKDIR /app
ADD . /app
RUN apt-get update && \
    apt-get install -y supervisor && \
    apt-get install -y gcc
RUN pip install -r requirements.txt
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
EXPOSE 8000 27017 27016 27015
CMD python ./app.py