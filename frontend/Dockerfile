FROM nginx:alpine

# Custom config: serves static files AND reverse-proxies /auth, /movies,
# /watchlist to the backend container. Replaces nginx's default config.
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY index.html /usr/share/nginx/html/index.html
COPY app.js /usr/share/nginx/html/app.js

EXPOSE 80
