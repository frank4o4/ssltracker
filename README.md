# ssltracker_django

# ssltracker_django
This project is to make a simple front end for the ssl tracking using Django Frame work



Create a Python3 virtual environment
``` sh
python3 -m venv env
```

Load virtual environment

``` sh
source env/bin/activate
```
install needed packages

``` sh
pip install django gunicorn psycopg2-binary django-bootstrap-v5 django-cronjob
```



## Install SSL

This needs to be done other wise you can't scan internal SSL
``` sh
openssl x509 -inform der -in brm-rootca01.cer -outform pem -out brm-rootca01.pem
```

Copy it to Certs to trust directory
``` sh
cp brm-rootca01.pem /etc/ssl/certs/
```

Update SSL

``` sh
update-ca-certificates --fresh
```



## Configure Nginx and Gunicorn

/etc/nginx/sites-enabled/ssltracker
``` sh
server {
    listen 80;
    server_name 10.125.2.40;


    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root /home/ssltracker/ssltracker;
    }
location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
```

After installation you have to apply data to `ssl_settings` table.

(1) Visit http://<ip address>/admin
(2) Login with account you created, if you didn't create one use `python manage.py createsuperuser`
(3) Click on the `ssl_settings` table and the following fields

```
ssl_ports 443,8080,8443
expiry_date_check=5,15,30
```

 /etc/systemd/system/gunicorn.socket 
``` sh
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target
```



/etc/systemd/system/gunicorn.service 
``` sh
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target


[Service]
User=ssltracker
Group=ssltracker
WorkingDirectory=/home/ssltracker/ssltracker/
ExecStart=/home/ssltracker/ssltracker/env/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          ssltracker.wsgi:application

[Install]
WantedBy=multi-user.target
```

