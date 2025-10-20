from flask import Flask
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

hostname=socket.gethostname()

app = Flask(__name__)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

ftasks="tasks.json"


file_path = __file__  # __file__ is the current script's path
mod_time = os.path.getmtime(file_path)
mod_date = datetime.datetime.fromtimestamp(mod_time)


version=mod_date.strftime('%Y-%m-%d')
nk=0


@app.route('/')
def hello():
    global ftasks
    now = str(datetime.datetime.now())[0:19]
    tasks = json.load(open(ftasks))

    table = "<table border=1><tr><td>task_id<td>pipeline<td>lastrun<td>Period (mins)<td>ret<td>T watch<td>T proc"

    for ek in tasks.keys():
        table += f"<tr><td>{ek}<td>{tasks[ek]['pyfunction']}<td>{tasks[ek]['lrun']}"
        table += f"<td align=right>{tasks[ek]['period']:.2f}"
        if 'ret' in  tasks[ek].keys():
            table += f"<td align=right>{tasks[ek]['ret']}"
        else:
            table += f"<td align=right> - no ret"

        if 'ets' in  tasks[ek].keys():
            table += f"<td align=right>{tasks[ek]['ets'][1]:.3f}"
            table += f"<td align=right>{tasks[ek]['ets'][0]:.3f}"


    table += "</table>"

    resp = f"""<html>
    <head>
    <script>
        setTimeout(function() {{ location.reload(); }}, 10000);
    </script>
    </head>
    <body style='font-family:roboto'>
    <h1>Header</h1>
    {table}
    <hr color=lime>
    Version {version}, running at {hostname} ({now}) [{nk}]
    </body>
    </html>
    """

    return resp



def dummy():
    try:
        ### do dummy job    
        print ("                »»»»»»»» dummy running !!!")
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
        print ("                »»»»»»»» ext_python running !!!")
        pret = subprocess.run(['python', 'other_script.py'],     capture_output=True, text=True)
        ret = pret.stderr
    except Exception as e:
        ret = e
    return ret




@app.route('/page2')
def page2():
    now = str(datetime.datetime.now())[0:19]
    return f'{now} This is Page 2'


def ping_pong_task():
    global nk, ftasks
    nk = nk+1
    # repeated task function
    ot = [time.perf_counter(), time.process_time()]
    
    tasks = json.load(open(ftasks))
    # print (tasks)
    for et in tasks.keys():
        # print("                KEY:", et)
        if et == "main":
            pass
        else:
            difference = datetime.datetime.now() - datetime.datetime.strptime(tasks[et]['lrun'], "%Y-%m-%d %H:%M:%S")
            print (f"        > {tasks[et]['pyfunction']:12s} {difference.seconds:3d} ", end = "")
            if difference.seconds/60 > tasks[et]['period']:
                print (f" >> call {tasks[et]['pyfunction']}()")
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


            else:
                print (" ()")

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

    print(f"{nk:9} Ping pong task running:", datetime.datetime.now())

    now = str(datetime.datetime.now())[0:19]
    with open(ostat, "w") as f:    
        f.write(json.dumps({"host":hostname, "uptime":now}))

    if nk > 100000:
        nk=0


now = str(datetime.datetime.now())[0:19]

ostat = 'ostat.json'
ping_pong_period = 40  # seconds

try:
    if os.path.isfile(ostat):
        print ("""\n          AAAAA 
         AA  AA
        AA   AA
       AAAAAAAA 
      AA     AA
     AA      AAUTO STARTING... wait a minute, pleeeeeeaseeee ...
              """)
        print ('file exists... ', end='')
        time.sleep(ping_pong_period+10)
        ostatus = json.load(open(ostat))
        print (ostatus)
        difference = datetime.datetime.now() - datetime.datetime.strptime(ostatus['uptime'], "%Y-%m-%d %H:%M:%S")
        print(print("Seconds:", difference.seconds))
        if difference.seconds > 100:
            now = str(datetime.datetime.now())[0:19]
            scheduler.add_job(id='ping_pong_job', func=ping_pong_task, trigger='interval', seconds=ping_pong_period)
            with open(ostat, "w") as f:    
                f.write(json.dumps({"host":hostname, "uptime":now}))

    else:
        print(f"File `{ostat}` does not exist")
        with open(ostat, "w") as f:    
            f.write(json.dumps({"host":hostname, "uptime":now}))

        # Add an interval job that runs every 50 seconds (example)
        scheduler.add_job(id='ping_pong_job', func=ping_pong_task, trigger='interval', seconds=ping_pong_period)
except Exception as e:
    print("error: ", e)
    exit(-8)

try:
    tasks = json.load(open(ftasks))
except Exception as e:
    print (f"opening {ftasks}:", e)
    tasks={}

if tasks == {}:
    tasks = {
        "dummy":{"pyfunction":"dummy", "lrun":"2025-09-26 18:30:00", "period":2},
        "dummy2":{"pyfunction":"ext_python", "lrun":"2025-09-26 18:30:00", "period":3}
    }

with open(ftasks, "w") as f:    
    f.write(json.dumps(tasks, ensure_ascii=False))

if __name__ == '__main__':
    app.run(debug=True)
