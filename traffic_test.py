from cereal import messaging

sm = messaging.SubMaster(['trafficLights'])

while True:
  sm.update(0)
  print(sm['trafficLights'].status)
  input()