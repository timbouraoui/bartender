import json
import os

file = open("pump_config.json", "r")
pump_list = json.load(file)
file.close()

# for key, value in pump_list.items():
#     for item in value:
#         print (item['name'])

# for pump in pump_list:
#     print (pump['pump_1'])

# for pump in pump_list:
#     print (pump_list[pump]['pin'])
drink_list = [
    {
        "name": "Rum & Coke",
        "ingredients": {
            "rum": 50,
            "coke": 150
        }
    }, {
        "name": "water",
        "ingredients": {
        }
    }, {
        "name": "Gin & Tonic",
        "ingredients": {
            "gin": 50,
            "tonic": 150
        }
    }, {
        "name": "Long Island",
        "ingredients": {
            "gin": 15,
            "rum": 15,
            "vodka": 15,
            "tequila": 15,
            "coke": 100,
            "oj": 30
        }
    }, {
        "name": "Screwdriver",
        "ingredients": {
            "vodka": 50,
            "oj": 150
        }
    }, {
        "name": "Margarita",
        "ingredients": {
            "tequila": 50,
            "mmix": 150
        }
    }, {
        "name": "Gin & Juice",
        "ingredients": {
                "gin": 50,
                "oj": 150
        }
    }, {
        "name": "Tequila Sunrise",
        "ingredients": {
            "tequila": 50,
            "oj": 150
        }
    }
]

for drink in drink_list:
    print(drink['name'])
    for ing in drink['ingredients']:
        print(drink['ingredients'][ing])