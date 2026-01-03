
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

# Third-party
#import duckdb
import psutil
import pymysql
import requests
from flask import Flask, Response, redirect, request, url_for
#from flask_apscheduler import APScheduler

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit


#Local
import clts_pcp as clts

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
ostat = 'ostat.json'
edirect = False

lpret = []
status={}

# Array to hold host status (memory, disk, cpu usage)
global hoststatus
hoststatus = []


@app.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools_discovery():
    return Response(status=204)

@app.route('/sstatus')
def sstatus():

    public_ip = requests.get("https://api.ipify.org", timeout=5).text
    #print(public_ip)

    toret = "<html>"
    # Basic system info without
    toret += f"<br>hostname:{hostname}"
    toret += f"<br>ip_address:{public_ip}"
    toret += "<br>OS, CPU, version:"+str(platform.uname())  # OS, CPU, version
    toret += "<br>Disk usage:"+str(shutil.disk_usage('/'))  # Disk usage

    toret += "<br>"+f"CPU Cores: {os.cpu_count()}"
    toret += "<br>"+f"Architecture: {platform.machine()}"

    # Memory info in bytes
    mem = psutil.virtual_memory()
    toret += "<br>"+ f"Total memory: {mem.total / (1024**3):.2f} GB"
    toret += "<br>"+ f"Available: {mem.available / (1024**3):.2f} GB"
    toret += "<br>"+ f"Used: {mem.used / (1024**3):.2f} GB"
    toret += "<br>"+ f"Percentusage: {mem.percent}%"
    toret += "<hr color=lime>"

    toret += "<br>"+json.dumps(json.load(open('ostat.json')))

    toret += "</html>"
    return (toret)

