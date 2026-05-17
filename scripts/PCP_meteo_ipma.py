# -*- coding: utf-8 -*-
"""PCP-meteo-IPMA

#Exemplo de recolha de dados meteorológicos


1. Recolha de dados das condições meteorológicas do Aeroporto Francisco de Sá Carneiro publicadas pelo IPMA

É importante revêr todo o código (incluindo os módulos que podem estar a ser importados mas não sejam usados), e reescrever de acordo com o PEP8 - [https://peps.python.org/pep-0008/][https://peps.python.org/pep-0008/].



PCP, 5/2026
"""


## imports
##

import datetime
import json
import requests
import math
import time
#import couchbase
import socket
import os
from urllib.parse import quote

global enviro

current_env = os.environ.get('CONDA_DEFAULT_ENV')
print ("current_env", current_env)

if current_env is None:
  hostname=socket.gethostname()[:30]
  if hostname[:4]=="srv-":
    enviro="render"
    
  else:
    enviro="colab.google"
    from google.colab import userdata
else:
  enviro="to be defined"
  enviro="flask"

print ("current enviro:", enviro)


#if current_env is None:
#  ! pip install pymysql --quiet
#  ! pip install clts_pcp --quiet
#  ! pip install crate --quiet

import pymysql

import clts_pcp as clts
import crate
print("... done.")

current_env = os.environ.get('CONDA_DEFAULT_ENV')
print ("current_env:", current_env)
print ("enviro:", enviro)

## Context gathering

# clts profiling
tstart=clts.getts()

# Default configuration with alternatives documented
DEFAULT_PARAMS = {
    "verbose": False,           # alternatives: [True, False]
    "destination": "-*-",         # deprecated to use several alternatives: ['localhost', 'baze.cm-maia.pt', 'aiven'] - see below
    "send_mail": True,          # alternatives: [True, False]
    
    "email_addresses": ['ppimenta.umaia@gmail.com' ]  
    #"email_addresses": ["pedroccpimenta@gmail.com", 'ppimenta.umaia@gmail.com', "mluizabaltar@gmail.com" , "rodrigo.mendes.0530@gmail.com", "gustavo.sa.martins@gmail.com"]  # array of email addresses - alternatives: ['ppimenta@umaia.pt', 'ppimenta@cm-maia.pt']
    }

#
# NOTES:
#   - destination is to be deprecated by a list of destinations from this version on (check below)
#
# PCP, November 2025
#

# get hostanme of the machine where the script is running
hostname=socket.gethostname()[:30]

ip = requests.get('https://api.ipify.org').text

print("Server name:", hostname, "Public IP Address:", ip)

destination=DEFAULT_PARAMS['destination']
verbose= DEFAULT_PARAMS['verbose']
send_mail = DEFAULT_PARAMS['send_mail']
email_addresses = DEFAULT_PARAMS['email_addresses']


if '__file__' in globals():    # script running in airflow / Linux
  script_path = os.path.abspath(__file__)
  parts = __file__.replace('\\', "/").split('/')
  datapath=f'./data/ppimenta/{parts[-1]}'
  #enviro = "airflow/linux"

  script = parts[-1]
  channel = parts[-2]
  user = parts[-3]

  user = "PCP"

