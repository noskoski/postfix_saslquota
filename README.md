POSTFIX_SASLQUOTA

Objective:

An simple alternative to Policyd ( only quota module for now ), lighter and easy to configure. 


Instalation:

  1 - install needed packages 
  ubuntu/debain:
    apt install supervisor python3
    pip install mysql-connector-python
    
  2 - copy and edit saslquota_supervisor.conf
  
       cp saslquota_supervisor.conf /etc/supervisor/conf.d/ 
       
       edit the content of saslquota_supervisor.conf
  

  3 - edit configuration in saslquota.json  

	{
   	"_bind" : "127.0.0.1",
   	"_bindport" : 10008,
   	"_bindtimeout" :  45,
   	"_myhost" : "localhost",
   	"_myuser" : "saslquota",
   	"_mypasswd" : "*******",
   	"_mydb": "saslquota",
   	"_logfacility": "mail",
   	"_loglevel": "DEBUG",
   	"_quotafile": "quotarules.json"
	}

  3 - setup the quotas quotarules.json:
  
  	{
   	"default" : {
   	  "period": 120,
   	  "msgquota": 500,
   	  "msg": " Ops!!! Você já mandou o limite de 500 emails no intervalo de 120 segundos, tente novamente mais tarde "
   	},
   	"localhost" : {
   	  "period": 1200,
   	  "msgquota": 5000,
   	  "msg": " Ops!!! você já mandou o limite de 5000 emails no intervalo de 1200 segundos, tente novamente mais tarde "
   	},
   	"root@localhost" : {
   	  "period": 300,
   	  "msgquota": 50,
   	  "msg": " Ops!!! você já mandou o limite de 50 emails no intervalo de 300 segundos, tente novamente mais tarde  "
   	}
   	}





  4 - create mysql database and grant access

        create database saslquota; 
        grant all on saslquota.* to saslquota@localhost identified by '*******' ;
        flush privileges;
        
  5 - import database structure
					
				root@:/# mysql -uroot -p  saslquota < mysql.sql
 
  5 - Restart supervisord an verify if is working
		
        - service supervisor restart
        - supervisorctl
          supervisor>  help      :) 
   
  6 - add line to /etc/postfix/main.cf
  
    saslquota = check_policy_service inet:127.0.0.1:10008 #change to the value of _bindport 
  
  7 - modify you /etc/postfix/master.cf ( smtps(465) or/and submission (587) entry, do not use this in smtp(25)  )
	
	submission inet n       -       y       -       -       smtpd 
  	-o syslog_name=postfix/submission
  	-o smtpd_tls_security_level=may
  	-o smtpd_sasl_auth_enable=yes
  	-o smtpd_tls_auth_only=no
  	-o smtpd_reject_unlisted_recipient=no
  	-o smtpd_client_restrictions=$saslquota    <<<<< here
  
  8 - service postfix reload   

  

Test:
 
  1 - verify if the daemon are listening:
        
        netstat -nl |grep 10008 ( use your _bindport value )
        
    
  2 - The test
 
      cat Testfile | netcat 127.0.0.1 10008
      
      response:
      action=OK 
      
      -----
      see the mail/syslog log too:
      
   	Mar 13 10:53:00 mail postfix/saslquota[55354]:[1167] thread started
   	Mar 13 10:53:00 mail postfix/saslquota[55354]:[1167] end of recv: (659)
   	Mar 13 10:53:00 mail postfix/saslquota[55354]:[1167] quota rule selected: (default)
   	Mar 13 10:53:00 mail postfix/saslquota[55354]:thread count: 2
   	Mar 13 10:53:00 mail postfix/saslquota[55354]:[1167] sasl_username=contabilidade2@XXXXXXXX.br, rcpt=gabine@YYYYYYY.br, rule=default, quota 4/1500 (0.27%), period=86400, action=ACCEPT
   	Mar 13 10:53:00 mail postfix/saslquota[55354]:[1167] thread stopped : (0.0784)

  
  3 - Try to send an email with an authenticated user and see the mail log
      
     


 
 
 
 










