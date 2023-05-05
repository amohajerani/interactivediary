FROM python:3-alpine3.17
WORKDIR /app
ADD . /app
RUN pip install -r requirements.txt
EXPOSE 8000 27017 27016 27015
CMD python ./app.py