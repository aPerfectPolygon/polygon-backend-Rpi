from UTILS.dev_utils.Objects import String
from UTILS.prj_utils import Encryptions as enc


class Encryptions:
	class V1(enc.Aes):
		def __init__(self):
			super().__init__('987fxvgklixfvzs56dvxgnhj69mdxfg5')
			self.slice_from = 2
			self.slice_len = 10
		
		def encrypt(self, message: str) -> str:
			output = super().encrypt(message)
			return f'{output[:self.slice_from]}{String.gen_random(self.slice_len)}{output[self.slice_from:]}'
		
		def decrypt(self, message: str) -> str:
			return super().decrypt(message[:self.slice_from] + message[self.slice_from + self.slice_len:])


if __name__ == '__main__':
	print(Encryptions.V1().decrypt(Encryptions.V1().encrypt('hello')))