if False:   #  CHECK FOr AIRFLOW
  if '__file__' in globals():    # script running in airflow / Linux
    script_path = os.path.abspath(__file__)
    parts = __file__.replace('\\', "/").split('/')
    datapath=f'./data/ppimenta/{parts[-1]}'
    #enviro = "airflow/linux"
  else:                          # script running in colab.research.google
    enviro = "jupyter"
    #  !pip install ipynbname --quiet
    import ipynbname
    folder_path = os.getcwd()  # This returns the folder where the notebook is located
    print("folder_path:", folder_path)
    parts=[hostname, "pcp", "meteo data from ICAO" , ipynbname.name()]
    datapath="."
    destination=DEFAULT_PARAMS['destination']
    verbose= DEFAULT_PARAMS['verbose']
    send_mail = DEFAULT_PARAMS['send_mail']
    email_addresses = DEFAULT_PARAMS['email_addresses']


  if enviro=="jupyter":
    clts.elapt[f"running <a href='https://colab.research.google.com/drive/{script.replace("fileId=","")}'>google colab notebook</a>"] = clts.deltat(tstart)
  elif enviro=="render":
    print ("running in ", enviro, ", hostname:", hostname)
    pass
  else:
    # Try to retrieve airflow variable
    try:
        clts.elapt[f"script filename:{script}"] = clts.deltat(tstart)
        clts.elapt[f"var name: {script.replace('.py', '')}"] = clts.deltat(tstart)
        #airflow_conf = json.loads(Variable.get(script.replace('.py', "")))
        #airflow_conf = json.loads(Variable.get("pcp_itecons_v25"))
        airflow_conf = Variable.get(script.replace('.py', ''), default_var={}, deserialize_json=True)
        clts.elapt[f"Params read from variable:{airflow_conf}"] = clts.deltat(tstart)
    except Exception as e:
        airflow_conf = {"status":f"error reading from {script.replace('.py', '')}"}
        clts.elapt[f"Error: {e}"] = clts.deltat(tstart)

    clts.elapt[f"After reading from airflow variable:{airflow_conf}"] = clts.deltat(tstart)

    # Merge with DEFAULT_PARAMS
    if True:
      print (f"Default config: {DEFAULT_PARAMS}")

    clts.elapt[f"Default params:{DEFAULT_PARAMS}"] = clts.deltat(tstart)    # Profiling, August 2025

    config = {**DEFAULT_PARAMS, **airflow_conf}
    print(f"Updated config: {config}")

    #clts.elapt[f"Updated params (1):{airflow_conf1}"] = clts.deltat(tstart)    # Profiling, August 2025
    clts.elapt[f"Updated params:{config}"] = clts.deltat(tstart)    # Profiling, August 2025

    verbose = config['verbose']
    destination = config['destination']
    send_mail = config['send_mail']
    email_addresses = config['email_addresses']

# The overall format of context should be:
# server (ip) | user | channel | file.py | database destination (to be deprecated)
context= f'{hostname} ({ip}) | {user} | {channel} | {script} | * redundant * '

clts.setcontext(context)
now = str(datetime.datetime.now())[0:19]
hoje = now[:10]
if verbose:
  print ("context:", context)
  # clts.listtimes()

# Execution options
datafrom = "restapi"
#datafrom = "file"

if hostname[:4]=="srv-":
    enviro="render"

filepath1 = f"ipma_data_{now.replace(":", "_")}.json"
filepath2 = f"ipma_data.json"

if enviro=="render":    # temporary
  datafrom="restapi"


print (f"Reading data from {datafrom}")

if datafrom=="restapi":  
  ## Getting data from IPMA endpoint
  #

  url ="https://api.ipma.pt/open-data/observation/meteorology/stations/obs-surface.geojson"

  resposta = requests.get(url)
  rtext=resposta.text
  calll=len(resposta.text)

  clts.elapt[f"Data request successful ({calll} chars)!"] = clts.deltat(tstart)    # add an entry to elapt dictionary


  data = json.loads(rtext)

  with open(filepath1, 'w') as fw:
    fw.write(rtext)

  with open(filepath2, 'w') as fw:
    fw.write(rtext)


else:
  print (f"Reading data from {filepath2}")

  data = json.load(open(filepath2))
  clts.elapt[f"Data read from file `{filepath2}`"] = clts.deltat(tstart)


data2=[]
for e in data['features']:
  if e['properties']['idEstacao'] == 1200545:
    print ("FOUND e:", e)
    
    data2.append(e) 

status='ok'
if data2 ==[]:
  clts.elapt["No idEstacao= 1200545 found on data source"]=clts.deltat(tstart)
  status="error"

