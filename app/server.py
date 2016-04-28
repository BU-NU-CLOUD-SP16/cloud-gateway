from flask import Flask, render_template, request, g

import os
import subprocess
import requests
import sqlite3
import yaml, json

app = Flask(__name__)

dnat_cmd = "sudo iptables -t nat %s PREROUTING -i %s -d %s -j DNAT --to-destination %s"
port_fwd_cmd = "sudo iptables -t nat %s PREROUTING -p %s -d %s --dport %s -j DNAT --to-destination %s"
internet_cmd = "sudo iptables -t nat %s POSTROUTING ! -d %s -j MASQUERADE"
internet_tag_file = "./internet_conn_on"

internet_status = "OFF"


# Override default database setting
net_config = yaml.load(open('../config/config.yaml').read())
app.config.update(dict(
    DATABASE = os.path.join(app.root_path, 'database.db'),
    DEBUG = True,
    SLAVE_URL = ("http://%s:%s") % (net_config["VcgIp"], net_config["VcgServicePort"])
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
        cur.execute("create table port_fwds (dport text, dst text, protocol text)")
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

    return render_template("index.html", dnats=dnats, port_fwds=port_fwds, internet_state=internet_status)


@app.route("/dnat", methods=['GET', 'POST', 'DELETE'])
def dnat():
    if request.method == 'GET':
        cur = get_db().cursor()
        return cur.execute("SELECT * FROM dnats")

    elif request.method == 'POST':
        ori_ip = request.form['ori_ip']
        real_ip = request.form['real_ip']

        # send put request to slave vcg
        rsp = requests.post(app.config["SLAVE_URL"] + '/dnat', data = request.form)
        rval = json.loads(rsp.content)

        # if fail in slave
        if rval["desc"] != "succ": 
            return rsp.contect

        # execute rule add locally
        try:
            add_dnat(ori_ip, real_ip)
            add_arp(real_ip, "eth0")
            add_arp(ori_ip, "eth1")
            print "haha"
            # write new rules into database
            
            execute_sql('insert into dnats values (?,?)', (ori_ip, real_ip,))
            print "321"
        except Exception as e:
            rval["desc"] = "fail"
            rval["reason"] = str(e)
        return json.dumps(rval)

    elif request.method == 'DELETE':
        ori_ip = request.form['ori_ip']
        real_ip = request.form['real_ip']
        params = {"ori_ip" : ori_ip, "real_ip" : real_ip}

        # send delete request to slave vcg
        rsp = requests.delete(app.config["SLAVE_URL"] + '/dnat', data = params)
        rval = json.loads(rsp.content)

        # if fail in slave
        if rval["desc"] != "succ": 
            return rsp.content

        try:
            # execute rule delete locally
            del_dnat(ori_ip, real_ip)
            del_arp(real_ip)
            del_arp(ori_ip, "eth1")

            # delete rule into database
            execute_sql('DELETE FROM dnats WHERE ori_ip=? and real_ip=?', (ori_ip, real_ip,))
        except Exception as e:
            rval["desc"] = "fail"
            rval["reason"] = str(e)
        return json.dumps(rval)


@app.route("/port_fwd", methods=['GET', 'POST', 'DELETE'])
def port_fwd():
    if request.method == 'POST':
        try:
            dport = request.form['dport']
            dst = request.form['dst']
            protocol = request.form['protocol']
        
            add_port_fwd(protocol, dport, dst)
            execute_sql('insert into port_fwds values (?, ?, ?)', (dport, dst, protocol))
            return "success"

        except Exception as e:
            return str(e)

    elif request.method == 'DELETE':
        try:
            dport = request.form['dport']
            dst = request.form['dst']
            protocol = request.form['protocol'].strip()
            
            del_port_fwd(protocol, dport, dst)
            execute_sql('DELETE FROM port_fwds WHERE dport=? and dst=? and protocol=?', (dport, dst, protocol,))
            return "success"

        except Exception as e:
            return str(e)

@app.route("/internet_connection", methods=['POST'])
def internet_connection():
    if request.method == 'POST':
        try:
            if request.form['flag'] == "OFF": 
                enable_internet()
            elif request.form['flag'] == "ON":
                disable_internet()
            return "succ"
        except Exception as e:
            print str(e)
            return str(e)

###################
# HELPER FUNCTION #
###################
def exeute_shell(cmd):
    return subprocess.check_output(cmd, shell = True)

def add_dnat(ori, new, dev="eth1"):
    return exeute_shell(dnat_cmd % ("-A", dev, ori, new))

def del_dnat(ori, new, dev="eth1"):
    return exeute_shell(dnat_cmd % ("-D", dev, ori, new))

def add_arp(ip, dev = "eth0"):
    """
    A a fake static arp for given ip address to ensure DNAT sucecess
    Note : DNAT will need mac addr for destination ip addr
    """
    cmd = ("arp -i %s -s %s 11:50:22:44:55:55") % (dev, ip)
    return exeute_shell(cmd)

def del_arp(ip, dev = "eth0"):
    return exeute_shell(("arp -i %s -d %s") % (dev, ip))

def add_port_fwd(proto, dport, dst):
    cmd = port_fwd_cmd % ("-A", proto, net_config["HqPrivateIp"], dport, dst)
    return exeute_shell(cmd)

def del_port_fwd(proto, dport, dst):
    cmd = port_fwd_cmd % ("-D", proto, net_config["HqPrivateIp"], dport, dst)
    return exeute_shell(cmd)

def enable_internet():
    global internet_status
    internet_status = "ON"
    dst = net_config["HqCidr"]
    cmd = internet_cmd % ('-A', dst)
    return exeute_shell(cmd)

def disable_internet():
    global internet_status
    internet_status = "OFF"
    dst = net_config["HqCidr"]
    cmd = internet_cmd % ('-D', dst)
    return exeute_shell(cmd)

if __name__ == "__main__":
    init_db()
    app.run(host='0.0.0.0',port=int(net_config['VcgServicePort']))
