from flask import Flask, render_template, request, g
import subprocess
import requests
app = Flask(__name__)

dnat_cmd = "sudo iptables -t nat %s PREROUTING -d %s -j DNAT --to-destination %s"
port_fwd_cmd = "sudo iptables -t nat %s PREROUTING -d %s -dport %s -j DNAT --to-destination %s"

# Database setting
DATABASE = './database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

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
		cur = get_db().cursor()
		for row in cur.execute("select * from dnats"):
			#do something
	elif request.method == 'POST':
		# send put request to slave vcg
		rsp = requests.put('http://vcgip/dnat', data = request.form)
		# if fail
		if rsp.content != "succ": 
			return rsp.content

		# execute rule add locally
		add_dnat(request.form['ori_dst'], request.form['new_dst'])
		add_arp(request.form['new_dst'])

		# write new rules into database
		cur = get_db().cursor()
		values = [ori_dst, new_dst]
		cur.execute('insert into dnat values (?,?)', (ori_dst, new_dst,))

		return "succ"

	elif request.method == 'DELETE':
		ori_dst = request.args.get('ori_dst')
		new_dst = request.args.get('new_dst')
		params = {"ori_dst" : ori_dst, "new_dst" : new_dst}

		# send delete request to slave vcg
		rsp = request.delete('http://vcgip/dnat', params = params)
		# if fail
		if rsp.content != "succ": 
			return rsp.content

		# execute rule delete locally
		del_dnat(ori_dst, new_dst)
		del_arp(new_dst)

		# delete rule into database
		cur = get_db().cursor()
		cur.execute('delete from dnat where ori_dst=? and new_dst=?', (ori_dst, new_dst,))
		return "succ"


@app.route("/port_fwd", methods=['GET', 'POST', 'DEL'])
def port_fwd():
	if request.method == 'GET':
		cur = get_db().cursor()
		for row in cur.execute("select * from dnats"):
			#do something

	elif request.method == 'POST':
		try:
			dport = request.form['dport']
			dst = request.form['dst']
			
			add_port_fwd(dport, dst)

			# delete rule into database
			cur = get_db().cursor()
			cur.execute('insert into port_fwd values (?,?)', (dport,dst,))
			return "succ"
		except Exception as e:
			return str(e)

	elif request.method == 'DELETE':
		try:
			dport = request.args.get('dport')
			dst = request.args.get('dst')

			del_port_fwd(dport, dst)

			cur = get_db().cursor()
			cur.execute('delete from dnat where dport=?', (dport,))
			return "succ"
		except Exception as e:
			return str(e)


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


if __name__ == "__main__":
	app.run()