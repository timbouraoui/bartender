import time
import os
import sys
import RPi.GPIO as GPIO
import json
import logging
import threading
import traceback
from flask import Flask
from flask_ask import Ask, request, session, question, statement
from enum import Enum

from drinks import drink_list

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# stepper pins
PIN_STP = 26
PIN_DIR = 19
PIN_MS1 = 13
PIN_MS2 = 5
PIN_EN = 6

#sensor pins
PIN_TRIG = 17
PIN_ECHO = 18

PIN_ENDSTOP = 2

class cup_status(Enum):
	ABSENT = 1
	PRESENT = 2
	FILLED = 3

class Table:
	def __init__(self, PIN_STP, PIN_DIR, PIN_MS1, PIN_MS2, PIN_EN, PIN_TRIG, PIN_ECHO, PIN_ENDSTOP):
		# steps per cup location
		self.stepper_constant = 50
		# distance from US sensor
		self.CUP_DIST = 10

		# constants for stepper motor direction
		self.FORWARD = GPIO.HIGH
		self.BACKWARD = GPIO.LOW

		self.pin_stp = PIN_STP
		self.pin_dir = PIN_DIR
		self.pin_ms1 = PIN_MS1
		self.pin_ms2 = PIN_MS2
		self.pin_en = PIN_EN

		self.pin_trig = PIN_TRIG
		self.pin_echo = PIN_ECHO

		self.pin_endstop = PIN_ENDSTOP

		GPIO.setup(self.pin_stp, GPIO.OUT)
		GPIO.setup(self.pin_dir, GPIO.OUT)
		GPIO.setup(self.pin_ms1, GPIO.OUT)
		GPIO.setup(self.pin_ms2, GPIO.OUT)
		GPIO.setup(self.pin_en, GPIO.OUT)
		GPIO.setup(self.pin_trig, GPIO.OUT)
		GPIO.setup(self.pin_echo, GPIO.IN)
		GPIO.setup(self.pin_endstop, GPIO.IN)

		# GPIO.output(self.pin_stp, GPIO.LOW)
		# GPIO.output(self.pin_dir, FORWARD)
		# GPIO.output(self.pin_ms1, GPIO.LOW)
		# GPIO.output(self.pin_ms2, GPIO.LOW)
		# GPIO.output(self.pin_en, GPIO.HIGH)

		self.cups=[cup_status.ABSENT, cup_status.ABSENT, cup_status.ABSENT,
					cup_status.ABSENT, cup_status.ABSENT, cup_status.ABSENT]
		self.current_table_location = 0

	# determines if there is a cup present based on distance
	def cup_present(self):
		if distance() < self.CUP_DIST: return True
		else: return False

	# finds distance of object in front of ultrasonic sensor
	def distance(self):
		# set Trigger to HIGH
		GPIO.output(self.pin_trig, True)

		# set Trigger after 0.01ms to LOW
		time.sleep(0.00001)
		GPIO.output(self.pin_trig, False)

		StartTime = time.time()
		StopTime = time.time()

		# save StartTime
		while GPIO.input(self.pin_echo) == 0:
			StartTime = time.time()

		# save time of arrival
		while GPIO.input(pin_echo) == 1:
			StopTime = time.time()

		# time difference between start and arrival
		TimeElapsed = StopTime - StartTime
		# multiply with the sonic speed (34300 cm/s)
		# and divide by 2, because there and back
		distance = (TimeElapsed * 34300) / 2

		return distance

	# uses the US sensor to fill the list self.cups with the locations of the cups
	def find_cup_locations(self):
		for cup_location in range(6):
			set_table_location(cup_location)
			if cup_present() and cups[cup_location] != cup_status.FILLED:
				cups[cup_location] = cup_status.PRESENT

	# count the number of cups in the list self.cups
	def find_num_present_cups(self):
		count = 0
		for cup in self.cups:
			if cup == cup_status.PRESENT: count += 1
		return count

	# rotates the table backward until the endstop is clicked
	def home_table(self):
		while not GPIO.input(self.pin_endstop):
			step_backward()
		self.current_table_location = 0

	# rotates the table to the desires location
	def set_table_location(self, new_location):
		if new_location >= 6: new_location = new_location % 6

		location_diff = new_location - self.current_table_location
		if location_diff == 0:
			return 0
		elif location_diff < 0:
			self.move_backward(-1*location_diff)
		else:
			self.move_forward(location_diff)

		self.current_table_location = new_location

	# rotates the table forward one step
	def step_forward(self):
		GPIO.output(self.pin_dir, self.FORWARD)
		GPIO.output(self.pin_stp, False)
		GPIO.output(self.pin_stp, True)

	# rotates the table forward a select number of cup_locations
	def move_forward(self, num_spots):
		for i in range(num_spots*self.stepper_constant):
			step_forward(self)

	# rotates the table backwards one step
	def step_backward(self):
		GPIO.output(self.pin_dir, self.BACKWARD)
		GPIO.output(self.pin_stp, False)
		GPIO.output(self.pin_stp, True)

	# rotates the table backward a select number of cup locations
	def move_backward(self, num_spots):
		for i in range(num_spots*self.stepper_constant):
			step_backward(self)

