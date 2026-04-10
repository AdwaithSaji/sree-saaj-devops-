FROM nginx:1.25-alpine
COPY . /usr/share/nginx/html
COPY ../infrastructure/nginx/nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
