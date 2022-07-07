import pandas as pd


x = pd.DataFrame([[1, 10, 11], [2, 21, 22]], columns=['id_l', 'd1', 'd2'])
y = pd.DataFrame([[1, 12, 13], [3, 15, 16]], columns=['id_r', 'd1', 'd4'])

print(x)
print(y)

z = pd.merge(x, y, left_on='id_l', right_on='id_r')
print(z)

