#!/bin/bash


sudo git pull
sudo docker stop $(sudo docker ps -a -q)
sudo docker rm $(sudo docker ps -a -q)
sudo docker network create mynetwork
sudo docker build -t app ./app
sudo docker build -t nginx ./nginx

sudo docker run --name app -d -p 8000:8000 -p 27017:27017 -p 27016:27016 -p 27015:27015 --network mynetwork app
sudo docker run --name nginx --restart always -d -p 80:80 -p 443:443 --network mynetwork nginx

sudo docker ps