class Bartender:
	def __init__(self, Table):
		self.PRIMING_DIST = 50
		self.CLEANING_DIST = 200
		self.FLOW_RATE = 60.0/100.0
		self.MAX_PUMPS = 8

		self.pump_list = {}
		self.current_menu = []

		self.load_pump_list()
		self.init_pump_gpios

		self.my_table = Table

	# load in pumps and ingredients from json
	def load_pump_list(self):
		file = open('pump_config.json', 'r')
		self.pump_list = json.load(file)
		file.close()

	# setup pump pins as gpio outputs
	def init_pump_gpios(self):
		for pump in self.pump_list:
			GPIO.setup(self.pump_list[pump]['pin'], GPIO.OUT)

	# update pump when switching over to ingredient
	def update_pump(self, pump_id, ingredient):
		prev_ingredient = ''
		if pump_id > 0 & pump_id <= self.MAX_PUMPS:
			for pump in self.pump_list:
					if self.pump_list[pump]['id'] == pump_id:
						prev_ingredient = self.pump_list[pump]['ingredient']
						self.pump_list[pump]['ingredient'] = ingredient

			file = open('pump_config.json', 'w')
			json.dump(self.pump_list, file)
			file.close()

		return prev_ingredient

		# primes all pumps - might have to do this sequentially instead of in parallel because of current issues

	# cleans a single pump
	def clean_pump(self, pump_id, cup_location):
		self.my_table.set_table_location(cup_location-1)

		for pump in self.pump_list:
			if self.pump_list[pump]['id'] == pump_id:
				self.pour(self.pump_list[pump]['pin'], self.CLEANING_DIST)

	# cleans all pumps
	def clean_all_pumps(self, cup_location):
		self.my_table.set_table_location(cup_location-1)

		pumpThreads = []
		for pump in self.pump_list:
			pump_t = threading.Thread(target=self.pour, args=(self.pump_list[pump]['pin'], self.cLEANING_DIST*self.FLOW_RATE))
			pumpThreads.append(pump_t)

		# start the pump threads
		for thread in pumpThreads:
			thread.start()

		# wait for threads to finish
		for thread in pumpThreads:
			thread.join()

	# primes all pumps - might have to do this sequentially instead of in parallel because of current issues
	def prime_all_pumps(self, cup_location):
		self.my_table.set_table_location(cup_location-1)

		pumpThreads = []
		for pump in self.pump_list:
			pump_t = threading.Thread(target=self.pour, args=(self.pump_list[pump]['pin'], self.PRIMING_DIST*self.FLOW_RATE))
			pumpThreads.append(pump_t)

		# start the pump threads
		for thread in pumpThreads:
			thread.start()

		# wait for threads to finish
		for thread in pumpThreads:
			thread.join()

	# primes a single pump
	def prime_pump(self, pump_id, cup_location):
		self.my_table.set_table_location(cup_location-1)

		for pump in self.pump_list:
			if self.pump_list[pump]['id'] == pump_id:
				self.pour(self.pump_list[pump]['pin'], self.PRIMING_DIST)

	#adds drinks from drink_list to the menu if all ingredients are hooked up to the pump
	def build_menu(self, drink_list):
		self.current_menu = []
		for drink in drink_list:
			drink_flag = 1
			for ingredient in drink['ingredients']:
				ingredient_flag = 0
				for pump in self.pump_list:
					if ingredient == self.pump_list[pump]['ingredient']:
						ingredient_flag = 1
				if not ingredient_flag: drink_flag = 0
			if drink_flag:	self.current_menu.append(drink)

	def make_drink(self, drink, cup_location):
		self.my_table.set_table_location(cup_location)

		pumpThreads = []
		for ingredient in drink['ingredients']:
			for pump in self.pump_list:
				if ingredient == self.pump_list[pump]['ingredient']:
					pump_t = threading.Thread(target=self.pour, args=(self.pump_list[pump]['pin'], drink['ingredients'][ingredient]*self.FLOW_RATE))
					pumpThreads.append(pump_t)

		# start the pump threads
		for thread in pumpThreads:
			thread.start()

		# wait for threads to finish
		for thread in pumpThreads:
			thread.join()

		my_table.cups[cup_location] = cup_status.FILLED

	def pour(self, pin, amount):
		GPIO.output(pin, GPIO.HIGH)
		time.sleep(amount)
		GPIO.output(pin, GPIO.LOW)

