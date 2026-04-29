
# Standard libraries
import datetime
import json
import os
import platform
import shutil
import socket
#import sqlite3
import schedule
import subprocess
import sys
import time
import threading
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False  # Windows doesn't have resource module

# Third-party
#import duckdb
import psutil
import pymysql
import random 
import requests
from flask import Flask, Response, redirect, request, url_for, jsonify
from flask import  send_from_directory
#from flask_apscheduler import APScheduler

#from apscheduler.schedulers.background import BackgroundScheduler
#from apscheduler.triggers.interval import IntervalTrigger
#import atexit


#Local
import clts_pcp as clts

global tt1
global uptime
global hostanme
hostname=socket.gethostname()[:30]

app = Flask(__name__)

#scheduler = BackgroundScheduler(daemon=True, timezone='UTC')

"""
# configs for APScheduler
app.config['SCHEDULER_API_ENABLED'] = False  # Disable API
app.config['SCHEDULER_TIMEZONE'] = 'UTC'

scheduler = APScheduler()
scheduler.init_app(app)
"""

#scheduler.start()

o_tasks="o_tasks.json"
r_tasks="r_tasks.json"
task_status="task_status.json"

mod_time = os.path.getmtime(__file__)
mod_date = datetime.datetime.fromtimestamp(mod_time)

version=mod_date.strftime('%Y-%m-%d')
nk=0

global enviro
enviro = "#NA"

global ostat
ostat = 'ostat.json'
edirect = False

lpret = []
status={}

# Array to hold host status (memory, disk, cpu usage)
global hoststatus
hoststatus = []

global mem_tot
mem = psutil.virtual_memory()
mem_tot = mem.total  

global disk_tot
disk_tot=shutil.disk_usage('/').total # GB

global uname
uname = platform.uname()

global cpu_cores
cpu_cores=os.cpu_count()

global psu_process
psu_process = psutil.Process()
cpu_percent = psu_process.cpu_percent(interval=None) 

global process
process = psutil.Process(os.getpid())

global tenant_mem_used_mb
tenant_mem_used_mb = process.memory_info().rss

@app.route('/history')
def history():
    global hoststatus
    response =  jsonify(hoststatus)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response

global elapsed
elapsed = 0

@app.route('/dataflow')
def dataflow():
    return send_from_directory('dataflow', 'index.html')



@app.route('/status', methods=['POST',"GET"])
def status():
    global r_tasks
    global edirect
    global elapsed
    global status
    global ostat
    global mem_tot
    global disk_tot
    global hostname
    global uname
    global cpu_cores        
    global uptime
    global process
    global psu_process
    global tenant_mem_used_mb
    global cpu_percent




    mem = psutil.virtual_memory()
    disk = shutil.disk_usage('.')
    #process = ps<util.Process(os.getpid())
    

    tenant_mem_used_mb = psu_process.memory_info().rss

    cpu_percent = psu_process.cpu_percent(interval=None) 

    elapsed = (datetime.datetime.now()-uptime).total_seconds()/86400
    
    try:
        result = subprocess.run(
            ["quota", "-s"],
            capture_output=True,
            text=True
        )
    except Exception as e:
        result="no quota -s available on this system."


    toret = { 
        "system": {
            "cpu_cores":cpu_cores,
            "disk_tot":disk_tot,
            "disk_used":disk.used,
            "disk_free":disk.free,
            "hostname":hostname,
            "mem_free":mem.available,
            "mem_pc":mem.percent,
            "mem_tot":mem_tot,
            "mem_used":mem.used,
            "uname":uname,
        },
        "tenant": {
            'CONDA_DEFAULT_ENV': os.environ.get("CONDA_DEFAULT_ENV"),
            'cpu_percent': cpu_percent,
            "elapsed": elapsed,
            "len_history":len(hoststatus),
            "mem": psu_process.memory_info(),
            "mem_used": tenant_mem_used_mb,
            'memory_mb': psu_process.memory_info().rss ,
            'memory_percent': psu_process.memory_percent(),
            "script":__file__,
            "__file__":__file__,
            "uptime":str(uptime)[:19],
            "disk_quota":result
        }

    }

    #toret = json.dumps(toret, ensure_ascii=False)

    return jsonify(toret)



