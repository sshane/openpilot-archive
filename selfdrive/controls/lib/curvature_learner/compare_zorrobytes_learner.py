learned_offset = 0
learning_rate = 50

CURVE_DIRECTION = 'left'
if CURVE_DIRECTION == 'left':
  lat_pos = 0.5
  angle_steers = 5
else:
  lat_pos = -0.5
  angle_steers = -5

direction = 'left' if lat_pos > 0 else 'right'

HUGGING_DIRECTION = 'right'
if HUGGING_DIRECTION == 'left':
  d_poly = [0, 0, 0, -0.5]
else:
  d_poly = [0, 0, 0, 0.5]

if angle_steers > 0.1:
  print('wheel angled left')
  learned_offset -= d_poly[3] / learning_rate
  offset = learned_offset

elif angle_steers < -0.1:
  print('wheel angled right')
  learned_offset += d_poly[3] / learning_rate
  offset = learned_offset

print('zorrobyte\'s learned_offset: {}'.format(learned_offset))  # todo: shouldnt't curv factor be negative for oversteering? not positive?

if direction == 'left':  # fixme: originally right, but left makes curv factor negative when oversteering and positive when understeering
  d_poly[3] = -d_poly[3]  # d_poly's sign switches for oversteering in different directions
learned_offset = 0
learned_offset -= d_poly[3] / learning_rate

print('new learned_offset: {}'.format(learned_offset))
