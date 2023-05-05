#!/bin/bash


 git pull
 docker stop $( docker ps -a -q)
 docker rm $( docker ps -a -q)
 docker network create mynetwork
 docker build -t app ./app
 docker build -t nginx ./nginx

 docker run --name app -d -p 8000:8000 -p 27017:27017 -p 27016:27016 -p 27015:27015 --network mynetwork app
 docker run --name nginx --restart always -d -p 80:80 -p 443:443 --network mynetwork nginx

 docker ps