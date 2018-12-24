from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Coffee, CoffeeItem, User

engine = create_engine('sqlite:///coffee.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Create dummy user
user = User(name="Areej", email="areej.moh26@hotmail.com")
session.add(user)
session.commit()

# Create ARNW Coffee
typeOfCoffee_1 = Coffee(user_id=1, name="ARNW Coffee")
session.add(typeOfCoffee_1)
session.commit()

Item_1 = CoffeeItem(user_id=1, name="Reno", description="It is a coffee mixed with a special ARNW coffee",
                             price=30, coffee=typeOfCoffee_1)
session.add(Item_1)
session.commit()


# Create Hot Coffee
typeOfCoffee_2 = Coffee(user_id=1, name="Hot Coffee")
session.add(typeOfCoffee_2)
session.commit()

Item_1 = CoffeeItem(user_id=1, name="Cappuccino", description="The hot cappuccino is prepared from American coffee with fresh milk",
                             price=15, coffee=typeOfCoffee_2)
session.add(Item_1)
session.commit()

# Create Ice Coffee
typeOfCoffee_3 = Coffee(user_id=1, name="Ice Coffee")
session.add(typeOfCoffee_3)
session.commit()

Item_1 = CoffeeItem(user_id=1, name="Latte", description="Cold coffee mixture with fresh milk",
                             price=18, coffee=typeOfCoffee_3)
session.add(Item_1)
session.commit()

# Create Fresh Drinks
typeOfCoffee_4 = Coffee(user_id=1, name="Fresh Drinks")
session.add(typeOfCoffee_4)
session.commit()

Item_1 = CoffeeItem(user_id=1, name="Apple juice", description="It is the juice extracted from imported fresh apples daily",
                             price=10, coffee=typeOfCoffee_4)

session.add(Item_1)
session.commit()


print "added items successfully!"
