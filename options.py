import os
import argparse

file_dir = os.path.dirname(__file__)  # the directory that options.py resides in

class NetworkOptions:
	def __init__(self):
		self.parser = argparse.ArgumentParser(description="Network options")
		self.parser.add_argument(
			"--interface",
			type=str,
			default='127.0.0.1'
		)
		self.parser.add_argument(
			"--log_dir",
			type=str,
			help="log directory",
			default=os.path.join(os.path.expanduser("~"), "tmp")
		)
		self.parser.add_argument(
			"--server",
			type=str,
			default="127.0.0.1"
		)
		self.parser.add_argument(
			"--port",
			type=int,
			default=6890
		)
		

	def parse(self):
		self.options = self.parser.parse_args()
		return self.options
