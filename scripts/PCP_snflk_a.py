
##################################################################################################
#                                                                                                #
# SENSITIVE CREDENTIALS – IMPORTANT                                                              #
# Before updating or pushing this code to GitHub, confirm that all credentials                   #
# and identifiable information are read from secure external files                               #
#                                                                                                #
# PCP, April 2026                                                                                #
#                                                                                                #
##################################################################################################  
   
## Standard modules
import datetime
import json
import re
import socket
#import sys
import time
#from decimal import Decimal
#from urllib.parse import quote

## Third-party packages
import pymysql
import pytz
import requests

import snowflake.connector


#from sshtunnel import SSHTunnelForwarder

import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
#from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key


## Local imports
import clts_pcp as clts

# to sort
#import pandas as pd
import json
import datetime
#import pygsheets

import codecs
#import mysql.connector
#from mysql.connector import Error

import crate

## Local imports
import clts_pcp as clts


"""
Gets data snowflake platform.

PCP, April 2026 

"""

# clts profiling

print (
      "***************************************************************************"
      "*         PCP_snflk_a                                                     *"
      "***************************************************************************"
  )
tstart=clts.getts()


## Context gathering

# get hostanme and ip of the machine where the script is running
hostname=socket.gethostname()
hostname=socket.gethostname()[:30]




ip = requests.get('https://api.ipify.org').text

print("Server name:", hostname, "Public IP Address:", ip)

parts = __file__.replace('\\', "/").split('/')

script = parts[-1]    
if len(parts) > 1:
    channel = parts[-2]
    user = script.split("_")[0]
else:
    channel = 'd5hive:snowflake platform'
    user = "PCP"


if hostname[:4]=="srv-":
  enviro="render"

else:
  enviro="flask"


print(
      f"\n\n\nHOSTNAME - enviro"
      f"{hostname}"
      f"{enviro}"
      )


# Default configuration with alternatives documented  # to be deprecated
DEFAULT_PARAMS = {
    "verbose": True,            # alternatives: [True, False]
    "destination": "baze",      # alternatives: ['localhos',  'aiven']
    "send_mail": True,          # alternatives: [True, False]  
    "email_addresses": ["pedroccpimenta@gmail.com"]             # alternatives: ['ppimenta@umaia.pt', 'ppimenta@cm-maia.pt']
}


# Merge with DEFAULT_PARAMS
if True: 
  print (f"Default config: {DEFAULT_PARAMS}")

#clts.elapt[f"Default params:{DEFAULT_PARAMS}"] = clts.deltat(tstart)    #to be deperacted

config = DEFAULT_PARAMS
print(f"Updated config: {config}")

#clts.elapt[f"Updated params (1):{airflow_conf1}"] = clts.deltat(tstart)     
#clts.elapt[f"Updated params:{config}"] = clts.deltat(tstart)    

verbose = config['verbose']
destination = config['destination']
send_mail = config['send_mail']
email_addresses = config['email_addresses']

if verbose:
    print ("script file_name:", script)
    print ('config:', config)

context= f'{hostname} | {channel} | {script} | * (redundant DBaaS) *'

clts.setcontext(context)
now = str(datetime.datetime.now())[0:19]
today = now[:10]

# Execution options
datafrom = "database"
#datafrom = "file"

if enviro=="render":    # temporary
  datafrom="database"


filepath1 = f"snfk_data_{today}.json"
filepath2 = f"snfk_data.json"

sstatus="ok"

if enviro == "google.colab":
  snflkcreds = json.loads(userdata.get(f"{user}-snflkcreds.json"))
elif enviro == "render":
  print (" > loading", f"/etc/secrets/{user}-snflkcreds.json")
  snflkcreds = json.load(open(f"/etc/secrets/{user}-snflkcreds.json"))
else:
  print (" > loading", f"./secrets/{user}-snflkcreds.json")
  snflkcreds = json.load(open(f"./secrets/{user}-snflkcreds.json"))
                         
