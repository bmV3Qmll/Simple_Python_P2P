from server import Server
from options import NetworkOptions

options = NetworkOptions()
opts = options.parse()

if __name__ == "__main__":
	server = Server(opts)
	server.window.mainloop()
