from flask import Flask, render_template, request, g
import os
import subprocess
import requests
import sqlite3
import yaml

app = Flask(__name__)

dnat_cmd = "sudo iptables -t nat %s PREROUTING -d %s -j DNAT --to-destination %s"
port_fwd_cmd = "sudo iptables -t nat %s PREROUTING -d %s -dport %s -j DNAT --to-destination %s"

# Override default database setting
vcg_config = yaml.load(open('config.yaml').read())
app.config.update(dict(
    DATABASE = os.path.join(app.root_path, 'database.db'),
    DEBUG = True,
    SLAVE_URL = ("http://%s:%s") % (vcg_config["VcgIp"], vcg_config["VcgServicePort"])
    ))

#########################
# DATABASE RELATED CODE #
#########################
def init_db():
    if not os.path.isfile(app.config['DATABASE']):
        # create database file
        path, file_name = os.path.split(app.config['DATABASE'])
        if not os.path.isdir(path):
            os.makedirs(path)
        open(file_name, 'a').close()

        # init tables
        conn = sqlite3.connect(app.config['DATABASE'])
        cur = conn.cursor()
        cur.execute("create table dnats (ori_ip text, real_ip text)")
        cur.execute("create table port_fwds (dport text, dst text)")
        conn.commit()
        conn.close()

def connect_to_database():
    return sqlite3.connect(app.config['DATABASE'])

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db

def execute_sql(query, params):
    conn = get_db()
    conn.cursor().execute(query, params)
    conn.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

#############
# HOME PAGE #
#############
@app.route("/")
def index():
    # return all exsiting dnat rules
    dnats = get_db().cursor().execute("SELECT * FROM dnats")

    # return all existing port forwarding rules
    port_fwds = get_db().cursor().execute("SELECT * FROM port_fwds")

    return render_template("index.html", dnats=dnats, port_fwds=port_fwds)


@app.route("/dnat", methods=['GET', 'POST', 'DELETE'])
def dnat():
    if request.method == 'GET':
        cur = get_db().cursor()
        return cur.execute("SELECT * FROM dnats")

    elif request.method == 'POST':
        ori_ip = request.form['ori_ip']
        real_ip = request.form['real_ip']

        # send put request to slave vcg
#        rsp = requests.post(app.config["SLAVE_URL"] + '/dnat', data = request.form)
 #       # if fail
  #      if rsp.content != "succ": 
   #         return rsp.content

        # execute rule add locally

        # write new rules into database
	#dnats = get_db().cursor().execute("SELECT * FROM dnats")
	#port_fwds = get_db().cursor().execute("SELECT * FROM port_fwds")
        execute_sql('insert into dnats values (?,?)', (ori_ip, real_ip,))
        #return render_template("index.html",dnats=dnats, port_fwds=port_fwds)
	return "success" 

    elif request.method == 'DELETE':
        ori_ip = request.form['ori_ip']
        real_ip = request.form['real_ip']
        # params = {"ori_ip" : ori_ip, "real_ip" : real_ip}

        # send delete request to slave vcg
        # rsp = requests.delete(app.config["SLAVE_URL"] + '/dnat', data = params)
        
        # if fail
        # if rsp.content != "succ": 
        #    return rsp.content

        # execute rule delete locally
        # del_dnat(ori_ip, real_ip)
        # del_arp(real_ip)
	# print params
        # delete rule into database
        execute_sql('DELETE FROM dnats WHERE ori_ip=? and real_ip=?', (ori_ip, real_ip,))
        return "success"

@app.route("/port_fwd", methods=['GET', 'POST', 'DELETE'])
def port_fwd():
    if request.method == 'GET':
        cur = get_db().cursor()
        return cur.execute("SELECT * FROM dnats")

    elif request.method == 'POST':
        try:
            dport = request.form['dport']
            dst = request.form['dst']

            add_port_fwd(dport, dst)

            #  rule into database
            execute_sql('insert into port_fwds values (?, ?)', (dport, dst,))
            return "success"
        except Exception as e:
            return str(e)

    elif request.method == 'DELETE':
        try:
            dport = request.form['dport']
            dst = request.form['dst']

            del_port_fwd(dport, dst)

            execute_sql('DELETE FROM port_fwds WHERE dport=? and dst=?', (dport, dst,))
            return "success"
        except Exception as e:
            return str(e)

###################
# HELPER FUNCTION #
###################
def add_dnat(ori, new):
    return subprocess.call(dnat_cmd % ("-A", ori, new), shell = True) == 0

def del_dnat(ori, new):
    return subprocess.call(dnat_cmd % ("-D", ori, new), shell = True) == 0

def add_arp(ip, dev = "eth0"):
    """
    A a fake static arp for given ip address to ensure DNAT sucecess
    Note : DNAT will need mac addr for destination ip addr
    """
    cmd = ("arp -i %s -s %s 11:50:22:44:55:55") % (dev, ip)
    return subprocess.call(cmd, shell = True) == 0

def del_arp(ip):
    return subprocess.call(["arp -d ", ip], shell = True) == 0

def add_port_fwd(dport, dst):
    cmd = port_fwd_cmd % ("-A", "this_machine ip", dport, dst)
    return subprocess.check_output(cmd, shell = True)

def del_port_fwd(dport, dst):
    cmd = port_fwd_cmd % ("-D", "this_machine ip", dport, dst)
    return subprocess.check_output(cmd, shell = True)


if __name__ == "__main__":
    init_db()
    app.run(host='0.0.0.0',port=int(vcg_config['VcgServicePort']))

