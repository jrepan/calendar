## Overview

A web-based calendar application that stored the events in memory. Supports iCal export and import.

This started as an experiment into AI-generated code, but to make it more realistic, I chose a project that I would actually use myself day to day and indeed I do. All features were added by AI, but I needed to adjust the code afterwards.


## Deployment

1. use gunicorn to run the server with only local access: `gunicorn app:app -b 127.0.0.1:8000 -D`

2. To add HTTPS-only external access with password protection, create a nginx config in /etc/nginx/sites-enabled by replace ADDRESS with a relevant value in the following example:

```
server {
    listen 80;
    server_name ADDRESS;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name ADDRESS;

    ssl_certificate /etc/letsencrypt/live/ADDRESS/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ADDRESS/privkey.pem;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    auth_basic           "Login";
    auth_basic_user_file /etc/nginx/htpasswd;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

3. Follow https://docs.nginx.com/nginx/admin-guide/security-controls/configuring-http-basic-authentication/ to generate /etc/nginx/passwd

4. Run `certbot --nginx -d ADDRESS -d www.ADDRESS` to get SSL certificates

5. Reload nginx to apply the config: `sudo systemctl reload nginx`
