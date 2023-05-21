FROM nginx:latest
ADD . /app
COPY nginx.conf /etc/nginx/nginx.conf
COPY ssl_ke.pem /etc/nginx/certs/thegagali.pem
COPY ssl_privat_ke.pem /etc/nginx/certs/thegagali-key.pem
EXPOSE 443 80 587 25