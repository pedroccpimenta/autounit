from flask import Flask, request, redirect, url_for, Response
from flask_apscheduler import APScheduler
import datetime
import socket
import json
import os
import sys
import requests
import pymysql
import clts_pcp as clts
import time 
import subprocess

hostname=socket.gethostname()[:30]

app = Flask(__name__)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

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


@app.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools_discovery():
    return Response(status=204)


@app.route('/')
def hello():
    global lpret
    now = str(datetime.datetime.now())[0:19]
    try:
        tasks = json.load(open(r_tasks))
        ostatus = json.load(open(ostat))
    except Exception as err:
        return("setting up... a minute, please...")

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
    <hr color=lime>
    Version {version}, running at {hostname} ({now}) [{ostatus['nk']}]
    </body>
    </html>
    """

    return resp


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
    ostatus = json.load(open(ostat))

    print("\n\n» Starting r_peter  (", ostatus['nk'],"):", str(datetime.datetime.now())[0:19])
    #print("time is:", time, "type:", type(time))
    ot = [time.perf_counter(), time.process_time()]
    
    tasks  = json.load(open(r_tasks))
    status = json.load(open(task_status))
    #print (" r_peter - tasks:" , tasks)
    #print (" r_peter - status:" , status)

    print (f"| id {" ":17s} | task status and execution")
    for et in tasks.keys():
        if et == "main" or et == "main cycle":
            pass
        else:
            print(f"| {et:<20s} | {status[et]:5s}", end="")
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

    # Saving tasks last status
    with open(r_tasks, "w") as f:    
        f.write(json.dumps(tasks, ensure_ascii=False))

    ostatus["nk"] = ostatus["nk"] + 1 
    if ostatus["nk"] > 100000:
        ostatus["nk"] = 0

    # Saving overall status
    with open(ostat, "w") as f:    
        f.write(json.dumps(ostatus, ensure_ascii=False))

    print("------------------------------------------------------------")
    print(f"« ending r_peter  ( {ostatus['nk']} ):", str(datetime.datetime.now())[0:19])
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

r_peter_period = 40  # seconds
current_env = os.environ.get('CONDA_DEFAULT_ENV')
print ("current_env", current_env)

## Defining the file running tasks (r_tasks) based on original tasks (o_tasks)

if os.path.exists(o_tasks):
    tasks = json.load(open(o_tasks))
    print (f"o_tasks ({o_tasks}) loaded.")
else:
    print (f"o_taks ({o_tasks}) not found, assuming default value.")
    tasks = {
        "pcp_meteo_icao": {
            "call": "python", 
            "script": "scripts/pcp_meteo_icao.py", 
            "lrun": "2025-12-23 10:20:46", 
            "period": 15, 
            "ets": [None, None], 
            "ret": " - not yet called - "
        }   
    }


if 'main' not in tasks.keys():
    tasks['main cycle'] ={
        "main": {
            "call": "function", 
            "script": "--", 
            "lrun": "2025-12-23 10:20:46", 
            "period": r_peter_period/100, 
            "ets": [None, None], 
            "ret": " - not yet called - "
        }   
    }

print (f"opening {r_tasks} and saving tasks:")
print (json.dumps(tasks, ensure_ascii=False, indent=3))    
with open(r_tasks, "w", encoding="utf-8") as fh:
    fh.write(json.dumps(tasks, ensure_ascii=False, indent=3))
print (f"{r_tasks} created!")


## Defining default status for default tasks

print (f"\n> Saving default task status to `{task_status}`: ")

status = {ek: "off" for ek in tasks}

with open(task_status, "w", encoding="utf-8") as f: json.dump({ek: "off" for ek in tasks}, f, ensure_ascii=False, indent=3)

print (json.dumps(status, ensure_ascii=False, indent=3))    
print ("done!")



## Calling and scheduling r_peter()

r_peter()
print (f"\n> opening `{ostat}` (overall status) and saving hostname and up timestamp...", end ="")
scheduler.add_job(id='r_peter_job', func=r_peter, trigger='interval', seconds=r_peter_period)
with open(ostat, "w") as f:    
    f.write(json.dumps({"host":hostname, "uptime":str(datetime.datetime.now())[0:19], "nk":0}))
print (" done!")

if __name__ == '__main__':
    app.run(debug=True)
