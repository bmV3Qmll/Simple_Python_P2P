import os
from socket import *
import json
import pickle
import platform # For getting the operating system name
import subprocess # For executing a shell command
from datetime import datetime
from threading import Thread, Semaphore
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
import sys
import collections

class Server:
	def __init__(self, options):
		''' Configuring server based on provided arguments
		'''
		self.opt = options
		if not os.path.exists(self.opt.log_dir):
			os.makedirs(self.opt.log_dir)
		self.log_file = os.path.join(self.opt.log_dir, 'opt.json')
		self.host = self.opt.server
		self.port = self.opt.serverport
		
		with open(self.log_file, 'w') as f:
			json.dump(self.opt.__dict__.copy(), f, indent=4)
		
		''' Inner datastructures
		'''
		self.files = []
		self.clientHost = []
		self.clientMetaData = ["name", "addr", "port"]
		self.fileMetaData = ["host_name", "host_port", "file_name", "date_added"]
		self.semaphore = Semaphore()

		''' GUI components
		'''
		# Window object
		self.window = tk.Tk()
		self.window.title("File sharing server")
		self.window.geometry("550x800")
		self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

		# discover
		self.discoverBtn = tk.Button(self.window, text="Discover:", border=1, width=12, command=self.discover)
		self.discoverBtn.place(x=20, y=20)
		self.host_nameEntry = ttk.Entry(self.window, width=15)
		self.host_nameEntry.place(x=120, y=20)

		self.list = tk.Frame(self.window, background="white")
		self.list.place(x=20, y=60)
		self.scroll = ttk.Scrollbar(self.list)
		self.listbox = tk.Listbox(
			self.list,
			yscrollcommand=self.scroll.set,
			width=80,
			height=10,
			borderwidth=0,
			selectmode="single"
		)
		self.scroll.pack(side="right", fill="y")
		self.listbox.pack(side="left", padx=5, pady=5)

		# list
		self.listBtn = tk.Button(self.window, text="List Host Name", border=1, width=12, command=self.listHost)
		self.listBtn.place(x=20, y=260)

		self.list1 = tk.Frame(self.window, background="white")
		self.list1.place(x=20, y=300)
		self.scroll1 = ttk.Scrollbar(self.list1)
		self.listbox1 = tk.Listbox(
			self.list1,
			yscrollcommand=self.scroll1.set,
			width=80,
			height=10,
			borderwidth=0,
			selectmode="single"
		)
		self.scroll1.pack(side="right", fill="y")
		self.listbox1.pack(side="left", padx=5, pady=5)

		# ping
		self.pingBtn = tk.Button(self.window, text="Ping", border=1, width=12, command=self.ping)
		self.pingBtn.place(x=20, y=500)
		self.host_nameEntryi = ttk.Entry(self.window, width=15)
		self.host_nameEntryi.place(x=120, y=500)

		self.list2 = tk.Frame(self.window, background="white")
		self.list2.place(x=20, y=540)
		self.scroll2 = ttk.Scrollbar(self.list2)
		self.listbox2 = tk.Listbox(
			self.list2,
			yscrollcommand=self.scroll2.set,
			width=80,
			height=5,
			borderwidth=0,
			selectmode="single"
		)
		self.scroll2.pack(side="right", fill="y")
		self.listbox2.pack(side="left", padx=5, pady=5)

		''' Open a new thread for listening to connection
		'''
		listener = Thread(target=self.run,
						  daemon=True)
		listener.start()

	def run(self):
		serverSocket = socket(AF_INET, SOCK_DGRAM)
		serverSocket.bind((self.host, self.port))
		print("The server is on.")
		
		while True:
			req, client_addr = serverSocket.recvfrom(2048)
			req = pickle.loads(req)
			message_type = req[0]
			if message_type == "initiate":
				print("Client", client_addr[0], "connects to the server")
				self.semaphore.acquire()
				dup = False
				clientPort = 6891
				for i, host in enumerate(self.clientHost):
					if req[1] == host["name"]:
						dup = True
						clientPort = host["port"]
						break
				if not dup:
					if len(self.clientHost) != 0:
						clientPort = self.clientHost[-1]["port"] + 1
					self.clientHost.append(dict(zip(self.clientMetaData, (req[1], client_addr[0], clientPort))))
				serverSocket.sendto(pickle.dumps(clientPort), client_addr)
				self.semaphore.release()

			elif message_type == "publish":
				print("Host", req[1], "want to share file")
				self.semaphore.acquire()
				reply = "File Registered Successfully."
				port = 0
				for host in self.clientHost:
					if host["name"] == req[1]:
						port = host["port"]
						break
				if port == 0:
					reply = "Client hasn't Registered."
				else:
					# choice for rename or overwrite: '1' for overwrting , '2' for auto rename
					choice = req[3]
					if choice == "yes":
						# overwriting, so we need to find file and change the datetime
						for record in self.files:
							if record["host_name"] == req[1] and record["file_name"] == req[2]:
								record["date_added"] = str(datetime.now())
								break
					else:
						self.files.insert(0, dict(zip(self.fileMetaData, [req[1], port, req[2], str(datetime.now())])))
				serverSocket.sendto(pickle.dumps(reply), client_addr)
				self.semaphore.release()

			elif message_type == "search":
				file_name = req[1]
				print("Client", client_addr[0], "search for file", file_name)
				self.semaphore.acquire()
				search_result = []
				for record in self.files:
					if record["file_name"].find(file_name) != -1:
						search_result.append(record)
				serverSocket.sendto(pickle.dumps(search_result), client_addr)
				self.semaphore.release()

			elif message_type == "repo":
				self.semaphore.acquire()
				file_list = self.list_files_in_repo(req[1])
				serverSocket.sendto(pickle.dumps(file_list), client_addr)
				self.semaphore.release()

			elif message_type == "get_host":
				self.semaphore.acquire()
				found = False
				for host in self.clientHost:
					if host["name"] == req[1]:
						serverSocket.sendto(pickle.dumps(host), client_addr)
						found = True
						break
				if not found:
					serverSocket.sendto(pickle.dumps("HOST_NOT_FOUND"), client_addr)
				self.semaphore.release()

	def list_files_in_repo(self, hostname):
		file_list = []
		if [hostname == host["name"] for host in self.clientHost]:
			for file in self.files:
				if file["host_name"] == hostname:
					file_data = [
						file["host_name"],
						file["host_port"],
						file["file_name"],
						file["date_added"]
					]
					file_list.append(dict(zip(self.fileMetaData, file_data)))
			return file_list
		return "404"

	def search_addr(self, hostname):
		for host in self.clientHost:
			if host["name"] == hostname:
				return host["addr"]
		return "404"

	def discover(self):
		hname = self.host_nameEntry.get()
		if hname != "":
			data = self.list_files_in_repo(hname)
			if data == "404":
				messagebox.showerror(title="WARNING", message="Hostname not found!")
				return
			self.listbox.delete(0, tk.END)
			str = "Host_name                Port              File_name                      Date_added"
			self.listbox.insert(tk.END, str)
			for item in data:
				text = f"     {item['host_name']}                  {item['host_port']}               {item['file_name']}            {item['date_added']}"
				self.listbox.insert(tk.END, text)

	def ping(self):
		pname = self.host_nameEntryi.get()
		if pname != "":
			addr = self.search_addr(pname)
			if addr == "404":
				messagebox.showerror(title="WARNING", message="Hostname not found!")
				return
			self.listbox2.delete(0, tk.END)
			param = "-n" if platform.system().lower() == "windows" else "-c"
			command = ["ping", param, "1", addr]
			out = f'Host_name: {pname} , IP: {addr} , Status: '.encode()
			try:
				out += subprocess.check_output(command)
				for res in addr:
					self.listbox2.insert(tk.END, out)
			except:
				self.listbox2.insert(tk.END, "Host: {pname} is not online.")

	def listHost(self):
		all_hosts = [host["name"] for host in self.clientHost]
		self.listbox1.delete(0, tk.END)
		str = "        Host_name"
		self.listbox1.insert(tk.END, str)
		for item in all_hosts:
			text = f"             {item}"
			self.listbox1.insert(tk.END, text)

	def on_closing(self):
		if messagebox.askokcancel("Quit", "Do you want to quit?"):
			self.window.destroy()
			os._exit(0)
