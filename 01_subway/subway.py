##
# TRACK 1
# One Train Two Tracks (datadrivendj.com/tracks/subway)
# Brian Foo (brianfoo.com)
# This file builds the sequence file for use with ChucK from the data supplied
##

# Library dependancies
import csv
import json
import math
import os
import random
import re
import time

# Config
BPM = 120 # 60, 75, 100, 120, 150
METERS_PER_BEAT = 75
DIVISIONS_PER_BEAT = 4
INSTRUMENTS_INPUT_FILE = 'data/instruments.csv'
STATIONS_INPUT_FILE = 'data/stations.csv'
REPORT_SUMMARY_OUTPUT_FILE = 'data/report_summary.csv'
REPORT_SEQUENCE_OUTPUT_FILE = 'data/report_sequence.csv'
INSTRUMENTS_OUTPUT_FILE = 'data/ck_instruments.csv'
SEQUENCE_OUTPUT_FILE = 'data/ck_sequence.csv'
JSON_OUTPUT_FILE = 'visualization/data/stations.json'
INSTRUMENTS_DIR = 'instruments/'
DO_INTRO = True
DO_OUTRO = True
WRITE_SEQUENCE = True
WRITE_REPORT = True
WRITE_JSON = True

# Calculations
BEAT_MS = round(60.0 / BPM * 1000)
ROUND_TO_NEAREST = round(BEAT_MS/DIVISIONS_PER_BEAT)

print('Building sequence at '+str(BPM)+' BPM ('+str(BEAT_MS)+'ms per beat)')

# Initialize Variables
instruments = []
stations = []
sequence = []

# Find index of first item that matches value
def findInList(list, key, value):
	found = -1
	for index, item in enumerate(list):
		if item[key] == value:
			found = index
			break
	return found

def roundToNearest(n, nearest):
	return 1.0 * round(1.0*n/nearest) * nearest

# Read instruments from file
with open(INSTRUMENTS_INPUT_FILE, 'rb') as f:
	r = csv.reader(f, delimiter='\t')
	next(r, None) # remove header
	for name,type,price,bracket_min,bracket_max,file,from_gain,to_gain,from_tempo,to_tempo,gain_phase,tempo_phase,active in r:
		if file and int(active):
			index = len(instruments)
			# build instrument object
			instrument = {
				'index': index,
				'name': name,
				'type': type.lower().replace(' ', '_'),
				'bracket_min': float(bracket_min),
				'bracket_max': float(bracket_max),
				'price': int(price),
				'file': INSTRUMENTS_DIR + file,
				'from_gain': round(float(from_gain), 1),
				'to_gain': round(float(to_gain), 1),
				'from_tempo': float(from_tempo),
				'to_tempo': float(to_tempo),
				'gain_phase': int(gain_phase),
				'tempo_phase': int(tempo_phase),
				'from_beat_ms': int(round(BEAT_MS/float(from_tempo))),
				'to_beat_ms': int(round(BEAT_MS/float(to_tempo)))
			}
			# add instrument to instruments
			instruments.append(instrument)

# Read stations from file
with open(STATIONS_INPUT_FILE, 'rb') as f:
	r = csv.reader(f, delimiter='\t')
	next(r, None) # remove header
	for name,income_annual,income,lat,lng,borough in r:
		index = len(stations)
		stations.append({
			'index': index,
			'name': name,
			'budget': float(re.sub(r'[\$|,]', '', income)),
			'percentile': 0.0,
			'lat': float(lat),
			'lng': float(lng),
			'beats': 0,
			'distance': 0,
			'duration': 0,
			'borough': borough,
			'borough_next': borough,
			'instruments': []
		})

# For calculating distance between two coords(lat, lng)
def distBetweenCoords(lat1, lng1, lat2, lng2):
	earthRadius = 6371000 # meters
	dLat = math.radians(lat2-lat1)
	dLng = math.radians(lng2-lng1)
	a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLng/2) * math.sin(dLng/2)
	c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
	dist = float(earthRadius * c)
	return dist

