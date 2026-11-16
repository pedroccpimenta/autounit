#!/usr/bin/env python
# coding: utf-8

# # PCP - Itecons V0_eosc
# 
# This script:
# 
# 1. **Queries** Itecons database
# 2. **Parses** the result
# 3. **Store** the data in D5Hive d5-comb databases
# 
# **Portability:** the script is designed to run unchanged several jupyter environments and locally in a conda environment.
# 
# For any questions, please contact Pedro Pimenta (ppimenta@ipmaia.pt).
# 
# Nov. 2026

# In[1]:


# imports

import datetime
import decimal
import io
import json
import os
import socket
import statistics
import sys
import time

import zoneinfo

import requests


# In[2]:


## imports depending on the execution environment

import os, sys

env = os.environ
img = env.get("JUPYTER_IMAGE", "")

if "google.colab" in sys.modules:
    enviro = "google colab"
elif "RENDER" in os.environ:
    enviro = "render"
elif "KAGGLE_KERNEL_RUN_TYPE" in env:
    enviro = "kaggle"
elif "DEEPNOTE_PROJECT_ID" in env:
    enviro = "deepnote"
elif "cloudferro" in img:
    enviro = "copernicus dataspace"
elif "eginotebooks" in img:
    enviro = "eosc eu node"
else:
    enviro = env.get("CONDA_DEFAULT_ENV", "unknown")

print ("detected enviro:", enviro)

work_dir = {
    "google colab": "/content",
    "kaggle": "/kaggle/working",
    "deepnote": "/work",
    "eosc eu node": os.path.expanduser("~"),
    "copernicus dataspace": os.path.expanduser("~"),
}.get(enviro, os.getcwd())

print(f"enviro: {enviro} | work_dir: {work_dir}")

if enviro == "google colab":

  import subprocess
  subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "clts_pcp", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "ipynbname", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "crate", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg[binary]", "--quiet"])

  from google.colab import userdata

  import ipynbname

elif enviro == "eosc eu node":
  import subprocess
  subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "clts_pcp", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "ipynbname", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "crate", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg[binary]", "--quiet"])
  import ipynbname

elif enviro == "copernicus dataspace":
  import subprocess
  subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "clts_pcp", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "ipynbname", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "crate", "--quiet"])
  subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg[binary]", "--quiet"])
  import ipynbname


else:
  # in a 'local' conda env, all the necessary modules should already be installed.
  print("LOCAL ENV")
  pass


import clts_pcp as clts
import pymysql
import psycopg

print(f"... done, current env:{enviro}")


# In[3]:


# Context gathering

tstart = clts.getts()

DEFAULT_PARAMS = {
    "verbose": False,           # alternatives: [True, False]
    "destination": "-*-",       # deprecated to use several alternatives: ['localhost', 'baze.cm-maia.pt', 'aiven'] - see below
    "send_mail": True,          # alternatives: [True, False]
    #"email_addresses": [ "pedroccpimenta@gmail.com"  ],  # array of email addresses
    "email_addresses": [ "pedroccpimenta@gmail.com"  ],  # array of email addresses
}

verbose= DEFAULT_PARAMS['verbose']
send_mail = DEFAULT_PARAMS['send_mail']
email_addresses = DEFAULT_PARAMS['email_addresses']

hostname = socket.gethostname()

try:
    ip = requests.get("https://api.ipify.org", timeout=5).text
except:
    ip = "unknown"

print("Server name:", hostname, "Public IP Address:", ip)


 
if enviro == "google colab":
    notebookname = requests.get("http://172.28.0.12:9000/api/sessions", timeout=5).json()[0]["name"]

    print(notebookname)
    user=notebookname.split("-")[0]
    script = ipynbname.name()                      # 'fileId=<id>' on Colab
    script_url = f"https://colab.research.google.com/drive/{script.removeprefix('fileId=')}"
    parts = [hostname, user, notebookname, script]
