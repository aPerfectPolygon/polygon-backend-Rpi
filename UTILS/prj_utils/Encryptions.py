import base64
import os

from Cryptodome.Cipher import AES
from py3rijndael import RijndaelCbc

from UTILS.dev_utils.Objects import String


class customPadder:
	def __init__(self, block_size=16):
		self.block_size = block_size
	
	def encode(self, source: bytes) -> bytes:
		pad_len = self.block_size - len(source) % self.block_size
		return source + (bytes([pad_len]) * pad_len)
	
	@staticmethod
	def decode(source: bytes) -> bytes:
		return source[0:-source[-1]]


class Aes:
	def __init__(self, k: str):
		self.k = k
		self.padder = customPadder()
	
	def encrypt(self, message: str) -> str:
		# generate a random iv and prepend that to the encrypted result The recipient then needs to unpack the iv and use it.
		iv = os.urandom(AES.block_size)
		
		encrypted = AES.new(
			self.k.encode("UTF-8"),
			AES.MODE_CBC,
			iv
		).encrypt(
			self.padder.encode(
				message.encode("UTF-8")
			)
		)
		
		# Note we PREPEND the unencrypted iv to the encrypted message
		return base64.b64encode(iv + encrypted).decode("UTF-8")
	
	def decrypt(self, message: str) -> str:
		byte_array = base64.b64decode(message)
		
		return self.padder.decode(
			AES.new(
				self.k.encode("UTF-8"),
				AES.MODE_CBC,
				byte_array[0:16]
			).decrypt(byte_array[16:])
		).decode("UTF-8")


class Rijndael:
	def __init__(self, k, iv):
		self.k = base64.b64decode(k.encode('utf-8'))
		self.iv = base64.b64decode(iv.encode('utf-8'))
		self.rjn = RijndaelCbc(self.k, self.iv, customPadder(32), 32)
	
	def encrypt(self, message: str) -> str:
		return base64.b64encode(self.rjn.encrypt(message.encode('utf-8'))).decode('utf-8')
	
	def decrypt(self, message: str) -> str:
		return self.rjn.decrypt(base64.b64decode(message.encode('utf-8'))).decode('utf-8')
