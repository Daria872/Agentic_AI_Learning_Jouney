#Creating a class in python
class Microwave:
  ...

#Creating an object smeg which is an instance of a class
smeg: Microwave=Microwave()


#With initialisers
class Microwave:
  #defining a function
  def __init__(self, brand: str, power_rating: str):
    #The name self can be changed
    self.brand=brand
    self.power_rating=power_rating

smeg: Microwave=Microwave("Cooker",6.78)
print(smeg)
print(smeg.brand)
print(smeg.power_rating)

# Creating a class in python
class Microwave:
    def __init__(self, brand: str, power_rating: float) -> None:
        self.brand = brand
        self.power_rating = power_rating
        self.turn_on = False

    def turnOn(self) -> None:
        if self.turn_on:
            print(f"Microwave {self.brand} is already turned on")
        else:
            self.turn_on = True
            print(f"Microwave {self.brand} is now turned on")

    def turnOff(self) -> None:
        if self.turn_on:
            self.turn_on = False
            print(f"Microwave {self.brand} is now off")
        else:
            print("Microwave is already turned off")

    def run(self, seconds: int) -> None:
        if self.turn_on:
            print(f"The microwave {self.brand} is running for {seconds} secs")
        else:
            print("Microwave is turned off")


#Dunder methods are special methods in Python with double underscores before and after their names, like str, add, and len. They let your class behave like built-in Python objects.
class Book:
    def __init__(self, title, pages):
        self.title = title
        self.pages = pages

    def __str__(self):
        return f"Book({self.title}, {self.pages} pages)"

    def __len__(self):
        return self.pages

    def __add__(self, other):
        return self.pages + other.pages


b1 = Book("Python Basics", 200)
b2 = Book("OOPs", 150)

print(str(b1))   # Book(Python Basics, 200 pages)
print(len(b1))   # 200
print(b1 + b2)   # 350

# Creating an instance of the class (added '=')
smeg = Microwave("Bosch", 6.78)

print(smeg.brand)
print(smeg.power_rating)

smeg.turnOn()
smeg.run(56)   # Runs successfully
smeg.turnOff()
 
  