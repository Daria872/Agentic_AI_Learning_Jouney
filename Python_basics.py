#Import statements
import math
import math as m
from math import sqrt

print(math.sqrt(56))
print(m.sqrt(64))
print(sqrt(65))

print("-------------------------------------------------------------------------")

#Basic python print statement
print('Hello World')

#Print statement for variable
name='Arul'
print('Hello, '+name)

#Data types in python
id=1
name='Madhavi'
ispresent=False
marks=97.2
coordinates=(1.0,2.0) #tuples
names=['A','B','C'] #list
unique={'A','B','B','C'} #set--> we can insert duplicates but while printing duplicates are automatically neglected
print(unique)
users={'A':1,'B':2,'C':3} #Dictionary

#Type conversion
s='12'
print(10+int(s))

#Type annotations--> explicitly defining the data type of the variable
#Format:- variable-name:data type=value name
age: int =10
name: str='Raghav'

#F-strings--> To format string
name='Raghav'
age=21
print(f"Name: {name} , Age: {age}")

#Functions

#specifying the data members along with their types
def func(a: int, b: int)->float: #-> signifies thr return type as float
  return a+b
#Calling the function
print(func(10,20))

#No return type
def func(greeting: str, name: str)->None:
  print(f'{name} welcomed by {greeting}')

func('Charles','Nameste')

#Looping
#Simple for loop
print('--------------------------------------------------------------------------')
for i in range(5):
  print(i)

#Iterating over a collection
print('--------------------------------------------------------------------------')
lis=["A","B","C","D"]
for ch in lis:
  print(ch)

#while loop
print('--------------------------------------------------------------------------')
i=0
while i<5:
  print(i)
  i+=1

print('--------------------------------------------------------------------------')
a=34
b=70
print(a<b)
print(a<=b)
print(a==b)

print('--------------------------------------------------------------------------')
user_input=input()
if user_input=='Hello':
  print("Bot: Hi!")
elif user_input=='How are you?':
  print("Bot: I'm good")
else:
  print("Bot: Sorry, couldn't understand")


print('--------------------------------------------------------------------------')
try:
  a,b=10
  print(a+b)
except TypeError as e: 
  print(f"Enter a valid argument")

  