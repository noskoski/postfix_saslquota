#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""saslquota.py: Postfix Daemon that limit sender quota ."""

__author__      = "Leandro Abelin Noskoski"
__site__	    = "www.alternativalinux.net"
__projectpage__ = "https://github.com/noskoski/postfix_saslauth"
__copyright__   = "Copyright 2020, Alternativa Linux"
__license__ 	= "GPL"
__version__ 	= "1.9"
__maintainer__ 	= "Leandro A. Noskoski"
__email__ 	    = "leandro@alternativalinux.net"
__status__ 	    = "Production"

import os,socket,struct,sys,time, logging, re,  mysql.connector, syslog, errno, signal, threading, unicodedata,json
from logging.handlers import SysLogHandler

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

try:
    with open('saslquota.json') as json_data_file:
        _conf = json.load(json_data_file)
except:
    sys.stderr.write("can't open saslquota.json\n")
    quit()

##OVERWRITE with environment variables (Dockerfile)
for k, v in os.environ.items():
    _conf[k] = v

logger = logging.getLogger()
if _conf["_loghandler"] == 'syslog' :
    syslog = SysLogHandler(address=(str(_conf["_logaddress"]),int(_conf["_logport"])),facility=str(_conf["_logfacility"]) )
    formatter = logging.Formatter('postfix/%(module)s[%(process)d]:%(message)s')
    syslog.setFormatter(formatter)
    logger.addHandler(syslog)
else:    
    logger.addHandler(logging.StreamHandler(sys.stdout))    

logger.setLevel(logging.getLevelName(_conf["_loglevel"]))



class Job(threading.Thread):

    def __init__(self,sock,name):
        threading.Thread.__init__(self)
        self.starttime = time.time()
        self.shutdown_flag = threading.Event()
        self.sock = sock
        self.name = name
        self.__sasl_username = None
        self.__recipient = None
        self.__end='\n\n'
        self.__total_data = ""
        self.terminate = 0
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution

## read the stream
    def recv_timeout(self):

        while not self.shutdown_flag.is_set():

            try:
                data=self.sock.recv(1024)
                if data == b'':
                    break
                self.__total_data  = self.__total_data + data.decode("UTF-8","ignore")
                if self.__end in data.decode("UTF-8","ignore") :
                    break
            except UnicodeDecodeError as e:
                logging.error(self.name + " unicode error: %s " % str(e) )
                break

            except KeyboardInterrupt:
                logging.error(self.name + ' CTRL-C HIT')
                break

            except socket.timeout as e:
                logging.debug(self.name + " socket timeout: %s " % str(e) )
                break

            except socket.error as e:
                logging.warning(self.name + " socket error: %s " % str(e) )
                break


        logging.debug(self.name + " end of recv: (" + str(len(self.__total_data)) + ")")

        ##extracts sasl_username value ( or not)

        if (len(str(self.__total_data))>10):
            for item in self.__total_data.split("\n"):
                if 'sasl_username=' in item:
                    self.__sasl_username = item.split('=')[1]
                if 'recipient=' in item:
                    self.__recipient = item.split('=')[1]

    def run(self):

        logging.debug('%s thread started' % self.name)
        self.recv_timeout()
        if self.__sasl_username :

            ## load quota rules
            try:
                with open(_conf["_quotafile"]) as jsonfile:
                    _quota = json.load(jsonfile)
            except:
                logging.warning(self.name + " no quota rule file (" + _conf["_quotafile"] + ")")

            ## quota rule selection
            try:
                if _quota[self.__sasl_username]:   ##By email
                    logging.debug(self.name + " quota rule selected: (" + str(self.__sasl_username) + ")")
                    _rule  = self.__sasl_username
                    _period = _quota[self.__sasl_username]["period"]
                    _msgquota = _quota[self.__sasl_username]["msgquota"]
                    _msg = _quota[self.__sasl_username]["msg"]
            except:
                try:
                    if _quota[self.__sasl_username.split("@")[1]]:  #By domain
                        logging.debug(self.name + " quota rule selected: (" + str(self.__sasl_username.split("@")[1]) + ")")
                        _rule = self.__sasl_username.split("@")[1]
                        _period = _quota[self.__sasl_username.split("@")[1]]["period"]
                        _msgquota = _quota[self.__sasl_username.split("@")[1]]["msgquota"]
                        _msg = _quota[self.__sasl_username.split("@")[1]]["msg"]
                except:
                    try:
                        if _quota["default"]:                          #By default Rule
                            logging.debug(self.name + " quota rule selected: (default)")
                            _rule = "default"
                            _period = _quota["default"]["period"]
                            _msgquota = _quota["default"]["msgquota"]
                            _msg = _quota["default"]["msg"]
                    except:
                        logging.warning(self.name + " No default quota Rule \"default\", forging one, 5000 per day per email")
                        _rule = "forged"
                        _period = 86400
                        _msgquota = 5001
                        _msg = "Sorry you send too much mails, wait and send it later..."

            try:
                _con = mysql.connector.connect(host=_conf["_myhost"], user=_conf["_myuser"], passwd=_conf["_mypasswd"], db=_conf["_mydb"])
                _cursor = _con.cursor()
                _cursor.execute("select count(*) from log where sasl_username =%s  and `date` >= DATE_SUB(now(6), INTERVAL %s SECOND)",(self.__sasl_username,_period,))
                record = _cursor.fetchone()

                _log = self.name + ' sasl_username=' + self.__sasl_username + ", rcpt=" + str(self.__recipient) + ", rule=" + _rule + ", quota=" + str(record[0]+1) + "/" + str(_msgquota)  + "(" +  "{0:.2f}".format( ( record[0] + 1 ) / _msgquota * 100) + "%), period=" + str(_period)
            except:
                logging.warning(self.name + " error reading mysql log ")
            #finally:
            #    _cursor.close()

            ### decision REJECT/ACCEPT
            if int(record[0]) <  int(_msgquota) :
                try :
                    self.sock.sendall(b"action=OK\n\n")
                    logging.info(_log + ", action=ACCEPT ")
                    try:
                        _cursor = _con.cursor()
                        _cursor.execute("insert into log (sasl_username, date ) values (%s,now(6)) ",
                                        (self.__sasl_username,))
                        _con.commit()
                    except:
                        logging.warning(self.name + " error inserting log entry for %s " % str(self.__sasl_username))
                        _con.rollback()
                    finally:
                        _cursor.close()
                except socket.error as e:
                    logging.warning(self.name + " socket error: %s " % str(e))
            else:
                try :
                    self.sock.sendall(b"action=REJECT (" + bytes(_msg, 'utf-8') + b")\n\n")
                    logging.info(_log + ', action=REJECT ' + _msg)
                except socket.error as e:
                    logging.warning(self.name + " socket error: %s " % str(e))




            #except socket.error as e:
            #    logging.error(self.name + " socket error: %s " % str(e) )


        else:
            logging.error(self.name + " no sasl_username in the stream")
            try:
                self.sock.sendall(b"action=REJECT\n\n")
                logging.debug(self.name + ' sending REJECT, :( ')
            except socket.error as e:
                
                logging.warning(self.name + " socket error: %s " % str(e) )

        self.sock.close()
        self.terminate = 1
        logging.debug('%s thread stopped : (%.4f)' % (self.name, time.time() - self.starttime , ) )