app = Flask(__name__)
ask = Ask(app, '/')
logging.getLogger('flask_ask').setLevel(logging.DEBUG)

my_table = Table(PIN_STP, PIN_DIR, PIN_MS1, PIN_MS2, PIN_EN, PIN_TRIG, PIN_ECHO, PIN_ENDSTOP)
my_bartender = Bartender(my_table)

# What's on the menu?
@ask.intent('MenuInquiry')
def menu_inquiry():
	my_bartender.build_menu(drink_list)
	my_statement = 'The following drinks are available '
	for drink in my_bartender.current_menu:
		my_statement = my_statement + drink['name'] + ', '
	return statement(my_statement)

# What ingredients do we have?
@ask.intent('IngredientInquiry')
def ingredient_inquiry():
	my_statement = 'The following ingredients are currently hooked up to the pumps. '
	for i in range(1, my_bartender.MAX_PUMPS+1):
		for pump in my_bartender.pump_list:
			if my_bartender.pump_list[pump]['id'] == i:
				my_statement = my_statement + my_bartender.pump_list[pump]['name'] + ' is ' + my_bartender.pump_list[pump]['ingredient'] + '. '
	return statement(my_statement)

# 'Connect pump 3 to whiskey'
@ask.intent('UpdatePump', convert={'pump_id':int})
def update_pump(pump_id):
	ingredient = request.intent.slots.ingredient.resolutions.resolutionsPerAuthority[0]['values'][0]['value']['id']
	prev_ingredient = my_bartender.update_pump(pump_id, ingredient)
	return statement('You\'ve changed pump {} from {} to {}'.format(pump_id, prev_ingredient, ingredient))

# used when filled cups are taken from the table
@ask.intent('ThankYou')
def thank_you():
	for cup in my_bartender.my_table.cups:
		if cup == cup_status.FILLED: cup = cup_status.ABSENT

# make quantity amount of drink drinks if there are cups present - shouldn't make drinks unless there are drinks present
@ask.intent('DrinkRequest')
def drink_request(drink, quantity):
	drank = {}
	my_statement = 'I have finished making the following. '
	for my_drink in drink_list:
		if my_drink['name'] == drink: drank = my_drink

	my_bartender.my_table.home_table()

	# if there are enough PRESENT cups
	if my_bartender.my_table.find_num_present_cups() >= quantity:
		for index, cup in enumerate(my_bartender.my_table.cups):
			if cup == cup_status.PRESENT:
				my_bartender.make_drink(drank, index)
				my_statement = my_statement + 'A {} in cup number {}'.format(drank['name'], index)
	# attempt to find new PRESENT cups
	else:
		my_bartender.my_table.find_cup_locations()
		if my_bartender.my_table.find_num_present_cups() >= quantity:
			for index, cup in enumerate(my_bartender.my_table.cups):
				if cup == cup_status.PRESENT:
					my_bartender.make_drink(drank, index)
					my_statement = my_statement + 'A {} in cup number {}'.format(drank['name'], index)
		else:
			return statement('There are not enough empty cups on the plate. If you see empty cups on the plate, try saying "thank you" to let me know you\'ve grabbed the previous drinks')
	my_statement = my_statement + ' Enjoy!'
	return statement(my_statement)

if __name__ == "__main__":
	app.config['ASK_VERIFY_REQUESTS'] = False
	app.run(debug=True)

	while True:
		x = input('What you tryna do')

		if x == '1':
			print(menu_inquiry())

	GPIO.cleanup()
