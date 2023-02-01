FROM python:3.10

MAINTAINER "leandro@alternativalinux.net"

RUN mkdir /postfix_saslquota/ -p && \
        apt-get update && \
        apt-get install -y --no-install-recommends  net-tools ssl-cert && \
        apt dist-upgrade -y && \
        rm -rf /var/lib/apt/lists/*

RUN     rm -f   /etc/localtime && \
        ln -fs /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime 

RUN 	chmod ugo+rx /etc/ssl/* -R
#RUN make-ssl-cert generate-default-snakeoil --force-overwrite 


RUN useradd -ms /bin/bash www && \
        chown www: /postfix_saslquota
        
USER www

WORKDIR /postfix_saslquota

ENV _bind=0.0.0.0 \
  _bindport=10008 \
  _bindtimeout=120 \
  _myhost=mysql \
  _myuser=saslquota \
  _mypasswd=1a2b3c \
  _mydb=saslquota \
  _logfacility=mail \
  _logaddress=localhost \
  _logport=514 \
  _loglevel=INFO \
  _loghandler=stdout \
  _quotafile=quotarules.json

COPY * /postfix_saslquota/

RUN mv  /postfix_saslquota/quotarules.json.orig  /postfix_saslquota/quotarules.json

RUN pip3 install mysql-connector-python


HEALTHCHECK CMD netstat -an | grep ${_bindport} > /dev/null; if [ 0 != $? ]; then exit 1; fi;

#VOLUME ["/postfix_saslquota"]

CMD [ "python", "/postfix_saslquota/saslquota.py" ]
