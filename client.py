import os
from socket import *
import json
import pickle
import re
import shutil
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
from tkinter.filedialog import askopenfilename, asksaveasfilename
from threading import *

class Client:
	def __init__(self, options):
		''' Configuring server based on provided arguments
		'''
		self.opt = options
		self.server = self.opt.server
		self.serverport = self.opt.serverport
		self.interface = self.opt.interface

		''' Network components
		'''
		self.semaphore = Semaphore()
		self.clientSocket = socket(AF_INET, SOCK_DGRAM)
		self.peerSocket = socket(AF_INET, SOCK_STREAM)
		self.clientSocket.bind((self.interface, self.opt.clientport))
		self.clientSocket.settimeout(1)

		''' Connect to server
		'''
		print("Initiate connection to server.")
		serverResp = self.sendUDP(["initiate", gethostname()])
		if serverResp is None:
			print("Connection failed.")		
			exit()
		else:
			self.port = serverResp
			self.peerSocket.bind((self.interface, self.port))
		
		''' GUI components
		'''
		# Window object
		self.window = tk.Tk()
		self.window.title("File sharing client")
		self.window.geometry("550x420")
		self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

		# hostname
		self.l1 = tk.Label(self.window, text="Hostname:")
		self.l1.place(x=20, y=20)
		self.l2 = tk.Label(self.window, text=gethostname())
		self.l2.place(x=120, y=20)

		# port
		self.lp = tk.Label(self.window, text="Port:")
		self.lp.place(x=240, y=20)
		self.lp1 = tk.Label(self.window, text=str(self.port))
		self.lp1.place(x=280, y=20)

		# publish
		self.selectBtn = tk.Button(self.window, text="Select file:", border=1, width=12, command=self.open)
		self.selectBtn.place(x=20, y=60)
		self.publishBtn = tk.Button(self.window, text="Publish as:", border=1, width=12, command=self.publish)
		self.publishBtn.place(x=340, y=60)
		self.lnameEntry = ttk.Entry(self.window, width=30)
		self.fnameEntry = ttk.Entry(self.window, width=15)
		self.lnameEntry.place(x=120, y=60)
		self.fnameEntry.place(x=440, y=60)

		# search
		self.searchFileBtn = tk.Button(self.window, text="Search", border=1, width=12, command=self.search)
		self.searchFileBtn.place(x=20, y=100)
		self.file_nameEntry = ttk.Entry(self.window, width=15)
		self.file_nameEntry.place(x=120, y=100)

		
		# list of search files
		self.fileArea = tk.Frame(self.window, background="white")
		self.fileArea.place(x=20, y=140)
		self.scroll = ttk.Scrollbar(self.fileArea)
		self.listbox = tk.Listbox(
			self.fileArea,
			yscrollcommand=self.scroll.set,
			width=80,
			height=5,
			borderwidth=0,
			selectmode="single"
		)
		self.scroll.pack(side="right", fill="y")
		self.listbox.pack(side="left", padx=5, pady=5)

		# output repo
		self.showListFile = tk.Button(self.window, text="List repo", border=1, width=12, command=self.repo)
		self.showListFile.place(x=20, y=240)
		self.listfile = tk.Frame(self.window, background="white")
		self.listfile.place(x=20, y=280)
		self.scroll1 = ttk.Scrollbar(self.listfile)
		self.listbox1 = tk.Listbox(
			self.listfile,
			yscrollcommand=self.scroll1.set,
			width=80,
			height=5,
			selectmode="single",
		)
		self.scroll1.pack(side="right", fill="y")
		self.listbox1.pack(side="left", padx=5, pady=5)

		# fetch
		self.fetchBtn = tk.Button(self.window, text="Fetch:", border=1, width=12, command=self.fetch)
		self.fetchBtn.place(x=20, y=380)
		self.lc = tk.Label(self.window, text="From:")
		self.lc.place(x=240, y=380)
		self.filenameEntry = ttk.Entry(self.window, width=15)
		self.peerportEntry = ttk.Entry(self.window, width=15)
		self.filenameEntry.place(x=120, y=380)
		self.peerportEntry.place(x=280, y=380)
		
		# Start a TCP server for listening to other clients
		Thread(target=self.serveTCP, daemon=True).start()

	def sendUDP(self, msg):
		for i in range(4):
			self.clientSocket.sendto(pickle.dumps(msg), (self.server, self.serverport))
			try:
				resp, _ = self.clientSocket.recvfrom(2048)
				return pickle.loads(resp)
			except timeout:
				continue
		return None

	def open(self):
		filepath = askopenfilename(filetypes=[("All Files", "*.*")])
		if not filepath:
			return
		self.lnameEntry.delete(0, tk.END)
		self.lnameEntry.insert(0, filepath)
		self.fnameEntry.delete(0, tk.END)
		self.fnameEntry.insert(0, filepath.split('/')[-1])

	def copy_file_to_repo(self, source, to_dir, fname):
		choice = "0"
		if not os.path.exists(to_dir):
			os.makedirs(to_dir)

		if os.path.isfile(source) and os.path.isdir(to_dir):
			if fname in os.listdir(to_dir):
				choice = messagebox.askquestion(
					"File Name Conflict",
					"File name already exists. Do you want to overwrite it?",
				)
				if choice == "yes":
					print("Overwriting file...")
				elif choice == "no":
					idx = 1
					while fname in os.listdir(to_dir):
						split_name = fname.rsplit(".", 1)
						match = re.search(r"\_\((\d+)\)$", split_name[0])
						if match:
							idx = int(match.group(1))
							fname = (
								re.sub(r"\_\((\d+)\)$", f"_({idx+1}).", split_name[0])
								+ split_name[1]
							)
						else:
							fname = split_name[0] + f"_(1)." + split_name[1]
						idx += 1
				else:
					print("Invalid choice. Please try again.")
			shutil.copy(source, os.path.join(to_dir, fname))
			return [True, fname, choice]
		else:
			return [False, fname, choice]

	def publish(self):
		fname = self.fnameEntry.get()
		lname = self.lnameEntry.get()
		if lname != "" and fname != "":
			repo_path = os.path.join(os.getcwd(), "repo")
			repo_path = repo_path.replace(os.path.sep, "/")
			result = self.copy_file_to_repo(lname, repo_path, fname)
			if not result[0]:
				messagebox.showerror("Error", "Your file path or file name is wrong! Please try again!")
			else:
				resp = self.sendUDP(["publish", gethostname(), result[1], result[2]])
				if resp == "File Registered Successfully.":
					messagebox.showinfo("Successfully published", "Successfully published")
				else:
					messagebox.showerror("Error", resp)
		else:
			messagebox.showerror("Error", "Missing value")

	def search(self):
		file_name = self.file_nameEntry.get()
		if file_name != "":
			data = self.sendUDP(["search", file_name, self.port])
			self.listbox.delete(0, tk.END)
			str = "Host_name       Port       File_name"
			self.listbox.insert(tk.END, str)
			for item in data:
				text = f"   {item['host_name']}           {item['host_port']}        {item['file_name']}"
				self.listbox.insert(tk.END, text)

	def repo(self):
		data = self.sendUDP(["repo", gethostname()])
		self.listbox1.delete(0, tk.END)
		str = "            File_name"
		self.listbox1.insert(tk.END, str)
		for item in data:
			text = f"              {item['file_name']} "
			self.listbox1.insert(tk.END, text)

	def fetch(self):
		filename = self.filenameEntry.get()
		hostname = self.peerportEntry.get()
		if filename == "" or hostname == "":
			messagebox.showerror("Error", "Missing value")
			return

		host_info = self.sendUDP(["get_host", hostname])
		if host_info == "HOST_NOT_FOUND":
			messagebox.showerror("Error", "Host not found! Please try again!")
			return

		try:
			conn = socket(AF_INET, SOCK_STREAM)
			conn.connect((host_info["addr"], int(host_info["port"])))
		except:
			messagebox.showerror("Error", f"Host: {hostname} is not online! Please try again!")
			return
		Thread(target=self.fetchFile, args=(conn, filename, ), daemon=True).start()

	def fetchFile(self, conn, filename):
		conn.send(pickle.dumps(["fetch", filename]))
		data = conn.recv(1024)
		if data == "FILE_NOT_FOUND".encode():
			messagebox.showerror("Error", "File not found! Please try again!")
			return

		download_path = os.path.join(os.getcwd(), "downloads")
		download_path = download_path.replace(os.path.sep, "/")
		if not os.path.exists(download_path):
			os.makedirs(download_path)

		# Handle for duplicate file name
		if filename in os.listdir(download_path):
			idx = 1
			while filename in os.listdir(download_path):
				split_name = filename.rsplit(".", 1)
				match = re.search(r"\_\((\d+)\)$", split_name[0])
				if match:
					idx = int(match.group(1))
					filename = (
						re.sub(r"\_\((\d+)\)$", f"_({idx+1}).", split_name[0])
						+ split_name[1]
					)
				else:
					filename = split_name[0] + f"_(1)." + split_name[1]
				idx += 1
		with open(os.path.join(download_path, filename), "wb") as download_file:
			while True:
				data = conn.recv(1024)
				if not data:
					download_file.close()
					break
				download_file.write(data)
		conn.close()
		print("The file is downloaded to your repository")
		messagebox.showinfo("Successfully fetched", "Successfully fetched")

	def serveTCP(self):
		self.peerSocket.listen()
		while True:
			connectionSocket, _ = self.peerSocket.accept()
			Thread(target=self.transmit, args=(connectionSocket, ), daemon=True).start()

	def transmit(self, conn):
		request = pickle.loads(conn.recv(1024))
		if request[0] == "fetch":
			repo_path = os.path.join(os.getcwd(), "repo")
			file_name = request[1]
			file_path = os.path.join(repo_path, file_name)
			
			if not os.path.exists(file_path):
				conn.send("FILE_NOT_FOUND".encode())
			else:
				conn.send("OK".encode())
				with open(file_path, "rb") as sharing_file:
					while True:
						data = sharing_file.read(1024)
						if not data:
							sharing_file.close()
							conn.close()
							break
						conn.send(data)
				print("The file has been sent successfully")

	def on_closing(self):
		if messagebox.askokcancel("Quit", "Do you want to quit?"):
			self.window.destroy()
			os._exit(0)