FROM python:3.9

MAINTAINER "leandro@alternativalinux.net"

RUN mkdir /postfix_saslquota/ -p

WORKDIR /postfix_saslquota

RUN git clone --progress --verbose  https://github.com/noskoski/postfix_saslquota /postfix_saslquota

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
  _quotafile=quotarules.json

RUN mv  /postfix_saslquota/quotarules.json.orig  /postfix_saslquota/quotarules.json

RUN pip install mysql-connector-python

VOLUME ["/postfix_saslquota"]

CMD [ "python", "/postfix_saslquota/saslquota.py" ]