def getIncomePercentile(station, sorted_station_list):
	percentile = 0.0
	index = findInList(sorted_station_list, 'index', station['index'])
	if index >= 0:
		percentile = 1.0 * index / len(sorted_station_list) * 100
	return percentile

# Buy instruments based on a specified budget
def buyInstruments(station, instruments_shelf):
	budget = station['budget']
	percentile = station['percentile']
	instruments_cart = []
	for i in instruments_shelf:
		# skip if not in bracket
		if percentile < i['bracket_min'] or percentile >= i['bracket_max']:
			continue
		# add to cart if in budget
		elif i['price'] < budget:
			budget -= i['price']
			if i['type'] != 'placeholder':
				instruments_cart.append(i)
		# out of budget, finished
		else:
			break
	return instruments_cart

# Pre-process stations
min_distance = 0
max_distance = 0
total_distance = 0
total_beats = 0
total_ms = 0
min_duration = 0
max_duration = 0

# Create a list of stations sorted by budget
sorted_stations = stations[:]
sorted_stations = sorted(sorted_stations, key=lambda k: k['budget'])

# Loop through stations
for index, station in enumerate(stations):
	# determine station's income percentile
	stations[index]['percentile'] = getIncomePercentile(station, sorted_stations)
	# determine the station's instruments based on budget
	stations[index]['instruments'] = buyInstruments(stations[index], instruments)
	if index > 0:
		# determine distance between last station
		distance = distBetweenCoords(station['lat'], station['lng'], stations[index-1]['lat'], stations[index-1]['lng'])
		beats = int(round(distance / METERS_PER_BEAT))
		duration = beats * BEAT_MS
		stations[index-1]['distance'] = distance
		stations[index-1]['beats'] = beats
		stations[index-1]['duration'] = duration
		stations[index-1]['borough_next'] = station['borough']
		total_distance += distance
		total_beats += beats
		total_ms += duration
		if distance > max_distance:
			max_distance = distance
			max_duration = duration
		if distance < min_distance or min_distance == 0:
			min_distance = distance
			min_duration = duration

# Calculate how many beats
station_count = len(stations)-1
total_seconds = int(1.0*total_ms/1000)
seconds_per_station = int(1.0*total_seconds/station_count)

print('Total distance in meters: '+str(round(total_distance)))
print('Distance range in meters: ['+str(min_distance)+','+str(max_distance)+']')
print('Average beats per station: '+str(1.0*total_beats/station_count))
print('Average time per station: '+time.strftime('%M:%S', time.gmtime(seconds_per_station)))
print('Main sequence beats: '+str(total_beats))
print('Main sequence time: '+time.strftime('%M:%S', time.gmtime(total_seconds)) + '(' + str(total_seconds) + 's)')

# Multiplier based on sine curve
def getMultiplier(percent_complete):
	radians = percent_complete * math.pi
	multiplier = math.sin(radians)
	if multiplier < 0:
		multiplier = 0.0
	elif multiplier > 1:
		multplier = 1.0
	return multiplier

# Retrieve gain based on current beat
def getGain(instrument, beat):
	beats_per_phase = instrument['gain_phase']
	percent_complete = float(beat % beats_per_phase) / beats_per_phase
	multiplier = getMultiplier(percent_complete)
	from_gain = instrument['from_gain']
	to_gain = instrument['to_gain']
	gain = multiplier * (to_gain - from_gain) + from_gain
	gain = round(gain, 2)
	return gain

# Get beat duration in ms based on current point in time
def getBeatMs(instrument, beat, round_to):	
	from_beat_ms = instrument['from_beat_ms']
	to_beat_ms = instrument['to_beat_ms']
	beats_per_phase = instrument['tempo_phase']
	percent_complete = float(beat % beats_per_phase) / beats_per_phase
	multiplier = getMultiplier(percent_complete)
	ms = multiplier * (to_beat_ms - from_beat_ms) + from_beat_ms
	ms = int(roundToNearest(ms, round_to))
	return ms