if status=='ok':
  clts.elapt[f"Found {len(data2)} records on {datafrom} regarding idEstacao=1200545"]=clts.deltat(tstart)

  print (data2)
  print ("--------------------------")
  recs = ""
  recs_c = ""

  # define the fields based on the first element of data2
  keys = ['hostsource'] + [k.lower() for k in data2[0]['properties'].keys()] + ['lon', 'lat']
  for kc in range(len(keys)):
    if keys[kc]=='time':
      keys[kc]='tstamp'

  lkeys =f"({", ".join(keys)})" 

  for kd in range(len(data2)):
      # extract the values from the dictionary
      vc = [hostname] + list(data2[kd]['properties'].values()) +  data2[kd]['geometry']['coordinates']
      
      # prepare the string for sql
      values = ", ".join(
        f"'{v}'" if isinstance(v, str) else str(v)
        for v in vc
      )

      recs = recs + f" ({values}), "

      print ("rec:", recs)

      data2[kd]['properties']['time']=f"timezone('Europe/Lisbon', '{data2[kd]['properties']['time']}'::TIMESTAMP)"
      vc = [hostname] + list(data2[kd]['properties'].values()) +  data2[kd]['geometry']['coordinates']
      values = ", ".join(
        f"'{v}'" if isinstance(v, str) else str(v)
        for v in vc
      )
      recs_c = recs_c + f" ({values}), "


  print ("------------------------------------")
  sql = "insert ignore into ipma_obs " + lkeys +" values "+ recs[:len(recs)-2] +  ";"

  recs_c=recs_c.replace("'timez", 'timez').replace("STAMP)'", "STAMP)")
  sql_c = "insert into ipma_obs " + lkeys +" values "+ recs_c[:len(recs_c)-2] +" on conflict do nothing;"

  print (sql)
  print (sql_c)




  #exit(0)
   

  # The script have to be parametrized by 'User' (so the script could be portable between users)
  #
  print ("\n\n")
  clts.elapt[f"Starting database accesses:"] = clts.deltat(tstart)

  # dblist is defined on a per-script basis
  #
  # deprecated:
  # dblist=json.loads(open(f"{user}-dblist.json")) # each user might use different destination databases
  # This connection needs further parametrization, since the same user might want to use
  # different databases for different pipelines / data sources

  dblist = [ "aiven_acess_mysql", 
              "tidb_ppimenta_umaia", 
              "tidb_Maria", 
              "aiven_projectoMaria_mysql",
              "crate_projectoMaria_crate",
              "crate_pedropimenta",
              "skysql_EstMaria",
              "skysql_IPMAIA",
              "skysql_PPimenta"
  ]


  #dblist = ["aiven_acess_mysql", "crate_pedropimenta" ]

  dblist = ["aiven_acess_mysql", "tidb_ppimenta_umaia", "crate_pedropimenta"  ]

  print(dblist)

  ndb =0
  for db in dblist:
      ndb = ndb+1
      status="nok"

      clts.elapt[f"Connecting to `{db}`"] = clts.deltat(tstart)
      if verbose:
        print ("db in dblist:", db)
        print (f'connecting to `{db}`')
      #if True:
      try:
        if enviro == "google.colab":
          dbcreds=json.loads(userdata.get(f'{user}-{db}.json'))
        elif enviro == "render":
          key_path = f'/etc/secrets/{user}-{db}.json'
          print(f"[{enviro}] About to open:", repr(key_path))
          dbcreds=json.load(open(key_path))
          
        else:
          key_path = f'secrets/{user}-{db}.json'
          print(f"[enviro:{enviro}] About to open:", repr(key_path))
          dbcreds=json.load(open(key_path))
          print("dbcreds:", dbcreds)


        if dbcreds['dbms']=="sql":
          print("... connecting to sql database...")
          timeout = dbcreds['timeout']

          connection = pymysql.connect(
              host=dbcreds["dest_host"],
              port=dbcreds["port"],
              db=dbcreds['database'],
              user=dbcreds['username'],
              password=dbcreds['password'],
              cursorclass=pymysql.cursors.DictCursor,
              charset="utf8mb4",
              connect_timeout=timeout,
              write_timeout=timeout,
              read_timeout=timeout
          )
          cursor = connection.cursor()
          clts.elapt[f"... connected to `{db}`"] = clts.deltat(tstart)
          status="ok"

        elif dbcreds['dbms']=="couchbase":

          # Your Capella connection details
          endpoint = dbcreds['ConnectionString']  # Your Capella endpoint
          username = dbcreds['username']
          password = dbcreds['password']
          bucket_name = dbcreds["bucket"]

          # Create authenticator
          auth = PasswordAuthenticator(dbcreds['username'], dbcreds['password'])

          # Connect to cluster
          cluster = Cluster(dbcreds['ConnectionString'], ClusterOptions(auth))

          # Wait until cluster is ready
          cluster.wait_until_ready(datetime.timedelta(seconds=5))

          # Access bucket and collection
          bucket = cluster.bucket(bucket_name)
          collection = bucket.default_collection()

          clts.elapt[f"... connected to `{db}`"] = clts.deltat(tstart)
          
          status="nok"

        elif dbcreds['dbms']=="sky_sql":
          print("... connecting to sky_sql database...")
          # timeout = dbcreds['timeout'] # NOT COMPATIBLE WITH SKYSQL ? - to verify


          connection = pymysql.connect(
              host=dbcreds["dest_host"],
              port=dbcreds["port"],
              db=dbcreds['database'],
              user=dbcreds['username'],
              password=dbcreds['password'],
              ssl={'verify_cert': True} ,
              connect_timeout=timeout,
              write_timeout=timeout,
              read_timeout=timeout,
              cursorclass=pymysql.cursors.DictCursor

              #cursorclass=pymysql.cursors.DictCursor,
              #charset="utf8mb4",
            
          )
          cursor = connection.cursor()
          clts.elapt[f"... connected to `{db}`"] = clts.deltat(tstart)
          status="ok"
          status="ok"

        elif dbcreds['dbms']=="sql_tls":
          print(f"... connecting to sql_tls database @{enviro}")
          timeout = dbcreds['timeout']
          if enviro =="google.colab":
            pem_content = userdata.get(dbcreds['pem'])

            with open(f'/tmp/{user}.pem', 'w') as f:
              f.write(pem_content)
            connection = pymysql.connect(
              host=dbcreds["dest_host"],
              port=dbcreds["port"],
              db=dbcreds['database'],
              user=dbcreds['username'],
              password=dbcreds['password'],
              cursorclass=pymysql.cursors.DictCursor,
              charset="utf8mb4",
              ssl={'ca': f'/tmp/{user}.pem'},
              connect_timeout=timeout,
              write_timeout=timeout,
              read_timeout=timeout,
              autocommit=True
          )
          elif enviro == "render":
            print ("ENVIRO", enviro)
            pem_path=f'/etc/secrets/{dbcreds['pem']}'
            print("About to use:", repr(pem_path))

            connection = pymysql.connect(
              host=dbcreds["dest_host"],
              port=dbcreds["port"],
              db=dbcreds['database'],
              user=dbcreds['username'],
              password=dbcreds['password'],
              cursorclass=pymysql.cursors.DictCursor,
              charset="utf8mb4",
              ssl={'ca': pem_path},
              connect_timeout=timeout,
              write_timeout=timeout,
              read_timeout=timeout,
              autocommit=True
          )
          else:
            pem_path = f'secrets/{dbcreds['pem']}'
            print("About to use:", repr(pem_path))
            
            connection = pymysql.connect(
              host=dbcreds["dest_host"],
              port=dbcreds["port"],
              db=dbcreds['database'],
              user=dbcreds['username'],
              password=dbcreds['password'],
              cursorclass=pymysql.cursors.DictCursor,
              charset="utf8mb4",
              ssl={'ca': pem_path},
              connect_timeout=timeout,
              write_timeout=timeout,
              read_timeout=timeout,
              autocommit=True
          )



          #cursor=connection.cursor()
          cursor = connection.cursor()
          clts.elapt[f"... connected to `{db}`"] = clts.deltat(tstart)
          status="ok"
        elif dbcreds['dbms']=="crate":
          # import crate
          print("... connecting to crate database...")
          from crate import client
          connection = client.connect(
              dbcreds["dest_host"],
              username=dbcreds['username'],
              password=dbcreds['password'],
              verify_ssl_cert=True
          )


          cursor = connection.cursor()
          clts.elapt[f"... connected to `{db}`"] = clts.deltat(tstart)
          status="ok"
        elif dbcreds['dbms']=="mongobd":
          clts.elapt[f"... mongodb dmbs not ready "] = clts.deltat(tstart)
          status='onerror'
          pass
        else:
          clts.elapt[f"... `{dbcreds['dbms']}` dmbs not ready "] = clts.deltat(tstart)
          status='onerror'
          pass
        status="ok"
      

      except Exception as e:
        print("Error:", e)
        clts.elapt[f"<b><i>{ndb}... error `{e}`</b></i>"] = clts.deltat(tstart)
        status='onerror'
        print ("status", status)
        #exit(1)

      print ("status:", status)
      if status=='ok':

        try:

          if dbcreds['dbms']=="crate":
            cursor.execute(sql_c)
            clts.elapt[f"... writing {len(data2)} records @ {db} "] = clts.deltat(tstart)
            connection.commit()
            clts.elapt[f"... {datetime.datetime.now()} commit "] = clts.deltat(tstart)
  

          elif dbcreds['dbms']=="sql":
            cursor.execute(sql)
            clts.elapt[f"... writing {len(data2)} records @ {db} "] = clts.deltat(tstart)
            connection.commit()
            clts.elapt[f"... {datetime.datetime.now()} commit "] = clts.deltat(tstart)
  
          elif dbcreds['dbms']=="sql_tls":
            cursor.execute(sql)
            clts.elapt[f"... writing {len(data2)} records @ {db} "] = clts.deltat(tstart)
            connection.commit()
            clts.elapt[f"... {datetime.datetime.now()} commit "] = clts.deltat(tstart)
  
          else:
            clts.elapt[f" dbms {dbcreds['dbms']} NOT PROCESSED! "] = clts.deltat(tstart)

          connection.close()

        except Exception as e:

          clts.elapt[f"<b><i>{ndb}... Error `{e}` in `{db}`   "] = clts.deltat(tstart)
          print ("Exception: ", e) 
      else:
        clts.elapt[f"{ndb}. Error in connecting {db} @ `{tstamp}`"] = clts.deltat(tstart)
        pass


