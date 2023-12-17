from client import Client
from options import NetworkOptions

options = NetworkOptions()
opts = options.parse()

if __name__ == "__main__":
	client = Client(opts)
	client.window.mainloop()