if datafrom=="database":  

  try:
  #if True:
    clts.elapt[f"Getting data from snowflake database"] = clts.deltat(tstart)    

    ##################################################################################################
    #                                                                                                #
    # SENSITIVE CREDENTIALS – IMPORTANT                                                              #
    # Before updating or pushing this code to GitHub, confirm that all credentials                   #
    # and identifiable information are read from secure external files                               #
    #                                                                                                #
    # PCP, April 2026                                                                                #
    #                                                                                                #
    ##################################################################################################  
    
    if enviro=="render":
      with open(f"/etc/secrets/{snflkcreds['p8']}", 'rb') as key_file:
        private_key = load_pem_private_key(
              key_file.read(),
              password=snflkcreds['password'].encode('utf-8') 
        )
    
    else:
      #f2o = f"./secrets/{snflkcreds['p8']}"
      #print ("f2o:", f2o)
      with open(f"./secrets/{snflkcreds['p8']}", 'rb') as key_file:
        private_key = load_pem_private_key(
              key_file.read(),
              password=snflkcreds['password'].encode('utf-8') 
        )
    
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
      )

    conn = snowflake.connector.connect(
        user=snflkcreds['user'],                   # from credentials file
        account=snflkcreds['account'],             # from credentials file
        private_key=private_key_bytes,             # computed at run time 
        warehouse=snflkcreds['warehouse'],         # from credentials file 
        database=snflkcreds['database'],           # from credentials file
        schema=snflkcreds['schema'],               # from credentials file
        role=snflkcreds['role']                    # from credentials file
    )


    clts.elapt[f"Connection ok!"] = clts.deltat(tstart)    
    
  #else:
  #  exit(0)
  except Exception as e:
    clts.elapt[f"error {e}"]=clts.deltat(tstart)
    sstatus="error"

  print("sstatus", sstatus)
  
  if sstatus=="ok":
    cursor = conn.cursor()
    
    # read query from file
    if enviro=="render":
      ssqueryf="/etc/secrets/PCP-vs_sql.json"
    else:
      ssqueryf="./secrets/PCP-vs_sql.json"

    psqueryf=json.load(open(ssqueryf))
    sql=psqueryf['sql']
    #print ("sql:", sql)          

    cursor.execute(sql)
    result = cursor.fetchall()
    
    columns = [col[0] for col in cursor.description]

    # Convert rows to list of dictionaries
    result = [dict(zip(columns, row)) for row in result]
    clts.elapt[f"{len(result)} readings extracted from system:snowflake"]= clts.deltat(tstart)
    clts.elapt[f"... connected to `{destination}`"] = clts.deltat(tstart)

    # Writing received data as JSON to file
    if enviro=='render':
      pass
    else:
      with open(f"{filepath1}", 'w', encoding='utf-8') as f:
        f.write(json.dumps(result))
      with open(f"{filepath2}", 'w', encoding='utf-8') as f:
        f.write(json.dumps(result))
        
    conn.close()    

else:
  try:
    if verbose:
      print("Reading from:", os.path.abspath(f"/home/ppimenta/{filepath2}"))
    clts.elapt[f"Getting data from file {filepath2} (testing)"] = clts.deltat(tstart)    # Profiling, August 2025 
    result=json.load(open(f"{filepath2}"))
  except Exception as e:
    clts.elapt[f"Error {e} getting data from file {filepath2} (testing) ❌"] = clts.deltat(tstart)    # Profiling, August 2025 
    sstatus="error"