# Add beats to sequence
def addBeatsToSequence(instrument, duration, ms, beat_ms, round_to):
	global sequence
	previous_ms = int(ms)
	from_beat_ms = instrument['from_beat_ms']
	to_beat_ms = instrument['to_beat_ms']
	min_ms = from_beat_ms if from_beat_ms < to_beat_ms else to_beat_ms
	remaining_duration = int(duration)
	elapsed_duration = 0
	while remaining_duration >= min_ms:
		elapsed_ms = int(ms)
		elapsed_beat = int((elapsed_ms-previous_ms) / beat_ms)
		this_beat_ms = getBeatMs(instrument, elapsed_beat, round_to)		
		sequence.append({
			'instrument_index': instrument['index'],
			'position': 0,
			'gain': getGain(instrument, elapsed_beat),
			'rate': 1,
			'elapsed_ms': elapsed_ms
		})
		remaining_duration -= this_beat_ms
		elapsed_duration += this_beat_ms
		ms += this_beat_ms

# Build intro sequence
global_ms = 0
intro_duration = 0
ding_i = findInList(instruments, 'name', 'Subway Ding')
dong_i = findInList(instruments, 'name', 'Subway Dong')
if DO_INTRO and ding_i >= 0 and dong_i >= 0:
	# Add curved ding-dong to sequence
	ding = instruments[ding_i]
	dong = instruments[dong_i]
	intro_duration = 0.5 * ding['tempo_phase'] * BEAT_MS
	addBeatsToSequence(ding, intro_duration, global_ms, BEAT_MS, 1)
	dong_offset = 0.5 * ding['from_beat_ms']
	addBeatsToSequence(dong, intro_duration - dong_offset, dong_offset, BEAT_MS, 1)	
	# Add linear ding-dong to sequence
	ding['from_beat_ms'] = BEAT_MS
	dong['from_beat_ms'] = BEAT_MS
	ding['to_gain'] = 0.0
	dong['to_gain'] = 0.0
	ding_dong_beats = int(ding['gain_phase'] / 2)
	addBeatsToSequence(ding, BEAT_MS * ding_dong_beats, intro_duration - BEAT_MS * 0.5, BEAT_MS, 1)
	addBeatsToSequence(dong, BEAT_MS * ding_dong_beats, intro_duration - BEAT_MS * 0.5, BEAT_MS, 1)
	global_ms = intro_duration - BEAT_MS * 1.5
	total_ms += global_ms
	intro_duration = global_ms

# Build main sequence
for instrument in instruments:
	ms = int(global_ms)
	station_queue_duration = 0
	if instrument['type'] == 'misc':
		continue
	# Each station in stations
	for station in stations:
		# Check if instrument is in this station
		instrument_index = findInList(station['instruments'], 'index', instrument['index'])
		# Instrument not here, just add the station duration and continue
		if instrument_index < 0 and station_queue_duration > 0:
			addBeatsToSequence(instrument, station_queue_duration, ms, BEAT_MS, ROUND_TO_NEAREST)
			ms += station_queue_duration + station['duration']
			station_queue_duration = 0
		elif instrument_index < 0:
			ms += station['duration']
		else:
			station_queue_duration += station['duration']
	if station_queue_duration > 0:
		addBeatsToSequence(instrument, station_queue_duration, ms, BEAT_MS, ROUND_TO_NEAREST)

# Build outro sequence
global_ms = total_ms
if DO_OUTRO and ding_i >= 0 and dong_i >= 0:
	ding = instruments[ding_i]
	dong = instruments[dong_i]
	# Add ding and dong to sequence
	sequence.append({
		'instrument_index': ding['index'],
		'position': 0,
		'gain': max([ding['from_gain'], ding['to_gain']]),
		'rate': 1,
		'elapsed_ms': global_ms
	})
	global_ms += BEAT_MS
	sequence.append({
		'instrument_index': dong['index'],
		'position': 0,
		'gain': max([dong['from_gain'], dong['to_gain']]),
		'rate': 1,
		'elapsed_ms': global_ms
	})
	total_ms += BEAT_MS * 2