# Envia email

clts.elapt["Overall (before email):"]=clts.deltat(tstart)
hora=str(datetime.datetime.now())[11:13]
horaemail= [f"{i:02d}" for i in range(1, 25)]

if enviro=='render':
  horaemail=['07', '11',   '15',   '18', '19', "20", '21', '22' ]

#if sendmail and (hora in horaemail):  
if send_mail and email_addresses!=[] and hora in horaemail :

  print ("Request to send enviro:", enviro)
  #return
  subject = f"🌦️ IPMA {context}"
  toem=clts.listtimes()
  text = toem+"\nEsta é uma mensagem automática."
  html = "<html><body style=''font-family:Montserrat;''>"+toem+ "<hr color=orange>"
  html = html +"This message is an automated notification from "+ context +"</body></html>"

  if enviro == "render":
    import resend
    credsgmail=json.load( open("/etc/secrets/PCP-resend.json" ))
    resend.api_key = credsgmail['api-key']
    for em in email_addresses:
      r = resend.Emails.send({
        "from": credsgmail['from'],
        "to": f"{em} <{em}>",
        "subject": subject,
        "html": html
      })
      print (f"render-email sending to {em}", r)
      time.sleep(3)

  else:

    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import smtplib, ssl

    # V25
    print (" AGAIN enviro:", enviro, "em hostname:", hostname)
    if enviro=="jupyter":
      credsgmail=json.loads(userdata.get('configGMail_PCP.json') )
    else:
      epath=""

      try:
          print("Trying to open " , f'{epath}secrets/configGMail_{hostname}.json')
          with open(f'{epath}secrets/configGMail_{hostname}.json', 'r') as fh:
              credsgmail=json.loads(fh.read())
      except Exception as err:
        print ("Error:", err)

    try:
      
        message = MIMEMultipart("alternative")
        message["Subject"] = subject

        message["From"]=credsgmail['UserFrom']
        message["To"]=", ".join(email_addresses)
        message["Reply-To"]="ppimenta@ipmaia.pt"

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

with open(f"{script.replace(".py", "_run.html")}", "w") as fh:
  fh.write(clts.listtimes())

if enviro!='render':
  now=str(datetime.datetime.now())[:19]
  with open(f"{script.replace(".py", f"_{now.replace(":","_")}_run.html")}", "w") as fh:
    fh.write(clts.listtimes())


print (f"dumping execution time to {script.replace(".py", "_run.json")}")  
with open(f"{script.replace(".py", "_run.json")}", "w") as fh:
  tend=clts.getts()
  fh.write (json.dumps({"tstart":tstart, "tend":tend}))
  print (f"{script.replace(".py", "_run.json")} created." )