if sstatus=="ok":
  # connecting to destination DBaaS
  #
  
  #destination_list = [ "aiven_acess"]
  destination_list = ["crate_pedropimenta", "aiven_acess"]


  for destination in destination_list:
    sstatus="ok"

    try:
    #if True:
      clts.elapt[f"Connecting to {destination}..."] = clts.deltat(tstart)   

      if destination =='aiven_acess':
          if enviro=="render":
            fcreds=f'/etc/secrets/{user}-{destination}_mysql.json'
          else:
            fcreds=f'./secrets/{user}-{destination}_mysql.json'
    
      elif destination=="crate_pedropimenta":
        if enviro=="render":
            fcreds=f'/etc/secrets/{user}-{db}.json'
        else:
            fcreds='./secrets/PCP-crate_pedropimenta.json'
          
      else:
          print(f"destination unknown:{destination}.")
          clts.elapt[f"destination {destination} unknown"] = clts.deltat(tstart)    
          sstatus="error"

      creds = json.load(open(fcreds))

      """
      with open(fcreds) as fh:
          creds=json.loads(fh.read())
          dbuser = creds['username']
          dbpwd = creds['password']
      """

      if sstatus=="ok":

        if creds["dbms"]=="sql":
          print(f"username:{creds['username']} acessing to {creds['database']} with password:______")

          timeout=20
          connection = pymysql.connect(
            host = creds['dest_host'],
            port = creds['port'],
            charset = "utf8mb4",
            cursorclass = pymysql.cursors.DictCursor,
            db = creds['database'],
            password = creds['password'],
            user = creds['username'],
            ssl={'verify_cert': True} ,
            connect_timeout = timeout,
            read_timeout = timeout,
            write_timeout = timeout,
          )

        elif creds["dbms"]=="sql_ssl":
          timeout=20
          connection = pymysql.connect(
            host = host,
            port = port,
            charset = "utf8mb4",
            connect_timeout = timeout,
            cursorclass = pymysql.cursors.DictCursor,
            db = creds['database'],
            password = creds['password'],
            user = creds['username'],
            read_timeout = timeout,
            write_timeout = timeout,
            ssl={"ca":f"./secrets/{creds['ssl_cert']}"}
          )
        elif creds["dbms"]=="crate":
          #print("... connecting to crate database...", creds)
          from crate import client
          connection = client.connect(
            creds["dest_host"],
            username=creds['username'],
            password=creds['password'],
            verify_ssl_cert=True
          )
          #cursor = connection.cursor()          

        else:
          print (f"Unknown db (`{destination}`) type:", creds["dbms"])
          clts.elapt[f"Unknown db (`{destination}`) type:", creds["dbms"]] = clts.deltat(tstart)  
          sstatus="error"

        if sstatus=="ok":
          cursor = connection.cursor()
          print (f"===================================== Connection to {destination} successfull ✅ ")
          clts.elapt[f"Connection to {destination} successfull ✅ "] = clts.deltat(tstart)    
      
        else:
          pass

      else:
        clts.elapt[f"{destination} not in cataog"] = clts.deltat(tstart)   
        print (f"Unknown db `{destination}`.")
        sstatus="error"
        pass

    except Exception as e:
      sstatus="error"
      clts.elapt[f"Connection to {destination} in error: {e} ❌"] = clts.deltat(tstart)    # add an entry to elapt dictionary
    #else:
    #  pass

    
    # Data access

    if sstatus=="ok":
      ## Data extraction, parsing and storing
      inserts = 0
      passes = 0

      insaq=0
      passaq=0

      #today = str(datetime.datetime.now())[:10]
      kr = 0

      tabela=snflkcreds["tabela"]

      for c in result:
        dt = datetime.datetime.strptime(c['SAMPLETIME'], "%d/%m/%Y %H:%M:%S")
        sql_datetime = dt.strftime("%Y-%m-%d %H:%M:%S")

        sql = f"select count(*) as nr from {tabela} where SAMPLETIME='{sql_datetime}' and DEVICESERIAL='{c['DEVICESERIAL']}' "   
        if kr < 5:  
          print ("sql:", sql)

        cursor.execute(sql)
        row=cursor.fetchone()

        if creds['dbms']=="crate":
            a={}
            a['nr']= row[0]
            row = a

        if row['nr'] >  1:
          print (f"Duplicate in {tabela} DEVICESERIAL {c['DEVICESERIAL']} at SAMPLETIME = '{sql_datetime}' ! - correct please")
          clts.elapt[f"{destination}:duplicate in {tabela} DEVICESERIAL {c['DEVICESERIAL']} at SAMPLETIME = '{sql_datetime}' for kr={kr}"] = clts.deltat(tstart)
          passes += 1

        elif row['nr'] == 1:
          passes += 1
          pass

        else:
          sql = ( 
              f"insert into {tabela} (hostsource, DEVICESERIAL, tstamp, METERSERIAL,TENANTNAME, SITENAME, SAMPLETIME,READING,CONSUMPTION) values ("
              f"'{hostname}', '{c['DEVICESERIAL']}', '{today}', '{c['METERSERIAL']}', '{c['TENANTNAME']}', '{c['SITENAME']}', '{sql_datetime}', {c['READING']}, {c['CONSUMPTION']})" 
            )
          inserts += 1

          if kr < 5:  
            print ("sql:", sql)

          cursor.execute(sql)
          connection.commit()
    
        kr=kr+1
      clts.elapt[f"{destination}:{inserts} inserts, {passes} passes (total:{inserts+passes}) ✅ "] = clts.deltat(tstart)    # add an entry to elapt dictionary
    

    else:
      clts.elapt[f"Script failed in connecting to destination database `{destination}`."] = clts.deltat(tstart)    # add an entry to elapt dictionary