@app.route('/logs')
def logs():
    global process    
  
    my_memory_mb = psu_process.memory_info().rss / (1024**2)
    
    if HAS_RESOURCE:
        # Unix/Linux only
        mem_limit = resource.getrlimit(resource.RLIMIT_AS)
        limit_text = f"Memory limit: {mem_limit}"
        
    else:
        # Windows
        limit_text = "Memory limit: Not available on Windows"

    #
    cdir = ""
    here = Path.cwd()          # current working directory
    #print("CWD:", here)
    cdir = cdir +f"Current dir: {here}"

    for p in sorted(
                    (p for p in here.iterdir() if "creds" not in p.name.lower()),
                    key=lambda p:(p.is_file(), p.name.lower())
        ):
        #print(p)
        cdir = cdir + f"<br> - {p}"
        if str(p).split(".")[-1].lower() == "json"  and str(p)[-8:]=='run.json':
            with open (str(p), 'r') as fh:
                cdir = cdir+ "<table border=1 cellspacing=0><tr><td><pre>" + json.dumps(json.loads(fh.read()), indent=3) +"</pre></table>"
        elif str(p).split(".")[-1].lower() == "html":
            with open (str(p), 'r') as fh:
                cdir = cdir+ "<table border=1 cellspacing=0><tr><td>" + fh.read() +"</table>"
        elif str(p).replace('\\', "/").split("/")[-1] in [
        'requirements.txt',
        'README.md'
        ]:
            with open (str(p), 'r', encoding='utf-8') as fh:
                cdir = cdir+ "<table border=1 cellspacing=0><tr><td>" + fh.read() +"</table>"
        
    
    return f"""
    <html><body style="font-family: monospace;">
    <pre>
    MY process memory: {my_memory_mb:.1f} MB
    {limit_text}
    

    <br>Files in current path:
    {cdir}
    
    </body></html>
    """

@app.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools_discovery():
    return Response(status=204)




@app.route('/zstatus')
def zstatus():
    global hostname
    global ostat
    global mem_tot
    global disk_tot
    try:

        #public_ip = requests.get("https://api.ipify.org", timeout=5).text
        #print(public_ip)
        public_ip = "_to be defined_"

        toret = "<html>"
        
        # Basic system info without
         
        toret += f"<br>hostname:{hostname}"
        toret += f"<br>ip_address:{public_ip}"
        toret += "<br>OS, CPU, version:"+str(platform.uname())  # OS, CPU, version
        toret += f"<br>CPU Cores: {os.cpu_count()}"

        toret += "<br>Disk usage:"+str(shutil.disk_usage('/'))  # Disk usage
        toret += f"<br>Disk usage: {disk_tot/(1024**3):.2f} MB  Used: {shutil.disk_usage('/').used/(1024**3):.2f} MB   Free: {shutil.disk_usage('/').free/(1024**3):.2f} MB " 

    
        
        # Memory info in bytes
        
        mem = psutil.virtual_memory()
        toret += f"<br>Total memory: {mem_tot/(1024**3) :.2f} GB"
        toret += f"<br>Available: {mem.available / (1024**3):.2f} GB  Used: {mem.used / (1024**3):.2f} GB Percent used: {mem.percent}%"
        toret += "<hr color=lime>"

        toret += f"<br>Attempting to read: {ostat}"
        toret += f"<br>File exists: {os.path.exists(ostat)}"
        #toret += "<br>"+json.dumps(json.load(open(ostat)))
        

        toret = toret + "</html>"
    except Exception as e:
        toret =f"<html><body>exception: {str(e)}</html>"
    
    return (toret)

