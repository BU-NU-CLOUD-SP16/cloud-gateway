from flask import Flask, render_template, request
import subprocess
import requests
app = Flask(__name__)

dnat_cmd = "sudo iptables -t nat %s PREROUTING -d %s -j DNAT --to-destination %s"
port_fwd_cmd = "sudo iptables -t nat %s PREROUTING -d %s -dport %s -j DNAT --to-destination %s"

@app.route("/")
def index():
	# iptables = detail_iptable()
	# Parse return value from detail_iptable in the form below
	pub_iptables = [('10.0.0.1', '192.168.1.1'), \
		     		('192.0.0.1', '10.0.0.1'),   \
	                ('168.192.0.1', '54.5.9.1')]
	pri_iptables = [('10.0.0.1', '192.168.1.1'), \
		     		('192.0.0.1', '10.0.0.1'),   \
	                ('10.0.0.1', '192.168.1.1'), \
		     		('192.0.0.1', '10.0.0.1'),   \
	                ('10.0.0.1', '192.168.1.1'), \
	                ('10.0.0.1', '192.168.1.1'), \
		     		('192.0.0.1', '10.0.0.1'),   \
		     		('192.0.0.1', '10.0.0.1'),   \
		     		('192.0.0.1', '10.0.0.1'),   \
		     		('192.0.0.1', '10.0.0.1'),   \
	                ('168.192.0.1', '54.5.9.1')]
	return render_template("index.html", public_rows=pub_iptables, private_rows=pri_iptables)


@app.route("/dnat", methods=['GET', 'POST', 'DELETE'])
def dnat():
	if request.method == 'GET':
		return list_dnat()

	elif request.method == 'POST':
		# send put request to slave vcg
		rsp = request.put('http://vcgip/dnat', data = request.form)
		# if fail
		if rsp: 
			return ...

		add_dnat(request.form['ori_dst'], request.form['new_dst'])
		add_arp(request.form['new_dst'])
		return ???

	elif request.method == 'DELETE':
		ori_dst = request.args.get('ori_dst')
		new_dst = request.args.get('new_dst')
		params = {"ori_dst" : ori_dst, "new_dst" : new_dst}

		# send delete request to slave vcg
		rsp = request.delete('http://vcgip/dnat', params = params)
		# if fail
		if rsp: 
			return ...

		# send del request to slave machine and parse response
		del_dnat(ori_dst, new_dst)
		del_arp(new_dst)
		return 

@app.route("/port_fwd", methods=['GET', 'POST', 'DEL'])
def port_fwd():
	if request.method == 'GET':
		return list_port_pwd()

	elif request.method == 'POST':
		dport = request.form['dport']
		dst = request.form['dst']
		return add_port_fwd(dport, dst)

	elif request.method == 'DELETE':
		dport = request.args.get('dport')
		dst = request.args.get('dst')
		return del_port_fwd(dport, dst)

# todo: We need ted to clearify that whether this "internet access"
# is in face port forwarding, which means 'internet can access". 
# But he described this in a wrong way in the previous meeting
@app.route("/internet/", methods=['POST'])
def internet():
	return "None"


def add_dnat(ori, new):
    return subprocress.call(dnat_cmd % ("-A", ori, new), shell = True) == 0

def del_dnat(ori, new):
    return subprocress.call(dnat_cmd % ("-D", ori, new), shell = True) == 0

def list_dnat():
    rval = subprocress.check_output("iptables -t nat -L", shell = True)
    # todo : handling output string

def add_arp(ip, dev = "eth0"):
	"""
	A a fake static arp for given ip address to ensure DNAT sucecess
	Note : DNAT will need mac addr for destination ip addr
	"""
    cmd = ("arp -i %s -s %s 11:50:22:44:55:55") % (dev, ip)
    return subprocress.call(cmd, shell = True) == 0

def del_arp(ip):
    return subprocress.call(["arp -d ", ip], shell = True) == 0


def add_port_fwd(dport, dst):
	cmd = port_fwd_cmd % ("-A", "this_machien ip", dport, dst)
	return subprocress.call(cmd, shell = True) == 0

def del_port_fwd(dport, dst):
	cmd = port_fwd_cmd % ("-D", "this_machien ip", dport, dst)
	return subprocress.call(cmd, shell = True) == 0

def list_port_pwd():
    rval = subprocress.check_output("iptables -t nat -L", shell = True)
    # todo : handling output string


if __name__ == "__main__":
	app.run()