total_seconds = int(1.0*total_ms/1000)
print('Total sequence time: '+time.strftime('%M:%S', time.gmtime(total_seconds)) + '(' + str(total_seconds) + 's)')
		
# Sort sequence
sequence = sorted(sequence, key=lambda k: k['elapsed_ms'])

# Add milliseconds to sequence
elapsed = 0
for index, step in enumerate(sequence):
	sequence[index]['milliseconds'] = step['elapsed_ms'] - elapsed
	elapsed = step['elapsed_ms']

# Write instruments to file
if WRITE_SEQUENCE:
	with open(INSTRUMENTS_OUTPUT_FILE, 'wb') as f:
		w = csv.writer(f)	
		for index, instrument in enumerate(instruments):
			w.writerow([index])
			w.writerow([instrument['file']])
		f.seek(-2, os.SEEK_END) # remove newline
		f.truncate()
		print('Successfully wrote instruments to file: '+INSTRUMENTS_OUTPUT_FILE)

# Write sequence to file
if WRITE_SEQUENCE:
	with open(SEQUENCE_OUTPUT_FILE, 'wb') as f:
		w = csv.writer(f)	
		for step in sequence:
			w.writerow([step['instrument_index']])
			w.writerow([step['position']])
			w.writerow([step['gain']])
			w.writerow([step['rate']])
			w.writerow([step['milliseconds']])
		f.seek(-2, os.SEEK_END) # remove newline
		f.truncate()
		print('Successfully wrote sequence to file: '+SEQUENCE_OUTPUT_FILE)

# Write summary file
if WRITE_REPORT:
	with open(REPORT_SUMMARY_OUTPUT_FILE, 'wb') as f:
		w = csv.writer(f)
		w.writerow(['Time', 'Name', 'Distance', 'Duration', 'Beats', 'Instruments'])
		elapsed = intro_duration
		for station in stations:
			duration = station['duration']
			duration_f = time.strftime('%M:%S', time.gmtime(int(duration/1000)))
			elapsed_f = time.strftime('%M:%S', time.gmtime(int(elapsed/1000)))
			elapsed += duration
			w.writerow([elapsed_f, station['name'], round(station['distance'], 2), duration_f, station['beats'], ' '.join([i['name'] for i in station['instruments']])])
		print('Successfully wrote summary file: '+REPORT_SUMMARY_OUTPUT_FILE)

# Write sequence report to file
if WRITE_REPORT:
	with open(REPORT_SEQUENCE_OUTPUT_FILE, 'wb') as f:
		w = csv.writer(f)
		w.writerow(['Time', 'Instrument', 'Gain'])
		for step in sequence:
			instrument = instruments[step['instrument_index']]
			elapsed = step['elapsed_ms']
			elapsed_f = time.strftime('%M:%S', time.gmtime(int(elapsed/1000)))
			ms = elapsed % 1000
			elapsed_f += '.' + str(ms)
			w.writerow([elapsed_f, instrument['file'], step['gain']])
		f.seek(-2, os.SEEK_END) # remove newline
		f.truncate()
		print('Successfully wrote sequence report to file: '+REPORT_SEQUENCE_OUTPUT_FILE)

# Write JSON data for the visualization
if WRITE_JSON:
	json_data = []
	elapsed_duration = 0
	for station in stations:
		json_data.append({
			'name': station['name'],
			'borough': station['borough'].upper(),
			'borough_next': station['borough_next'].upper(),
			'duration': station['duration'],			
			'elapsed_duration': elapsed_duration,
			'min_duration': min_duration
		})
		elapsed_duration += station['duration']
	with open(JSON_OUTPUT_FILE, 'w') as outfile:
		json.dump(json_data, outfile)
	print('Successfully wrote to JSON file: '+JSON_OUTPUT_FILE)
