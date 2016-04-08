from flask import Flask, render_template, request
import subprocess
app = Flask(__name__)

dnat_cmd = "sudo iptables -t nat %s PREROUTING -d %s -j DNAT --to-destination %s"

@app.route("/iptables", methods=['GET', 'PUT', 'DEL'])
def iptables():
    if request.method == 'GET':
        return list_dnat()

    elif request.method == 'POST':
        add_dnat(request.form['ori_dst'], request.form['new_dst'])
        add_arp(request.form['new_dst'])
        return ???

    elif request.method == 'DELETE':
        ori_dst = request.args.get('ori_dst')
        new_dst = request.args.get('new_dst')

        # send del request to slave machine and parse response
        del_dnat(ori_dst, new_dst)
        del_arp(new_dst)
        return ??


def add_dnat(ori, new):
    return subprocress.call(dnat_cmd % ("-A", ori, new), shell = True) == 0

def del_dnat(ori, new):
    return subprocress.call(dnat_cmd % ("-D", ori, new), shell = True) == 0

if __name__ == "__main__":
    app.run()