#!/bin/python
import fileinput
import json

for line in fileinput.input():
   event = json.loads(line)
   series = event['series']
   revision = event['parameters']['revision']
   print("series %d (rev %d)" % (series, revision))
