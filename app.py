from flask import Flask, request, redirect, url_for
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

ftasks="tasks.json"
ftstat="tasks_status.json"

file_path = __file__  # __file__ is the current script's path
mod_time = os.path.getmtime(file_path)
mod_date = datetime.datetime.fromtimestamp(mod_time)

version=mod_date.strftime('%Y-%m-%d')
nk=0
ostat = 'ostat.json'
edirect = False

lpret = []


@app.route('/')
def hello():
    global lpret
    #global ftasks
    now = str(datetime.datetime.now())[0:19]
    tasks = json.load(open(ftasks))
    ostatus = json.load(open(ostat))
    #print (" =========================", ostatus)

    table = "<table border=1 cellspacing=0 cellpadding=1><tr style='background:silver'><td>task_id<td>pipeline<td>lastrun<td>Period (mins)<td>ret<td>T watch<td>T proc"

    for ek in tasks.keys():
        table += f"<tr><td>{ek}<td>{tasks[ek]['pyfunction']}<td>{tasks[ek]['lrun']}"
        table += f"<td align=right>{tasks[ek]['period']:.2f}"
        if 'ret' in  tasks[ek].keys():
            table += f"<td align=right>{tasks[ek]['ret']}"
        else:
            table += f"<td align=right> - no ret (!)"

        if 'ets' in  tasks[ek].keys():
            table += f"<td align=right>{tasks[ek]['ets'][1]:.3f}"
            table += f"<td align=right>{tasks[ek]['ets'][0]:.3f}"


    table += "</table>"


    table2="<table border=1  cellspacing=0 cellpadding=1><tr style='background:silver'>"
    table2 += f"<tr><td><colspan =2>lpret:{lpret}"
    table2 += "<tr><td>#<td>"
    for ep in lpret :

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
        setTimeout(function() {{ location.reload(); }}, 10000);
    </script>
    </head>
    <body style='font-family:roboto'>
    <h1>Header</h1>
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


# Process the form and redirect based on input
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
    global ftasks
    global edirect

    if edirect:
        pass
    else:
        xkvalue = request.form.get('xkvalue')
        if xkvalue!='EZ53':
            return redirect(url_for('hello'))


    now = str(datetime.datetime.now())[0:19]
    tasks = json.load(open(ftasks))

    table = "<form action='/edittasks' method=POST><table border=1 cellspacing=0 cellpadding=1><tr style='background:silver'><task_status><td>task_id<td>pipeline<td>lastrun<td>Period (mins)<td>ret<td>T watch<td>T proc"

    for ek in tasks.keys():
        table += f"<tr><td> botão MUDA estado <td>{ek}<td>{tasks[ek]['pyfunction']}<td>{tasks[ek]['lrun']}"
        table += f"<td align=right>{tasks[ek]['period']:.2f}"
        if 'ret' in  tasks[ek].keys():
            table += f"<td align=right>{tasks[ek]['ret']}"
        else:
            table += f"<td align=right> - no ret (!)"

        if 'ets' in  tasks[ek].keys():
            table += f"<td align=right>{tasks[ek]['ets'][1]:.3f}"
            table += f"<td align=right>{tasks[ek]['ets'][0]:.3f}"


    table += "</table><input type=password name=xkvalue value='EZ53'><input type='submit' value='Submit'>"


    ostatus = json.load(open(ostat))
    print (" =========================", ostatus)
    task_status=json.load(open(ftstat))
    print (" =========================", task_status)


    resp = f"""<html>
    <head>
    <script>
       // setTimeout(function() {{ location.reload(); }}, 10000);
        setTimeout(function() {{ location.submit(); }}, 10000);
    </script>
    </head>
    <body style='font-family:roboto'>
    <h1>Header</h1>
    {table}
     <hr color=lime>
    Version {version}, running at {hostname} ({now}) [{ostatus['nk']}]
    </body>
    </html>
    """

    edirect=False
    return resp


def keep_alive():
    jtkr = requests.get("https://autounit.onrender.com/")
    return  str(jtkr)
    #return(53)

def keep_alive2():
    jtkr = requests.get("https://autounit-b.onrender.com/")
    return  str(jtkr)
     
    #return(53)

def dummy():
    jtkr = requests.get("https://autounit.onrender.com/")
    try:
        ### do dummy job    
        print ("     »» dummy running !!!")
        now = str(datetime.datetime.now())[0:19]
        #tasks = json.load(open(ftasks))
        #tasks['dummy']['lrun']=now
        #with open(ftasks, "w") as f:    
        #    f.write(json.dumps(tasks, ensure_ascii=False))
        ret = 0
    except Exception as e:
        ret = e
    return ret

