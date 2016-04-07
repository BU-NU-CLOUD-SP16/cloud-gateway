from flask import Flask, render_template, request
import subprocess
app = Flask(__name__)

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

@app.route("/iptables", methods=['GET', 'POST', 'PUT'])
def iptables():
	if request.method == 'POST':
		# Let request.form contain all the attributes required to append to the iptable
		# We can also add some sanity checks here
		return append_iptables(request.form)
	elif request.method == 'GET':
		return detail_iptables()
	elif request.method == 'PUT':
		return update_iptables(request.form)

# This returns the iptable
def detail_iptables():
	return subprocess.check_output('iptables', '-L', '-t', 'nat', shell=True) 

# This adds a new entry to the iptables
def append_iptables(form):
	# Earlier thoughts were writting directly to file but that is bound to have 
	# unwanted repurcussions
    # with open("/usr/local/bin/iptables", "w") as iptables:
    #     iptables.write('\n lorem ipsum..')
    source_add = form['source_add']
    dest_add   = form['dest_add']
    return subprocess.check_output('iptables', source_add, dest_add, shell=True) 

def update_iptables(form):
	pass

if __name__ == "__main__":
	app.run()