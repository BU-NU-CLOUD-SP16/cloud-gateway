from flask import Flask, render_template, request
import subprocess
app = Flask(__name__)

dnat_cmd = "sudo iptables -t nat %s PREROUTING -d %s -j DNAT --to-destination %s"

@app.route("/dnat", methods=['POST', 'DELETE'])
def dnat():
    if request.method == 'POST':
        try:
            add_dnat(request.form['ori_ip'], request.form['real_ip'])
        except Exception as e:
            return str(e)
        return "succ"
 
    elif request.method == 'DELETE':
        try:
            ori_ip = request.form['ori_ip']
            real_ip = request.form['real_ip']

            # send del request to slave machine and parse response
            del_dnat(ori_ip, real_ip)
        except Exception as e:
            return str(e)
        return "succ"


def add_dnat(ori, new):
    return subprocess.call(dnat_cmd % ("-A", ori, new), shell = True) == 0

def del_dnat(ori, new):
    return subprocess.call(dnat_cmd % ("-D", ori, new), shell = True) == 0

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6432, debug=True)
