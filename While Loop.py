i = -20
while i <= 0:
    print(i)
    if i == -13:
        break
    i += 1

i = 0
while i > -20:
    i -= 1
    if i == -13:
        continue
    print(i)
else:
    print('-20 is greater than i!')