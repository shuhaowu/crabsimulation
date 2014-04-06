from linkage import Linkage
import math
import subprocess


class Testor(object):
  def __init__(self, base="crab.txt", motor_link=(0, 1)):
    self.base = base
    self.motor_link = motor_link
    self.reload()

  def reload(self):
    self.linkage = Linkage()
    self.linkage.load(self.base)

  def nudge_vertex(self, i, delta):
    self.linkage.vertices[i] = (self.linkage.vertices[i][0] + delta[0], self.linkage.vertices[i][1][1])

  def nudge_angle(self, i, j, dtheta):
    # Nudge in azimuth bearing
    # i is held to be fixed.
    # j is nudged
    xi, yi = self.linkage.vertices[i]
    xj, yj = self.linkage.vertices[j]

    dx, dy = xj - xi, yj -  yi
    r = math.sqrt(dx**2, dy**2)
    theta = math.atan2(dy, dx)
    theta = (-theta + math.pi / 2) % (2 * math.pi)
    theta += dtheta
    xj, yj = r * math.sin(theta), r * math.cos(theta)
    self.linkage.vertices[j] = (xj, yj)

  def simulate(self):
    self.linkage.save("verify_linkage.txt")
    p = subprocess.Popen(["python", "main.py", "verify_linkage.txt", "1", "1", str(self.motor_link[0]), str(self.motor_link[1])], stderr=subprocess.PIPE)

    found = 0
    while p.poll() is None:
      l = p.stderr.readline().strip() # This blocks until it receives a newline.
      if l == "CIRCLE FOUND":
        found += 1

      if found >= 2:
        p.kill()

    return found >= 2

def test():
  testor = Testor()
  print testor.simulate()



if __name__ == "__main__":
  test()