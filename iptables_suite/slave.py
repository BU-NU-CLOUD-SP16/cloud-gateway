from flask import Flask, render_template, request
import subprocess
app = Flask(__name__)

dnat_cmd = "sudo iptables -t nat %s PREROUTING -d %s -j DNAT --to-destination %s"

@app.route("/dnat", methods=['GET', 'PUT', 'DEL'])
def dnat():
    if request.method == 'GET':
        return list_dnat()

    elif request.method == 'POST':
        try:
            add_dnat(request.form['ori_dst'], request.form['new_dst'])
            add_arp(request.form['new_dst'])
        except Exception as e:
            return str(e)
        return "succ"

    elif request.method == 'DELETE':
        try:
            ori_dst = request.args.get('ori_dst')
            new_dst = request.args.get('new_dst')

            # send del request to slave machine and parse response
            del_dnat(ori_dst, new_dst)
            del_arp(new_dst)
        except Exception as e:
            return str(e)
        return "succ"


def add_dnat(ori, new):
    return subprocress.call(dnat_cmd % ("-A", ori, new), shell = True) == 0

def del_dnat(ori, new):
    return subprocress.call(dnat_cmd % ("-D", ori, new), shell = True) == 0

if __name__ == "__main__":
    app.run()