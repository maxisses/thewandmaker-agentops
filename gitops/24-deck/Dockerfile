# The deck as a static site. The staged folder "site" is a copy of deck/ with the hosted live
# config (no key in it); gitops/24-deck/install.sh puts it together.
FROM registry.access.redhat.com/ubi9/httpd-24:latest
COPY site/ /var/www/html/
# The config and the page itself are always asked for again; everything else carries ?v=… in its address.
RUN printf '<FilesMatch "(index\\.html|config\\.local\\.js)$">\nHeader set Cache-Control "no-cache"\n</FilesMatch>\n' > /etc/httpd/conf.d/deck.conf