def ext_python():
    try:
        print ("     »» ext_python running !!!")
        pret = subprocess.run(['python', 'other_script.py'], capture_output=True, text=True)
        ret = pret.stderr
    except Exception as e:
        ret = e
    return ret

def pcp_icao():
    global lpret
    now=str(datetime.datetime.now())[0:19]
    try:
        print ("     »» pcp_icao !!!")
        #pret = subprocess.Popen(['python', 'scripts/pcp_meteo_icao.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pret = subprocess.Popen(['python', 'scripts/pcp_meteo_icao.py'])
        #pret = subprocess.Popen(['python', 'scripts/pcp_meteo_icao.py'], stdout=subprocess.PIPE, 
        #                stderr=subprocess.PIPE, 
        #                text=True)
        print ("\n\n ---------------------------------------------------")
        print( pret)
        print ("---------------------------------------------------\n\n")
        lpret.append(pret)
        ret = f"pcp_meteo_icao launched ({now}): {str(pret)}"

    except Exception as e:
        ret = e
    return ret

def ping_pong_task():
    ostatus = json.load(open(ostat))

    print("» Ping pong task started running (", ostatus['nk'],"):", datetime.datetime.now())
    #global ftasks
    # repeated task function
    ot = [time.perf_counter(), time.process_time()]
    
    tasks = json.load(open(ftasks))
    task_status=json.load(open(ftstat))
    # print (tasks)

    for et in tasks.keys():
        if et == "main":
            pass
        else:
            print(f"  KEY: {et:>19s} |", end="")

            difference = datetime.datetime.now() - datetime.datetime.strptime(tasks[et]['lrun'], "%Y-%m-%d %H:%M:%S")
            print (f" {tasks[et]['pyfunction']:>22s} | {tasks[et]['lrun']:>20s} | {difference.seconds:>5d} |", end = "")
            if difference.seconds/60 > tasks[et]['period']:
                print (f" calling {tasks[et]['pyfunction']}() ..." )
                bc = [time.perf_counter(), time.process_time()]
                try:
                    rv = eval(tasks[et]['pyfunction'] + "()")
                except Exception as e:
                    rv = e
                    #pass
                
                pc = [time.perf_counter(), time.process_time()]

                tasks[et]["lrun"]=str(datetime.datetime.now())[0:19]
                tasks[et]["ets"]=[pc[0]-bc[0], pc[1]-bc[1]]
                rv=str(rv)
                if type(rv) == type("abc"):
                    tasks[et]["ret"] = rv.replace('"', "`")
                else:
                    tasks[et]["ret"] = rv 
                print( "     »»", rv )

            else:
                print (" (... not yet time:", tasks[et]['period']*60, ")")

    now = str(datetime.datetime.now())[0:19]

    ut = [time.perf_counter(), time.process_time()]
    tasks['main'] = {
        'pyfunction':'null', 'lrun':now,'period':ping_pong_period/60, 
        'ets':[ut[0]-ot[0], ut[0]-ot[0]],
        'ret':"0"
    }

    #print (tasks)
    with open(ftasks, "w") as f:    
        f.write(json.dumps(tasks, ensure_ascii=False))

    #ostatus = json.load(open(ostat))


    now = str(datetime.datetime.now())[0:19]
    #print("______________________",ostatus)
    ostatus['uptime']= now
    ostatus["nk"] = ostatus["nk"] + 1 
    if ostatus["nk"] > 100000:
        ostatus["nk"] = 0

    #print("______________________",ostatus)

    with open(ostat, "w") as f:    
        f.write(json.dumps(ostatus, ensure_ascii=False))

    print(f"« Ping pong task finished running ( {ostatus['nk']} ):", datetime.datetime.now())

####### AUTOUNIT

now = str(datetime.datetime.now())[0:19]

ping_pong_period = 40  # seconds
current_env = os.environ.get('CONDA_DEFAULT_ENV')
print ("current_env", current_env)