else:
  # Script arrived to (destination) database connection in error status 
  clts.elapt[f"Script arrived to destination database - connectior in error status."] = clts.deltat(tstart)    # add an entry to elapt dictionary
  pass

# if send_mail and email_addresses and hora in [lista]:           
#    or randomly sends an email p < 0.01 ...
#    or as a function of inserts / passes ...
# ...

clts.elapt["Overall (before email):"]=clts.deltat(tstart)
hora=str(datetime.datetime.now())[11:13]


if enviro=='render':
  horaemail=['07', '11', '15',  "20" ]
  horaemail=range(0,23,1)   ## temporary
else:
  horaemail=range(0,23,1)   ## if running locally, always send emails

if send_mail and email_addresses!=[] and hora in horaemail :   # This script is to be ran every 4 hours, so it only counts with 8 emails / day

  print ("Request to send at enviro:", enviro)

  if enviro == "render":
    toem=clts.listtimes()

    text = toem+"\nEsta é uma mensagem automática."
    subject = f"V💦 {context}"
    html = "<html><body style=''font-family:Montserrat;''>"+toem+ "<hr color=orange>"
    html = html +"This message is an automated notification from "+ context +"</body></html>"

    import resend
    credsgmail=json.load( open("/etc/secrets/PCP-resend.json" ))
    resend.api_key = credsgmail['api-key']
    for em in email_addresses:
      r = resend.Emails.send({
        "from": credsgmail['from'],
        "to": f"{em} <{em}>",
        "subject": f"V💦 {context}",
        "html": html
      })
      print (f"email sending to {em}", r)
      time.sleep(3)


  else:
    toem=clts.listtimes()

    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import smtplib, ssl

    # V25
    print (" enviro:", enviro, "at hostname:", hostname)
    if enviro=="jupyter":
      credsgmail=json.loads(userdata.get('configGMail_PCP.json') )
    else:
      epath=""
      if enviro=="render":
          epath="/etc/"

      try:
          print("Trying to open " , f'{epath}secrets/configGMail_{hostname}.json')
          with open(f'{epath}secrets/configGMail_{hostname}.json', 'r') as fh:
              credsgmail=json.loads(fh.read())
      except Exception as err:
        print ("Error:", err)


    try:
        assunto = f"V💦 {context}"

        message = MIMEMultipart("alternative")
        message["Subject"] = assunto

        message["From"]=credsgmail['UserFrom']
        message["To"]=", ".join(email_addresses)
        message["Reply-To"]="ppimenta@ipmaia.pt"

        text = toem+"\nEsta é uma mensagem automática."

        html = "<html><body style=''font-family:Montserrat;''>"+toem+ "<hr color=orange>"
        html = html +"This message is an automated notification from "+ context +"</body></html>"

        # Turn these into plain/html MIMEText objects
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")

        # Add HTML/plain-text parts to MIMEMultipart message
        # The email client will try to render the last part first
        message.attach(part1)
        message.attach(part2)

        port=465 # SSL

        # Create a secure SSL context
        ssl_context = ssl.create_default_context()

        with smtplib.SMTP_SSL("smtp.gmail.com", port, context=ssl_context) as server:
          server.login(credsgmail['UserName'], credsgmail['UserPwd'])
          sender_email = credsgmail['UserFrom']
          server.sendmail(sender_email,email_addresses, message.as_string())
    except Exception as e:
        print('A notificação não foi enviada:', e)
        clts.elapt[f"email not sent ({e})"] = clts.deltat(tstart)       # add an entry to elapt dictionary
    finally:
        pass

  print ("Notificação enviada.")
  clts.elapt[f"After sending email"] = clts.deltat(tstart)        # add an entry to elapt dictionary
else:
  print(f"Tstamp not included to send emails ({horaemail}).")
  clts.listtimes()


print (f"dumping execution time to {script.replace(".py", "_run.json")}")  
with open(f"{script.replace(".py", "_run.json")}", "w") as fh:
  tend=clts.getts()
  fh.write (json.dumps({"tstart":tstart, "tend":tend}))
  print (f"{script.replace(".py", "_run.json")} created." )

k=clts.listtimes()
with open(f"{script.replace(".py", "_run.html")}", "w") as fh:
  fh.write (k)
  