@app.route('/')
def hello():
    global lpret
    global hoststatus
    now = str(datetime.datetime.now())[0:19]
    try:
        tasks = json.load(open(r_tasks))
        ostatus = json.load(open(ostat))
    except Exception as err:
        return("setting up... a minute, please...")

    #print (json.dumps(tasks))
    table = "<table border=1 cellspacing=0 cellpadding=1><tr style='background:silver'><td>task_id<td align=center>status<TD>call / script<td>Period (mins)<td>lastrun<td>ret<td>T watch<td>T proc"

    for ek in tasks.keys():
        if ek=="main cycle" or ek=="main":
            status[ek]="<b>on"
            tasks[ek]['call']="function"
            tasks[ek]['period']=r_peter_period/60
            tasks[ek]['script']="#na"

        table += f"<tr><td align=left>{ek}<td align=center>{status[ek]}<td>{tasks[ek]['call']} /{tasks[ek]['script']} "
        table += f"<td align=right>{tasks[ek]['period']:.2f}"
        table += f"<td align=right>{tasks[ek]['lrun']}"
        #table += f"<td align=right>{'ret'}"

        if 'ret' in  tasks[ek].keys():
            table += f"<td align=right>{tasks[ek]['ret']}"
        else:
            table += f"<td align=right> - no ret (!)"

        if 'ets' in  tasks[ek].keys() and tasks[ek]['ets'][0]!=None:
            table += f"<td align=right>{tasks[ek]['ets'][1]:.3f}"
            table += f"<td align=right>{tasks[ek]['ets'][0]:.3f}"


    table += "</table>"

    table2="<table border=1  cellspacing=0 cellpadding=1><tr style='background:silver'>"
    table2 += f"<tr><td><colspan =2>lpret:{lpret}"
    table2 += "<tr><td>#<td>"
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

    table2 += "</table>"

    table3="<table border=1  cellspacing=0 cellpadding=1><tr style='background:silver'>"
    table3 += "<tr><td colspan=2>System status"

    table3 += f"<tr><td>Platform {platform.uname()}"
    table3 += f"<tr><td>Disk usage {shutil.disk_usage('/')}"
    table3 += f"<tr><td># cores {os.cpu_count()}"
    

    table3 += f"<tr><td>CPU usage {psutil.cpu_percent(interval=3)}"
    table3 += f"<tr><td>CPU usage {psutil.cpu_percent(interval=3, percpu=True)}"


    tt2 = datetime.datetime.now() - datetime.timedelta(minutes=5)
    tt1 = uptime + datetime.timedelta(minutes=5)
    
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
    table3 += "<br><pre>|    nk   |         tstamp      | mem used (%) | disk used (%) | cpu used (%) |<br>"

    #hoststatus = [elem for elem in hoststatus if not (tt1 <= elem[1] <= tt2)]

    hoststatus[:] = [row for row in hoststatus if not (tt1 < row[1] < tt2)]


    for ast in hoststatus:
        table3 += f"| {ast[0]:7d} | {str(ast[1])[:19]} | {ast[2]:12.2f} | {ast[3]:13.2f} | {ast[3]:12.2f} |<br>"


    table3 += "</pre>"

    resp = f"""<html>
    <head>
    <script>
        setTimeout(function() {{ location.reload(); }}, 30000);
    </script>
    </head>
    <body style='font-family:roboto'>
    <h1>Overall</h1>
    <h2>Tasks</h2>
    {table}
    <h2>sub-processes</h2>
    {table2}
    <form action="/process" method="POST">
        <input type="password" id="apass" name="apass" > 
        <input type="submit" value="Submit">
    </form>
    <h3>System Status</h3>
    {table3}
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

    user_input =  request.form['apass']

    # Example logic: redirect based on string content
    if 'admin' in user_input.lower():
        edirect = True
        return redirect(url_for('edittasks'))
    else:
        return redirect(url_for('hello'))


@app.route('/edittasks', methods=['POST',"GET"])
def edittasks():
    global r_tasks
    global edirect
    global status

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

    resp = f"""<html>
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
    ostatus = json.load(open(ostat))

    print("\n\n» Starting r_peter  (", ostatus['nk'],"):", str(datetime.datetime.now())[0:19])
    #print("time is:", time, "type:", type(time))
    ot = [time.perf_counter(), time.process_time()]
    
    tasks  = json.load(open(r_tasks))
    status = json.load(open(task_status))
    #print (" r_peter - tasks:" , tasks)
    #print (" r_peter - status:" , status)

    print (f"| id {" ":19s} | task status and execution")
    for et in tasks.keys():
        if et == "main" or et == "main cycle":
            pass
        else:
            print(f"| {et:<21s} | {status[et]:5s}", end="")
            if status[et]=="off":
                print("")
                pass
            else:
                print (" status on: ", end="")

                difference = datetime.datetime.now(datetime.UTC) - datetime.datetime.strptime( tasks[et]["lrun"], "%Y-%m-%d %H:%M:%S" ).replace(tzinfo=datetime.UTC)

                print (f" {et:>22s} | {tasks[et]['lrun']:>20s} | {difference.seconds:>5d} |", end = "")
                if difference.seconds/60 > tasks[et]['period']:
                    print (f" calling {et} ..." )

                    bc = [time.perf_counter(), time.process_time()]
                   
                    if tasks[et]['call']=="python":
                        pret = subprocess.Popen([tasks[et]['call'], tasks[et]['script']])
                    elif tasks[et]['call']=="url":
                        pret = requests.get(tasks[et]['script'])
                    else:
                        pret ="`call` not defined."
                    
                    pc = [time.perf_counter(), time.process_time()]

                    tasks[et]["lrun"]=str(datetime.datetime.now())[0:19]
                    tasks[et]["ets"]=[pc[0]-bc[0], pc[1]-bc[1]]
                    tasks[et]["ret"]=str(pret)
                    lpret.append(pret)        

                else:
                    print (" (... not yet time:", tasks[et]['period']*60, ")")

    now = str(datetime.datetime.now())[0:19]

    ut = [time.perf_counter(), time.process_time()]
    tasks['main cycle']['lrun' ] = now
    tasks['main cycle']['ets' ] = [ut[0]-ot[0], ut[0]-ot[0]]

    dusage = shutil.disk_usage('/')
    disk_pc = dusage.used/dusage.total*100

    cpu_pc = psutil.cpu_percent(interval=3)

    # Memory info in bytes
    mem = psutil.virtual_memory()
    mem_tot = mem.total / (1024**2)  # Mb 
    mem_available = mem.available / (1024**2) # Mb
    mem_used = mem.used / (1024**2)  # Mb
    mem_pc = mem_used/mem_tot*100

    """
    # conn.execute('create TABLE if not exists au_status (id INTEGER PRIMARY KEY, tstamp datetime, disk_pc float, mem_pc float, proc_pc float);')
    sql = f"insert into au_status (tstamp, mem_pc, disk_pc, proc_pc) values ('{datetime.datetime.now()}',{mem_pc:.2f},{dusage.used/dusage.total*100:.2f},  {cpu_percent:.2f})"
    print ("sql:", sql)
    
    with duckdb.connect('au_db2.duckdb') as conn:
        conn.execute(sql)

    """
    hoststatus.append([ ostatus['nk'], datetime.datetime.now(), mem_pc, disk_pc, cpu_pc])

    ostatus["nk"] = ostatus["nk"] + 1 
    if ostatus["nk"] > 100000:
        ostatus["nk"] = 0

    # Saving overall status
    with open(ostat, "w") as f:    
        f.write(json.dumps(ostatus, ensure_ascii=False))

    # Saving tasks last status
    with open(r_tasks, "w") as f:    
        f.write(json.dumps(tasks, ensure_ascii=False))


    print("------------------------------------------------------------")
    print(f"« ending r_peter  ( {ostatus['nk']} ):", str(datetime.datetime.now())[0:19], " len(hoststatus):", len(hoststatus))
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

r_peter_period = 40  # seconds

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


schedule.every(10).seconds.do(test_job)
schedule.every(40).seconds.do(r_peter)


#print(f">>> Scheduler state: running={scheduler.running}")

# Run scheduler in background thread
def run_scheduler():
    print(">>> Scheduler thread starting...")
    while True:
        schedule.run_pending()
        time.sleep(1)

scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()
print(">>> Scheduler thread started")

#print(f">>> Jobs: {schedule.get_jobs()}")


if __name__ == '__main__':
    app.run(debug=False, use_reloader=False)


""" or

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        init_once()
    app.run(debug=True)  # reloader ON
"""