@app.route('/')
def hello():
    global elapsed
    global lpret
    global hoststatus
    global ostat
    global r_tasks
    global tt1

    now = str(datetime.datetime.now())[0:19]
    try:
        tasks = json.load(open(r_tasks))
        ostatus = json.load(open(ostat))
    except Exception as err:
        return("setting up... a minute, please...")

    #print (json.dumps(tasks))
    table = "<table border=1 cellspacing=0 cellpadding=1><tr style='background:silver'><td>task_id<td align=center>status<TD>call / script<td>Period (mins)<td>lastrun<td>ret<td>T watch<td>T proc"

    for ek in tasks.keys():
        if ek=="main cycle" or ek=="main" or ek=="r_peter":
            status[ek]="<b>on"
            tasks[ek]['call']="function"
            tasks[ek]['period']=r_peter_period/60
            tasks[ek]['script']="#na"
            #tasks[ek]['ret']="#na"
            # !!!!!   tasks[ek]['ets']=[0,0]


        table += f"<tr><td align=left>{ek}<td align=center>{status[ek]}<td>{tasks[ek]['call']} /{tasks[ek]['script']} "
        table += f"<td align=right>{tasks[ek]['period']:.2f}"
        table += f"<td align=right>{tasks[ek]['lrun']}"
        #table += f"<td align=right>{'ret'}"

        if 'ret' in  tasks[ek].keys():
            table += f"<td align=right>{tasks[ek]['ret']}"
        else:
            table += f"<td align=right> - no ret (!)"

        if 'ets' in  tasks[ek].keys() and tasks[ek]['ets'][0]!=None:
            table += f"<td align=right>{tasks[ek]['ets'][0]:.3f}"
            table += f"<td align=right>{tasks[ek]['ets'][1]:.3f}"


    table += "</table>"

    table2="<table border=1  cellspacing=0 cellpadding=1><tr style='background:silver'>"
    table2 += f"<tr><td><colspan =2>lpret:{lpret}"
    table2 += "<tr><td>#<td>"
    
    """
    for ep in lpret :

        if type(ep) is  requests.models.Response:
            table2 += f"<tr><td align=right clospan=2>{ep.text}"  
        else:
            if ep.poll() is None:  # Still running
                table2 += f"<tr><td align=right clospan=2>Process {ep.pid} still running."  

            else:  # Completed
                #print(f"Process {ep.pid} finished with return code {ep.returncode}")
                stdout, stderr = ep.communicate()  # Only call once per process
                #print(f"STDOUT: {stdout}")
                #print(f"STDERR: {stderr}")
                table2 += f"<tr><td align=right>{stdout}<td> {stderr}."

                #ztat = ep.communicate()
                #table2 += f"<tr><td align=right clospan=2>{ztat}"
                #table2 += f"<tr><td align=right>{ep.pid}<td align=right>{ep.returncode}"
    """

    table2 += "</table>"

    table3="<table border=1 id=table_history onclick='copyTable(this)' cellspacing=0 cellpadding=1><tr style='background:silver'>"
    table3 += f"<tr><td>CPU usage {psutil.cpu_percent(interval=3)}"
    table3 += f"<tr><td>CPU usage {psutil.cpu_percent(interval=3, percpu=True)}"
    table3 += f"<tr><td><pre>"

    tt2 = datetime.datetime.now() - datetime.timedelta(minutes=8)
    
    """ duckdb
    with duckdb.connect('au_db2.duckdb') as conn:
        #conn.execute('drop table if exists au_status;')

        tt2 = datetime.datetime.now() - datetime.timedelta(minutes=5)
        tt1 = uptime + datetime.timedelta(minutes=5)

        
        # conn.execute('create TABLE if not exists au_status (id INTEGER PRIMARY KEY, tstamp datetime, disk_pc float, mem_pc float, proc_pc float);')

        res = conn.execute(f"select * from au_status where tstamp < '{tt1}'  or tstamp > '{tt2}' order by id; ").fetchall()

    
    table3 += f"<tr><td><pre>"
    table3 += f"   nk     | tstamp          |  disk used % |  mem used % | proc used %  <br>"
    for ar in res:
        for item in ar:
            if isinstance(item, datetime.datetime):
                table3 += f" {item.strftime("%Y-%m-%d %H:%M:%S")} "
            elif isinstance(item, int):
                table3 += f" {item:>8d} "
            else:
                table3 += f" {item:>12.2f}"
        table3 += f"<br>"

    table3 += "</pre></table>"

    """
    hoststatus[:] = [row for row in hoststatus if not (tt1 < row[1] <= tt2)]


    table3 += "                               |                  system                     |          tenant        <br>"
    table3 += "    nk   |         tstamp      | mem used (%) | disk used (%) | cpu used (%) | mem used (MB) | cpu_pc <pre>"
    table3 +="<tr><td><pre>"    

    for ast in hoststatus:
        table3 += f" {ast[0]:7d} | {str(ast[1])[:19]} | {ast[2]:12.2f} | {ast[3]:13.2f} | {ast[4]:12.2f} | {ast[5]:13.2f} | {ast[6]:6.3f} <br>"


    table3 += "</pre>"
    table3 += ( 
        "<TR><TD>"
        " <a href='./status' target=_new>status</a> "
        " <a href='./zstatus' target=_new>zstatus</a> "
        # " <a href='./real-limits' target=_new>./real-limits</a>"
        " <a href='./history' target=_new>history</a>"
        " <a href='./logs' target=_new>logs</a>"
        "</table>"
        )

    resp = f"""<html>
    <head>
    <script>""" + """function copyTable(el) {
  const text = el.innerText;        // ou el.outerHTML se quiseres o HTML
  navigator.clipboard.writeText(text);
}"""+f"""
        setTimeout(function() {{ location.reload(); }}, 30000);
    </script>
    </head>
    <body style='font-family:roboto'>
    <h1>Overall <small>{hostname} {str(uptime)[:19]} ({elapsed:.1f} days)</h1>
    <h2>Tasks</h2>
    {table}
    <form action="/process" method="POST">
        <input type="password" id="apass" name="apass" > 
        <input type="submit" value="Submit">
    </form>
    <h2>History</h2>
    {table3}
    <h2>sub-processes</h2>
    {table2}
    <hr color=lime>
    Version {version}, running at {hostname} ({now}) [{ostatus['nk']}]
    </body>
    </html>
    """

    return resp


