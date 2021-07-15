FROM python:3.7

MAINTAINER "leandro@alternativalinux.net"

RUN mkdir /postfix_saslquota/ -p

WORKDIR /postfix_saslquota

RUN git clone --progress --verbose  https://github.com/noskoski/postfix_saslquota /postfix_saslquota

#COPY requirements.txt saslquota.py mysql.sql saslquota.json ./

RUN mv quotarules.json.orig quotarules.json

RUN pip install mysql-connector-python

VOLUME ["/postfix_saslquota"]

CMD [ "python", "/postfix_saslquota/saslquota.py" ]