elif enviro == "eosc eu node":
    import os, json, urllib.request
    from jupyter_server import serverapp

    kernel_id = os.path.basename(get_ipython().kernel.config["IPKernelApp"]["connection_file"]).split("-", 1)[1].split(".")[0]
    notebookname = None
    for s in serverapp.list_running_servers():
        req = urllib.request.Request(s["url"].rstrip("/") + "/api/sessions",
                                     headers={"Authorization": f"token {s.get('token', '')}"})
        for sess in json.load(urllib.request.urlopen(req, timeout=5)):
            if sess["kernel"]["id"] == kernel_id:
                notebookname = os.path.basename(sess["path"])
    print(notebookname)
    import os
    from urllib.parse import quote

    HUB = "https://eu-2.notebooks.open-science-cloud.ec.europa.eu"   # EOSC
    # HUB = "https://jupyterhub.dataspace.copernicus.eu"            # Copernicus

    prefix = os.environ["JUPYTERHUB_SERVICE_PREFIX"]                  # /user/<id>/
    rel = os.environ["JPY_SESSION_NAME"].replace(os.environ["HOME"] + "/", "", 1)
    notebookurl = f"{HUB}{prefix}lab/tree/{quote(rel)}"
    print(notebookurl)


    #notebookname = requests.get("http://172.28.0.12:9000/api/sessions", timeout=5).json()[0]["name"]
    #notebookname = os.path.basename(os.environ["JPY_SESSION_NAME"])   # 'Untitled.ipynb'
    print("notebookname:", notebookname)
    user=notebookname.split("-")[0]
    script = notebookname                      # 'fileId=<id>' on Colab
    script_url = notebookurl
    parts = [hostname, user, notebookname, script]

elif enviro=="copernicus dataspace":

    import os
    from urllib.parse import quote

    hostname = os.environ["HOSTNAME"]                      # jupyter-pedroccpimenta-gmail-com---c769d9d3


    path = os.environ["JPY_SESSION_NAME"]                  # /home/jovyan/Untitled.ipynb
    print("PATH:", path)
    notebookname = os.path.basename(path)                  # Untitled.ipynb
    print("NOTEBOOKNAME:", notebookname)

    script = os.path.splitext(notebookname)[0]             # Untitled
    user = notebookname.split("-")[0]     # só a parte antes do @
    print ("USER:", user)

    rel = os.path.relpath(path, os.environ["HOME"])        # Untitled.ipynb (ou pasta/Untitled.ipynb)
    script_url = ("https://jupyterhub.dataspace.copernicus.eu"
              + os.environ["JUPYTERHUB_SERVICE_PREFIX"]    # /user/<id>/
              + "lab/tree/" + quote(rel))

    parts = [hostname, user, notebookname, script]
    print(notebookname)

else:
    script_path=os.path.abspath(__file__)
    script_name=os.path.basename(script_path)

    enviro = "airflow/linux"
    path = __file__.replace('\\', "/").split('/')
    user = path[-1].split("-")[0]
    script_url=f"{script_name}@{hostname}"
    parts=[hostname, user, path[-2], path[-1]]


channel = parts[-2]
script = parts[-1]
user = parts[-3]

if enviro in ["google colab", "eosc eu node"] :
  clts.elapt[f"running <a href='{script_url}'>{notebookname}</a>"] = clts.deltat(tstart)
else:
  clts.elapt[f"running {script} at {hostname}" ] = clts.deltat(tstart)

now = str(datetime.datetime.now())[0:19]
today = now[:10]

context= f'☁️ | {hostname} | {user} | {channel} | {now} '
print ("context:", context, "enviro:", enviro)
print ("HOSTNAME:", hostname, "user:", user)

clts.setcontext(context)

# Access the source database

if enviro in ["google colab"]:    # 👍 in google colab
  creds = json.loads(userdata.get(f"{user.upper()}-Itecons.json"))

elif enviro == "render":
  creds = json.loads(userdata.get(f"/etc/secrets/{user.upper()}-Itecons.json"))

else:  # both for "egi notebooks" and localhost
  with open(f'./secrets/{user.upper()}-Itecons.json', 'r') as fh:
    creds = json.load(fh)

clts.elapt["Itecons credentials ✅"] = clts.deltat(tstart)


print (json.dumps(creds, sort_keys=False, indent=4))


# In[5]:


conv = pymysql.converters.conversions.copy()
conv[pymysql.constants.FIELD_TYPE.DECIMAL] = float
conv[pymysql.constants.FIELD_TYPE.NEWDECIMAL] = float      # é este que os DECIMAL(x,y) usam

leitura = True
#leitura = False

if leitura==True:
    try:
        connection = pymysql.connect(
            host=creds['host'],
            port=int(creds['port']),
						charset='utf8',
            user=creds['user'],
            password=creds['pwd'],
            cursorclass=pymysql.cursors.DictCursor,
            conv=conv

        )

        cursor = connection.cursor()
        #sql = "SELECT * FROM ForumMaia.Registos WHERE datahora = (SELECT MAX(datahora) FROM ForumMaia.Registos)"
        sql = "SELECT * FROM ForumMaia.Registos WHERE datahora >= NOW() - INTERVAL 2 HOUR  ORDER BY datahora"

        cursor.execute(sql)
        rows = cursor.fetchall()
        text = json.dumps(rows, default=lambda o: o.isoformat(), ensure_ascii=False, indent=2)
        rows=json.loads(text)
        with open("Itecons_log.json", "w", encoding="utf-8") as fh:
            fh.write(text)

        tom =  f"Live Itecons data ({len(rows)}) ✅"
        clts.elapt[tom] = clts.deltat(tstart)
        print (tom)

    except Exception as e:
        tom = "Error while connecting to MySQL: "+e
        clts.elapt[tom] = clts.deltat(tstart)
        print (tom)

    finally:
        if connection.open:
            cursor.close()
            connection.close()

