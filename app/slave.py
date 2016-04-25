from flask import Flask, render_template, request
import subprocess
import yaml, json
app = Flask(__name__)

dnat_cmd = "sudo iptables -t nat %s PREROUTING -d %s -j DNAT --to-destination %s"

config = yaml.load(open('/home/ubuntu/cloud-gateway/config/config.yaml','r').read())

@app.route("/dnat", methods=['POST', 'DELETE'])
def dnat():
    if request.method == 'POST':
        rval = {}
        try:    
            add_dnat(request.form['ori_ip'], request.form['real_ip'])
        except Exception as e:
            rval["desc"] = "fail"
            rval["reason"] = str(e)

        rval["desc"] = "succ"
        rval["reason"] = ""
        return json.dumps(rval)
 
    elif request.method == 'DELETE':
        rval = {}
        try:
            # send del request to slave machine and parse response
            del_dnat(request.form['ori_ip'], request.form['real_ip'])
        except Exception as e:
            rval["desc"] = "fail"
            rval["reason"] = str(e)
            
        rval["desc"] = "succ"
        rval["reason"] = ""
        return json.dumps(rval)

def add_dnat(ori, new):
    return subprocess.check_output(dnat_cmd % ("-A", ori, new), shell = True)

def del_dnat(ori, new):
    return subprocess.check_output(dnat_cmd % ("-D", ori, new), shell = True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(config['VcgServicePort']), debug=True)