class ServiceExit(Exception):
    pass

# the thread
def service_shutdown(signum, frame):
    logging.debug('caught signal %d' % signum)
    raise ServiceExit

def Main():
    #try to connect at the start

    _con = mysql.connector.connect(host=_conf["_myhost"], user=_conf["_myuser"], passwd=_conf["_mypasswd"], db=_conf["_mydb"])
    _con.close()

    socket.setdefaulttimeout(int(_conf["_bindtimeout"]))
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    signal.signal(signal.SIGTERM, service_shutdown)
    signal.signal(signal.SIGINT, service_shutdown)
    logging.debug('default timeout: ' + str(s.gettimeout()))
    i = 1
    aThreads = []
    sockok=0

    while (not sockok):

        try:
            s.bind( ( str(_conf["_bind"]) , int(_conf["_bindport"])) )
            logging.debug('socket binded to port: ' + str(_conf["_bindport"]))
            # put the socket into listening mode
            s.listen(128)
            logging.debug('socket is listening')
            sockok=1

        except socket.timeout as e:
            logging.debug("socket error in startup: %s " % str(e) )
            continue

        except socket.error as e:
            logging.warning("socket error in startup: %s " % str(e) )
            time.sleep(2)
            continue



    # a forever loop until client wants to exit
    while True:
        try:
            c, addr = s.accept()
        except socket.error as e:
            logging.warning("socket error: %s " % str(e) )
            continue
        except ServiceExit:
            logging.warning("serviceExit : " )
            for th in aThreads:
                th.shutdown_flag.set()
                th.sock.close()
                th.join()
        # lock acquired by client
        # Start a new thread and return its identifier
        if c:
            logging.debug('connected to :' + str(addr[0]) + ':' + str(addr[1]))
            process = (Job(c,"[" + str(i) + "]"))
            aThreads.append(process)

        i += 1
        if (i > 99999):
            i = 0

        for th in aThreads:
            if th.terminate:
                aThreads.remove(th)

        logging.debug("thread count: " + str(len(aThreads)) )

    logging.debug('close socket ')


    for process in aThreads:
        process.join()

    try:
        s.close()
    except:
        pass


    self.terminate = 1


if __name__ == '__main__':
    Main()