else:
    with open("Itecons_log.json", encoding="utf-8") as fh:
      rows = json.load(fh)
      tom =  f"Reading Itecons data from file ({len(rows)}) ⚠️"
      clts.elapt[tom] = clts.deltat(tstart)
      print (tom)

#print (json.dumps(rows))
print (rows[0])
print (rows[-1])



# In[6]:


# Connection to destination DB


dblist=["prisma_d5comb01" , "crate_pedropimenta", "error-example" ]

LISBON = zoneinfo.ZoneInfo("Europe/Lisbon")
SOURCE, LOCATION = "Itecons", "ForumMaia"      # ajusta

map = {
    "datahora": "tstamp",
    "radiacao": "radiation",
    "pressao_atm": "pressure",
    "pressao_vapor": "vapor_pressure",
    "temperatura": "temperature",
    "temperatura_SH": "sh_temperature",
    "velocidade_vento": "wind_speed",
    "direcao_vento": "wind_direction",
    "gust_vento": "wind_gust",
    "trovoes": "lightning",
    "dist_trovoes": "lightning_distance",
    "precipitacao": "precipitation",
    "humidade": "humidity",
    "orientacaoX": "orientation_x",
    "orientacaoY": "orientation_y",
    "SH1": "soil_moisture_1",
    "SH2": "soil_moisture_2",
}