## Health check

@app.route('/health')
def health():
    return 'OK', 200

## Process the form and redirect based on input

@app.route('/process', methods=['POST'])
def process():
    global edirect
    global enviro
    global hostname

    user = "PCP"

    user_input =  request.form['apass']

    if hostname[:4]=="srv-":
        enviro="render"

    #print("PROCESS, enviro:", enviro)
    #print ("request.form['apass']:",request.form['apass'])

    if enviro == "render":
        print (" > loading", f"/etc/secrets/{user}-d5bee.json")
        ucreds = json.load(open(f"/etc/secrets/{user}-d5bee.json"))

    else:
        print (" > loading", f"./secrets/{user}-d5bee.json")
        ucreds = json.load(open(f"./secrets/{user}-d5bee.json"))


    #print ("ucreds:", ucreds)
    # Example logic: redirect based on string content
    if ucreds['admin'] == user_input :
        edirect = True
        return redirect(url_for('edittasks'))
    else:
        return redirect(url_for('hello'))


    # Example logic: redirect based on string content
    #if 'admin' in user_input.lower():
    #    edirect = True
    #    return redirect(url_for('edittasks'))
    #else:
    #    return redirect(url_for('hello'))

@app.route('/edittasks', methods=['POST',"GET"])
def edittasks():
    global r_tasks
    global edirect
    global status
    global ostat

    now = str(datetime.datetime.now())[0:19]

    status=json.load(open(task_status))
    #print ("\nEDITTASKS\n Status:", status)
    tasks = json.load(open(r_tasks))
    #print ("\n tasks:", tasks)

    if edirect:
        pass
    else:
        #print ("PARAMETERS on edittasks", request.form)
        xkvalue = request.form.get('xkvalue')
        if xkvalue!='EZ53':
            return redirect(url_for('hello'))
        xchange=False
        for es in status.keys():
            if es=="main cycle":
                pass
            else:
                if es in request.form.keys():
                    xchange=True
                    if request.form.get(es)=="on":
                        status[es]="off"
                    else:
                        status[es]="on"
                if xchange:
                    with open(task_status, "w", encoding="utf-8") as f: json.dump(status, f, ensure_ascii=False, indent=3)
                    r_peter()
  
    table = "<form action='/edittasks' method=POST><table border=1 cellspacing=0 cellpadding=1><tr style='background:silver'><td>task_status<td>task_id<td>pipeline<td>lastrun<td>Period (mins)<td>ret<td>T watch<td>T proc"

    for ek in tasks.keys() :
        #print (" ==========================", ek)
        if ek=="main cycle":
            pass
        else:
            bgcolor = 'lime' if status[ek] == "on" else "orange"

            table += f"<tr><td>{status[ek]}<button name='{ek}' id='s_{ek}' value='{status[ek]}' onclick='submit()' style='background:{bgcolor}' title='click to change status'> {status[ek]} <td>{ek}<td>{tasks[ek]['call']} {tasks[ek]['script']}<td>{tasks[ek]['lrun']}"
            table += f"<td align=right>{tasks[ek]['period']:.0f}"

            if 'ret' in  tasks[ek].keys():
                table += f"<td align=right>{tasks[ek]['ret']}"
            else:
                table += f"<td align=right> - no ret (!)"

            if 'ets' in  tasks[ek].keys() and tasks[ek]['ets'][1]!=None:
                table += f"<td align=right>{tasks[ek]['ets'][1]:.3f}"
                table += f"<td align=right>{tasks[ek]['ets'][0]:.3f}"
            else:
                table += f"<td align=right>None"
                table += f"<td align=right>None"


    table += "</table><input type=password name=xkvalue value='EZ53'><input type='submit' value='Submit'>"


   
    #print (" ========================= Status", status)
    ostatus = json.load(open(ostat))
    #print (" ========================= Overall status", ostatus)

    resp = f"""<!doctype html><link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&display=swap" rel="stylesheet">
    <head>
        <link rel="icon" type="image/x-icon" href="static/pics/autounit.ico">
    <head>
    <script>
       // setTimeout(function() {{ location.reload(); }}, 10000);
        setTimeout(function() {{ location.submit(); }}, 20000);
    </script>
    </head>
    <body style='font-family:roboto'>
    <h1>Editing task status</h1>
    {table}
     <hr color=lime>
    Version {version}, running at {hostname} ({now}) [{ostatus['nk']}]
    </body>
    </html>
    """

    edirect=False
    return resp
     
