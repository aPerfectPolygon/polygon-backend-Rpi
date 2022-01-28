import base64
import os

from Cryptodome.Cipher import AES
from py3rijndael import RijndaelCbc

from UTILS.dev_utils.Objects import String


class customPadder:
	def __init__(self, block_size=16):
		self.block_size = block_size
	
	def pad(self, source: bytes) -> bytes:
		pad_len = self.block_size - len(source) % self.block_size
		return source + (bytes([pad_len]) * pad_len)
	
	@staticmethod
	def unpad(source: bytes) -> bytes:
		return source[0:-source[-1]]
	
	def encode(self, source: bytes) -> bytes:
		return self.pad(source)
	
	def decode(self, source: bytes) -> bytes:
		return self.unpad(source)


class Encryptions:
	class V1:
		slice_from = 2
		slice_len = 10
		key = '987fxvgklixfvzs56dvxgnhj69mdxfg5'
		padder = customPadder()
		
		def encrypt(self, message: str) -> str:
			"""
			Input String, return base64 encoded encrypted String
			"""
			# generate a random iv and prepend that to the encrypted result.
			# The recipient then needs to unpack the iv and use it.
			iv = os.urandom(AES.block_size)
			
			encrypted = AES.new(
				self.key.encode("UTF-8"),
				AES.MODE_CBC,
				iv
			).encrypt(
				self.padder.pad(
					message.encode("UTF-8")
				)
			)
			
			# Note we PREPEND the unencrypted iv to the encrypted message
			output = base64.b64encode(iv + encrypted).decode("UTF-8")
			output = f'{output[:self.slice_from]}{String.gen_random(self.slice_len)}{output[self.slice_from:]}'
			
			return output
		
		def decrypt(self, message: str) -> str:
			"""
			Input encrypted bytes, return decrypted bytes, using iv and key
			"""
			
			message = message[:self.slice_from] + message[self.slice_from + self.slice_len:]
			byte_array = base64.b64decode(message)
			
			iv = byte_array[0:16]  # extract the 16-byte initialization vector
			message_bytes = byte_array[16:]  # encrypted message is the bit after the iv
			cipher = AES.new(self.key.encode("UTF-8"), AES.MODE_CBC, iv)
			decrypted_padded = cipher.decrypt(message_bytes)
			decrypted = self.padder.unpad(decrypted_padded)
			
			return decrypted.decode("UTF-8")
	
	class Rijndael:
		def __init__(self, k, iv):
			self.k = base64.b64decode(k.encode('utf-8'))
			self.iv = base64.b64decode(iv.encode('utf-8'))
			# noinspection PyTypeChecker
			self.rjn = RijndaelCbc(self.k, self.iv, customPadder(32), 32)
		
		def encrypt(self, message: str) -> str:
			return base64.b64encode(self.rjn.encrypt(message.encode('utf-8'))).decode('utf-8')
		
		def decrypt(self, message: str) -> str:
			return self.rjn.decrypt(base64.b64decode(message.encode('utf-8'))).decode('utf-8')


if __name__ == '__main__':
	print(Encryptions.V1().decrypt(Encryptions.V1().encrypt('hello')))
