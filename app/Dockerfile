FROM python:3-alpine3.17
WORKDIR /app
ADD . /app
RUN pip install -r requirements.txt
RUN apt-get update && \
    apt-get install -y supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
EXPOSE 8000 27017 27016 27015
CMD ["supervisord", "-n"]