for db in dblist:
    clts.elapt[f"Connecting to `{db}`"] = clts.deltat(tstart)

    try:
    #if True:
      if enviro == "google colab":
        dbcreds = json.loads(userdata.get(f'{user}-{db}.json'))
      elif enviro == "render":
        with open(f"/etc/secrets/{user}-{db}.json") as f:
          dbcreds = json.load(f)
      else:
        with open(f"./secrets/{user}-{db}.json") as f:
          dbcreds = json.load(f)

      print("\n----------", json.dumps(dbcreds))
      if dbcreds['dest_host']=="baze.cm-maia.pt":
       # tunnel
        if enviro == "jupyter":
           id_rsa_content = userdata.get(f'{user.lower()}-id_rsa')
        elif enviro == "render":
          with open(f"/etc/secrets/{user.lower()}-id_rsa") as ff:
              id_rsa_content = fh.read()

        else:
          try:
            clts.elapt[f"... reading {user}-id_rsa..."] = clts.deltat(tstart)

            with open(f"./secrets/{user}-id_rsa") as fh:
              id_rsa_content = fh.read()
          except Exception as err:
            clts.elapt[f"... 🚧 reading {user}-id_rsa - {str(err) }"] = clts.deltat(tstart)
            clts.elapt[f"... re-trying {user.lower()}-id_rsa..."] = clts.deltat(tstart)

            with open(f"./secrets/{user.lower()}-id_rsa") as fh:
              id_rsa_content = fh.read()
              clts.elapt[f"... reading {user.lower()}-id_rsa ✅"] = clts.deltat(tstart)

        clts.elapt[f"RSA credentials read ✅"] = clts.deltat(tstart)

        # Create and start SSH tunnel
        print("Establishing SSH tunnel...")

        if not hasattr(paramiko, 'DSSKey'):
          paramiko.DSSKey = paramiko.RSAKey  # dummy placeholder, sshtunnel only references it, doesn't need it functional

        print('Connecting to the MariaDB Database at baze ...', end="")

        ssh_tunnel = SSHTunnelForwarder(dbcreds['dest_host'],
            ssh_username=dbcreds['username'],
            ssh_pkey=paramiko.RSAKey.from_private_key(io.StringIO(id_rsa_content)),
            remote_bind_address=("localhost", dbcreds['port'])
          )

        ssh_tunnel.start()
        #print(ssh_tunnel.local_bind_address)
        ssh_port = ssh_tunnel.local_bind_port
        print ("ssh_port (ssh):", ssh_port)
        dbcreds["port"]=ssh_port

        clts.elapt[f"SSH tunnel established (port {ssh_port}) ✅"] = clts.deltat(tstart)

        # connection

      if dbcreds['dbms'] in ["sql", "sql_tls" ]:
        print(" - ... connecting to sql database...", end="")
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

        cursor=connection.cursor()
        clts.elapt[f"connected to `{db}`"] = clts.deltat(tstart)
        status="ok"

      elif dbcreds["dbms"] == "postgres":
        #The format is postgres://USER:PASSWORD@HOST:PORT/DATABASE?options
        DATABASE_URL=f"postgres://{dbcreds['user']}:{dbcreds['pwd']}@{dbcreds['dest_host']}:{dbcreds['port']}/postgres?sslmode=require"

        # 3. Abre a ligação e executa as operações SQL de forma sequencial
        with psycopg.connect(DATABASE_URL) as conn:
            print("✅ Ligado com sucesso ao Prisma Postgres!")

            cols = ["source", "location"] + list(map.values())
            sql = ( f"INSERT INTO doc.weather_station ({', '.join(cols)}) "
                    f"VALUES ({', '.join(['%s'] * len(cols))}) "
                    f"ON CONFLICT (tstamp, location, source) DO NOTHING"
                  )

            #cols = ["source", "location"] + list(map.values())
            #sql = (f"INSERT INTO doc.weather_station ({', '.join(cols)}) VALUES %s "
            #      f"ON CONFLICT (tstamp, location, source) DO NOTHING RETURNING 1")

            dados = [
                [SOURCE, LOCATION, datetime.datetime.fromisoformat(r["datahora"]).replace(tzinfo=LISBON)]
                + [r[k] for k in map if k != "datahora"]
                for r in rows
            ]

            with conn.cursor() as cur:
              cur.executemany(sql, dados)
              inserted = cur.rowcount      # total de linhas realmente inseridas

              tom = f"{dbcreds['dest_host']} Processing {len(rows)} rows ({inserted} new), last at {rows[-1]['datahora']} ✅"
              clts.elapt[tom] = clts.deltat(tstart)
              print(tom)

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

        cols = ["source", "location"] + list(map.values())
        sql = (f"INSERT INTO doc.weather_station ({', '.join(cols)}) "
              f"VALUES ({', '.join('?' * len(cols))}) "
              f"ON CONFLICT (tstamp, location, source) DO NOTHING")

        dados = [
            [SOURCE, LOCATION, datetime.datetime.fromisoformat(r["datahora"]).replace(tzinfo=LISBON)]
            + [r[k] for k in map if k != "datahora"]
            for r in rows
        ]

        n=connection.cursor().executemany(sql, dados)

        tom = f"{dbcreds['dest_host']} Processing {len(rows)} rows ({inserted} new), last at {rows[-1]['datahora']} ✅"
        clts.elapt[tom] = clts.deltat(tstart)
        print(tom)

        #raise SystemExit

      elif dbcreds['dbms']=="mongobd":
        clts.elapt[f"...🚧 mongodb dmbs not ready"] = clts.deltat(tstart)
        status='onerror'
        pass
      elif dbcreds['dbms']=="crate":
        clts.elapt[f"...🚧 mongodb dmbs not ready"] = clts.deltat(tstart)
        status='onerror'
        pass

    except Exception as e:
      print("Error:", e)
      clts.elapt[f"... 🚧 error: `{e}` "] = clts.deltat(tstart)
      status='onerror'




# In[7]:


#
# send email

clts.elapt["Overall (before email):"]=clts.deltat(tstart)
send_mail=False
send_mail=True

if send_mail and email_addresses!=[]:

  print ("Request to send enviro:", enviro)
  #return
  subject = context
  toem=clts.listtimes()
  text = toem+"\nEsta é uma mensagem automática."
  html = "<html><body style=''font-family:Montserrat;''>"+toem+ "<hr color=orange>"
  html = html +f"This message (approx {len(html)+50}) is an automated notification from "+ context +"</body></html>"

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
    from email.mime.image import MIMEImage
    import smtplib, ssl




    # V25
    if enviro=="google colab":
      credsgmail=json.loads(userdata.get('configGMail_PCP.json') )
    else:
      try:
          print("opening", f'./secrets/configGMail_{hostname}.json' )
          with open(f'./secrets/configGMail_{hostname}.json', 'r') as fh:
              credsgmail=json.loads(fh.read())
      except Exception as err:
        print ("Error:", err)

    print  (f"username:{credsgmail['UserName']}")

    try:
        #assunto=context

        message = MIMEMultipart("alternative")
        message["Subject"] = context

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
        print (f"Notificação enviada - {datetime.datetime.now()}.")
        clts.elapt[f"After sending email"] = clts.deltat(tstart)        # add an entry to elapt dictionary
    except Error as e:
        print('A notificação não foi enviada:', e)
        clts.elapt[f"email not sent ({e})"] = clts.deltat(tstart)       # add an entry to elapt dictionary
    finally:
        pass


# In[ ]:





# In[ ]:




