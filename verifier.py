from linkage import Linkage
import math
import subprocess
import random

class Testor(object):
  def __init__(self, base="crab.txt", motor_link=(0, 1)):
    self.base = base
    self.motor_link = motor_link
    self.reload()

  def reload(self):
    self.linkage = Linkage()
    self.linkage.load(self.base)

  def nudge_vertex(self, i, delta):
    self.linkage.vertices[i] = (self.linkage.vertices[i][0] + delta[0], self.linkage.vertices[i][1] + delta[1])

  def nudge_angle(self, i, j, dtheta):
    # Nudge in azimuth bearing
    # i is held to be fixed.
    # j is nudged
    xi, yi = self.linkage.vertices[i]
    xj, yj = self.linkage.vertices[j]

    dx, dy = xj - xi, yj -  yi
    r = math.sqrt(dx**2 + dy**2)
    theta = math.atan2(dy, dx)
    theta = (-theta + math.pi / 2) % (2 * math.pi)
    theta += dtheta
    xj, yj = xi + r * math.sin(theta), yi + r * math.cos(theta)
    self.linkage.vertices[j] = (xj, yj)
    return theta

  def simulate(self):
    filename = "verify_linkage.%d.txt" % random.randint(0, 1000000000)
    print filename
    self.linkage.save(filename)
    p = subprocess.Popen(["python", "main.py", filename, "1", "1", str(self.motor_link[0]), str(self.motor_link[1])], stderr=subprocess.PIPE)

    found = 0
    stuck = 0
    while p.poll() is None:
      l = p.stderr.readline().strip() # This blocks until it receives a newline.
      if l == "CIRCLE FOUND":
        found += 1
      elif l == "STUCK?":
        stuck += 1

      if stuck >= 15:
        found = 0
        p.kill()

      if found >= 2:
        p.kill()

    return found >= 2


def length(a):
  return math.sqrt(a[0]**2 + a[1]**2)


from threading import Thread
from Queue import Queue

class SingleSimulation(Thread):
  def __init__(self, taskq, resultq, *args, **kwargs):
    Thread.__init__(self, *args, **kwargs)
    self.taskq = taskq
    self.resultq = resultq

  def run(self):
    while True:
      info, testor = self.taskq.get()
      success = testor.simulate()
      print info[0], info[1], success
      self.resultq.put((info[0], info[1], success))
      self.taskq.task_done()

def double_integration_threaded(fixed_vertex, moving_vertex):
  successmap = []

  original_linkage = Testor("crab.txt").linkage
  DTHETA = math.radians(10)
  DY = 10

  moving = original_linkage.vertices[moving_vertex]
  fixed = original_linkage.vertices[fixed_vertex]

  original_length = length((moving[0] - fixed[0], moving[1] - fixed[1]))
  current_length = 10
  all_failed = False
  while not (all_failed and current_length > original_length):
    print "current_length:", current_length
    taskq = Queue()
    resultq = Queue()
    for i in range(8):
      worker = SingleSimulation(taskq, resultq)
      worker.daemon = True
      worker.start()

    all_failed = True
    for i in xrange(36):
      testor = Testor("crab.txt")
      testor.linkage.vertices[moving_vertex] = list(testor.linkage.vertices[fixed_vertex])
      testor.linkage.vertices[moving_vertex][1] += current_length
      testor.linkage.vertices[moving_vertex] = tuple(testor.linkage.vertices[moving_vertex])
      testor.nudge_angle(fixed_vertex, moving_vertex, i * DTHETA)
      info = (current_length, i * DTHETA)
      taskq.put((info, testor))

    taskq.join()
    while not resultq.empty():
      l, angle, success = resultq.get()
      successmap.append((l, angle, success))
      if success:
        all_failed = False

    current_length += DY

  return successmap


def double_integration(fixed_vertex, moving_vertex):
  testor = Testor("crab.txt")
  successmap = []
  DELTA_THETA = math.radians(10)
  DELTA_Y = 5
  original_moving = testor.linkage.vertices[moving_vertex]
  original_l = length((original_moving[0] - testor.linkage.vertices[fixed_vertex][0], original_moving[1] - testor.linkage.vertices[fixed_vertex][1]))
  testor.linkage.vertices[moving_vertex] = list(testor.linkage.vertices[fixed_vertex])
  testor.linkage.vertices[moving_vertex][1] += DELTA_Y
  testor.linkage.vertices[moving_vertex] = tuple(testor.linkage.vertices[moving_vertex])

  i = 1
  print '"length","angle","success"'
  while True:
    last_theta = 0
    current_theta = 0
    l = length((testor.linkage.vertices[moving_vertex][0] - testor.linkage.vertices[fixed_vertex][0], testor.linkage.vertices[moving_vertex][1] - testor.linkage.vertices[fixed_vertex][1]))

    all_failed = True
    while not (1.5 * math.pi < last_theta <= 2 * math.pi and 0 < current_theta <= 0.5 * math.pi):
      success = testor.simulate()
      if success:
        all_failed = False
      successmap.append((l, current_theta, success))
      current_theta = testor.nudge_angle(fixed_vertex, moving_vertex, DELTA_THETA)
      print str(successmap[-1][0]) + "," + str(math.degrees(successmap[-1][1])) + "," + str(success)

    if all_failed and l > original_l:
      break

    i += 1
    testor.linkage.vertices[moving_vertex][1] = original_moving[1] + i * DELTA_Y
    testor.linkage.vertices[moving_vertex][0] = original_moving[0]

  return successmap

if __name__ == "__main__":
  print double_integration_threaded(0, 1)
