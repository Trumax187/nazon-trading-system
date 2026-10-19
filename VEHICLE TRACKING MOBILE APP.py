# VEHICLE TRACKING MOBILE APP
congestion = 80
if congestion > 80:
    print("Avoid this road, it's highly congested!")
elif congestion > 65:
    print("This road is congested!")
elif congestion >= 40:
    print('This road is moderately congested!')
else:
    print('Use this road!')


Road_Name = 'Great East Road'
congestion_level = 70
if congestion_level > 90:
    print(f'{Road_Name} is highly congested. Use another road!')
elif congestion_level >= 60:
    print(f'{Road_Name} has moderate traffic but expect some delays!')
else:
    print(f'{Road_Name} is clear. You can use it!')

# Comparing two roads
Road1 = input('enter the road name 1: ')
congst1 = int(input('Enter the the congestion level in percentage: '))
Road2 = input('Enter the road name 2: ')
congst2 = int(input('Enter the congestion level in percentage: '))
Travel_time = int(input('Enter the travel time in minutes: '))
if congst1 > congst2:
    print(f'Use {Road2} is less congested than {Road1}!')
elif congst2 > congst1:
    print(f'Use {Road1} because it is less congested than {Road2}!')
else:
    print(f'Both roads {Road1} and {Road2} is congested and be cautious!')
print(f'Your travel time will be {Travel_time}')