@app.route('/api', methods=['POST',"GET"])
def api():
    return "ok"

def r_peter():
    global pret
    global lpret
    global hoststatus
    global otsat
    global mem_tot
    global uptime
    global tt1
    global process
    global enviro

    ot = [time.perf_counter(), time.process_time()]

    ostatus = json.load(open(ostat))
    tasks  = json.load(open(r_tasks))
    status = json.load(open(task_status))

    print( "\n\n» Starting r_peter  (", ostatus['nk'],"):", str(datetime.datetime.now())[0:19] )
    
    #if enviro=='flask_autounit_dec25':
    #    print (" SLEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEP")
    #    time.sleep(2)

    print (f"| id {" ":18s} | task status and execution")
    for et in tasks.keys():
        if et == "main" or et == "main cycle" or  et == "r_peter":
            pass
        else:
            print(f"| {et:<21s} | {status[et]:5s}", end="")
            if status[et]=="off":
                print("")
                pass
            else:
                print (" status on: ", end="")
                #print('time check:')
                #print('time check: now', datetime.datetime.now(datetime.UTC))
                #print('time check: then', datetime.datetime.strptime( tasks[et]["lrun"], "%Y-%m-%d %H:%M:%S" ).replace(tzinfo=datetime.UTC))

                difference = datetime.datetime.now(datetime.UTC) - datetime.datetime.strptime( tasks[et]["lrun"], "%Y-%m-%d %H:%M:%S" ).replace(tzinfo=datetime.UTC)
                totsecs=difference.days*24*60*60+difference.seconds    
                totsecs=difference.total_seconds()    

                #print ('time check: ', totsecs, ' totsecs')    
                #print (f"time check: {et:>22s} | {tasks[et]['lrun']:>20s} | {totsecs:.0f} |", end = "")
                #print (f"time check: {totsecs/60} compared to  {tasks[et]['period']}", end = "")

                if totsecs/60 > tasks[et]['period']:
                    print (f"  ============================= calling {et} ..." )

                    bc = [time.perf_counter(), time.process_time()]
                   
                    if tasks[et]['call']=="python":
                        pret = subprocess.Popen([tasks[et]['call'], tasks[et]['script']])
                    elif tasks[et]['call']=="url":
                        pret = requests.get(tasks[et]['script'])
                    else:
                        pret ="`call` not defined."
                    
                    pc = [time.perf_counter(), time.process_time()]

                    tasks[et]["lrun"]=str(datetime.datetime.now())[0:19]
                    #tasks[et]["ret"]=str(pret)
                    tasks[et]["ret"]= ostatus["nk"]
                    #lpret.append(pret)        
                    tasks[et]["ets"]=[pc[0]-bc[0], pc[1]-bc[1]]

                else:
                    print (" (... not yet time:", tasks[et]['period']*60, ")")

    now = str(datetime.datetime.now())[0:19]
    tasks['main cycle']['lrun' ] = now

    dusage = shutil.disk_usage('/')
    disk_pc = dusage.used/dusage.total*100

    cpu_pc = psutil.cpu_percent(interval=2)

    # Memory info in bytes
    mem = psutil.virtual_memory()
    #mem_tot = mem.total / (1024**2)  # Mb 
    #mem_available = mem.available / (1024**2) # Mb
    mem_used = mem.used   # Mb
    mem_pc = mem_used/mem_tot*100

    """
    # conn.execute('create TABLE if not exists au_status (id INTEGER PRIMARY KEY, tstamp datetime, disk_pc float, mem_pc float, proc_pc float);')
    sql = f"insert into au_status (tstamp, mem_pc, disk_pc, proc_pc) values ('{datetime.datetime.now()}',{mem_pc:.2f},{dusage.used/dusage.total*100:.2f},  {cpu_percent:.2f})"
    print ("sql:", sql)
    
    with duckdb.connect('au_db2.duckdb') as conn:
        conn.execute(sql)

    """
    #process= psutil.Process()

    hoststatus.append([ ostatus['nk'], datetime.datetime.now(), mem_pc, disk_pc, cpu_pc, psu_process.memory_info().rss/(1024**2), psu_process.cpu_percent(interval=None) ])

    if ostatus["nk"]==0:
        tt1 = uptime + datetime.timedelta(minutes=8)

    ostatus["nk"] = ostatus["nk"] + 1 
    if ostatus["nk"] > 100000:
        ostatus["nk"] = 0

    # Saving overall status
    with open(ostat, "w") as f:    
        f.write(json.dumps(ostatus, ensure_ascii=False))

    #pc = [time.perf_counter(), time.process_time()]

    ut = [time.perf_counter(), time.process_time()]
    tasks['main cycle']['ets' ] = [ut[0]-ot[0], ut[1]-ot[1]]
    tasks['main cycle']['ret' ] = f"{len(hoststatus)} | [{(ut[0]-ot[0]):.2f} {(ut[1]-ot[1]):.2f}]"
    # Saving tasks last status
    with open(r_tasks, "w") as f:    
        f.write(json.dumps(tasks, ensure_ascii=False))

    print("------------------------------------------------------------")
    print(f"« ending r_peter  ( {ostatus['nk']} ): {now}, len(hoststatus): {len(hoststatus)}", [ut[0]-ot[0], ut[1]-ot[1]])
    print("------------------------------------------------------------\n\n")