try:
    print ("""\n          AAAAA          UU     UU
         AA  AA          UU     UU                     
        AA   AA          UU     UU
       AAAAAAAA          UU     UU 
      AA     AA          UU     UU
     AA      AAutonomous UUUUUUUUUnit - TO STARTING... wait a minute, pleeeeeeaseeee ...
              """)
    
    if os.path.isfile(ostat):
        print (f'file `{ostat}` exists.')
        time.sleep(ping_pong_period+10)
        ostatus = json.load(open(ostat))
        #print (ostatus)
        ostatus['nk']=0
        difference = datetime.datetime.now() - datetime.datetime.strptime(ostatus['uptime'], "%Y-%m-%d %H:%M:%S")
        print("Seconds:", difference.seconds)
        if difference.seconds > 100:
            now = str(datetime.datetime.now())[0:19]
            scheduler.add_job(id='ping_pong_job', func=ping_pong_task, trigger='interval', seconds=ping_pong_period)
            with open(ostat, "w") as f:    
                f.write(json.dumps({"host":hostname, "uptime":now, "nk":nk}))

    else:
        print(f"File `{ostat}` does not exist.")
        with open(ostat, "w") as f:    
            f.write(json.dumps({"host":hostname, "uptime":now, "nk":0}))

        # Add an interval job that runs every 50 seconds (example)
        scheduler.add_job(id='ping_pong_job', func=ping_pong_task, trigger='interval', seconds=ping_pong_period)

except Exception as e:
    print("error:", e)
    exit(-8)

try:
    tasks = json.load(open(ftasks))
except Exception as e:
    print (f"opening {ftasks}:", e)
    tasks={}

    if tasks == {}:
        # Version September 2025
        tasks = {
        "dummy":{"pyfunction":"dummy", "lrun":"2025-09-26 18:30:00", "period":2},
        "dummy2":{"pyfunction":"ext_python", "lrun":"2025-09-26 18:30:00", "period":3},
        "dummy3":{"pyfunction":"keep_alive2", "lrun":"2025-09-26 18:30:00", "period":6}
        }

        # Version December 2025

        tasks = {
            "dummy": {"pyfunction": "dummy", "lrun": "2025-12-14 18:50:52", "period": 2, "ets": [0.3018737999955192, 0.0], "ret": "0"}, 
            "dummy2": {"pyfunction": "ext_python", "lrun": "2025-12-14 18:50:52", "period": 3, "ets": [0.025285999989137053, 0.0], "ret": "python: can't open file 'D:\\\\github\\\\autounit\\\\other_script.py': [Errno 2] No such file or directory\n"}, 
            "main": {"pyfunction": "null", "lrun": "2025-12-14 18:52:11", "period": 0.6666666666666666, "ets": [0.002531200007069856, 0.002531200007069856], "ret": "0"}, 
            "keep_alive": {"pyfunction": "keep_alive", "lrun": "2025-12-14 18:51:32", "period": 3, "ets": [0.37277300003916025, 0.0], "ret": "<Response [200]>"}, 
            "keep_alive2": {"pyfunction": "keep_alive2", "lrun": "2025-12-14 18:50:53", "period": 3, "ets": [0.38333000004058704, 0.0], "ret": "<Response [200]>"},
            "pcp_meteo_icao": {"pyfunction": "pcp_icao", "lrun": "2025-12-14 18:50:53", "period": 15, "ets": [None, None], "ret": " - not yet called - "}
            }
    print (f"{ftasks} created...")
                     

with open(ftasks, "w") as f:    
    f.write(json.dumps(tasks, ensure_ascii=False))

tstat = {}

for ek in tasks.keys():
            tstat[ek]="off"

with open(ftstat, "w") as f:    
    f.write(json.dumps(tstat, ensure_ascii=False))


## 14/12/2025 tasks
tasks = { "dummy": {"pyfunction": "dummy", "lrun": "2025-12-14 18:22:25", "period": 2, "ets": [0.3278165999799967, 0.0], "ret": "0"}, 
         "dummy2": {"pyfunction": "ext_python", "lrun": "2025-12-14 18:19:45", "period": 3, "ets": [0.023559799999929965, 0.0], "ret": "python: can't open file 'D:\\\\github\\\\autounit\\\\other_script.py': [Errno 2] No such file or directory\n"}, 
         "main": {"pyfunction": "null", "lrun": "2025-12-14 18:22:25", "period": 0.6666666666666666, "ets": [0.3526784000569023, 0.3526784000569023], "ret": "0"}, 
         "keep_alive": {"pyfunction": "keep_alive", "lrun": "2025-12-14 18:20:25", "period": 3, "ets": [0.384520799969323, 0.0], "ret": "<Response [200]>"}, 
         "keep_alive2": {"pyfunction": "keep_alive2", "lrun": "2025-12-14 18:19:47", "period": 3, "ets": [1.0239231000305153, 0.0], "ret": "<Response [200]>"}
    }


if __name__ == '__main__':
    app.run(debug=True)
