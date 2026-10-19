# LOOPS
# WHILE LOOP RUNS CONTINUOUSLY
count = 0  # start counter
while count < 5: # if condition is TRUE... the code will run
    print('Checking traffic...') # will output Checking traffic for 5 times
    count += 1 # increasing count by one and it terminates the execution else it will run forever

# INFINITE LOOP (REAL SYSTEMS USE THIS)
while True:
    print('Monitoring traffic...') # This runs forever
    break # this stops the code to run forever

while True:
    road = input('Enter road name (or type "exit"): ')
    if road == 'exit': # stops when the user enters EXIT
        print('System stopped!')
        break # stops the infinite while loop
congestion = int(input('Enter congestion level: '))
if congestion > 70:
    print('Avoid this road!')
else:
    print('Road is usable!')

 # FOR LOOPS IS FOR FIXED NUMBER OF ITERATIONS
for i in range(4): # wil keep running for 4 times but 4 will not be included
    print('Checking Road...', i)