####### AUTOUNIT
print ("""\n          AAAAA          UU     UU
         AA  AA          UU     UU                     
        AA   AA          UU     UU
       AAAAAAAA          UU     UU 
      AA     AA          UU     UU
     AA      AAutonomous UUUUUUUUUnit - TO STARTING... wait a minute, pleeeeeeaseeee ...
     """)

## Context variables - FLASK @ Local vs Flask @ render / (...)
now = str(datetime.datetime.now())[0:19]
uptime=datetime.datetime.now()


current_env = os.environ.get('CONDA_DEFAULT_ENV')

print ("current_env", current_env)
enviro = current_env


print ("Path to /etc/secrets and contents")
from pathlib import Path

print(Path("/etc/secrets").exists())
print(list(Path("/etc/secrets").glob("*")))


#print("sqlite version:", sqlite3.sqlite_version)


# Connect/create DB, create table
#conn = sqlite3.connect(':memory:')
#conn = sqlite3.connect('au_db2')
#conn.close()

"""
with duckdb.connect('au_db2.duckdb') as conn:
    conn.execute('drop table if exists au_status;')
    conn.execute ("CREATE or replace SEQUENCE id_seq START 1;")
    conn.execute("create TABLE if not exists au_status (id INTEGER PRIMARY KEY DEFAULT nextval('id_seq'), tstamp datetime, disk_pc float, mem_pc float, proc_pc float);")
"""

## Defining r_peter period

r_peter_period = 35  # seconds

## Defining the file running tasks (r_tasks) based on original tasks (o_tasks)

if os.path.exists(o_tasks):
    tasks = json.load(open(o_tasks))
    print (f"o_tasks ({o_tasks}) loaded.")
    print (f"opening {r_tasks} and saving tasks:")
    #print (json.dumps(tasks, ensure_ascii=False, indent=3))    

    if "main cycle" not in tasks.keys():
        tasks['main cycle'] ={
        "call": "function", 
        "script": "--", 
        "lrun": "2025-12-23 10:20:46", 
        "period": None, 
        "ets": [None, None], 
        "ret": " - not yet called - "
    }

    with open(r_tasks, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(tasks, ensure_ascii=False, indent=3))
    print (f"{r_tasks} created!")
else:
    print (f"`o_tasks` ({o_tasks}) not found.")
    exit(3)


## Defining default status for default tasks

print (f"\n> Saving default task status to `{task_status}`: ")
status = {ek: "off" for ek in tasks}
with open(task_status, "w", encoding="utf-8") as f: 
    json.dump({ek: "off" for ek in tasks}, f, ensure_ascii=False, indent=3)

#print (json.dumps(status, ensure_ascii=False, indent=3))    


print (f"\n> opening `{ostat}` (overall status) and saving hostname and up timestamp...", end ="")
with open(ostat, "w") as f:    
    f.write(json.dumps({"host":hostname, "uptime":str(datetime.datetime.now())[0:19], "nk":0}))


## Calling r_peter()
r_peter()


def test_job():
    print(f"TEST JOB EXECUTED at {datetime.datetime.now()}")

"""
#scheduler.add_job(id='test', func=test_job, trigger='interval', seconds=10)
scheduler.add_job(
    id='test',
    func=test_job,
    trigger=IntervalTrigger(seconds=10),
    replace_existing=True
)

## Scheduling r_peter()
# scheduler.add_job(id='r_peter_job', func=r_peter, trigger='interval', seconds=r_peter_period)

scheduler.add_job(
    id='r_peter_job',
    func=r_peter,
    trigger=IntervalTrigger(seconds=r_peter_period),
    replace_existing=True
)
"""

schedule.every(20).seconds.do(test_job)
schedule.every(40).seconds.do(r_peter)

print(f">>> Scheduled Jobs: {schedule.get_jobs()}")

#print(f">>> Scheduler state: running={scheduler.running}")

# Run scheduler in background thread
def run_scheduler():

    #print(">>> Scheduler thread starting...")
    try:
        while True:
            #print(f">>> Scheduler tick at {datetime.datetime.now()}")
            schedule.run_pending()
            #print(f">>> Scheduler tick complete at {datetime.datetime.now()}")
            time.sleep(random.uniform(5, 8))
            #time.sleep(5)
    except Exception as e:
        print(f"!!! Scheduler thread crashed: {e}")
        import traceback
        traceback.print_exc()

scheduler_thread = None

def start_scheduler():
    global scheduler_thread
    if scheduler_thread is None or not scheduler_thread.is_alive():
        #print(">>> Starting scheduler thread...")
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        #print(">>> Scheduler thread started")

# Start it in a route that gets called early
@app.before_request
def ensure_scheduler():
    start_scheduler()

if __name__ == '__main__':
   port = int(os.environ.get("PORT", 10000))
   app.run(debug=True, use_reloader=False)
   # app.run(debug=False, use_reloader=False)


""" or
if __name__ == "__main__":
    # CRITICAL for Render: host="0.0.0.0", port from $PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)


    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        init_once()
    app.run(debug=True)  # reloader ON
"""