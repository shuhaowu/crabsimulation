import sys
import math
import numpy
from OpenGL.GL import *
from OpenGL.GLUT import *
from PIL import Image
import linkage

link = linkage.Linkage()
velocities = []
curVertex = -1
curEdge = -1
attractor = False
attractorCenterVertex = -1
attractorVertex = -1
attractorIncrementDirection = 1
attractorIncrementTheta = numpy.pi / 6
testInitTheta = None
testCurrentTheta = None
testLastTheta = None
testLast10ThetaDeltas = []
tracks = {}
view = 0
VIEWS = 8
info = 0
INFOS = 2
recording = -1

V_COEFF = 1
V_MAG = 1

VERTEX_SIZE = 10
LINE_WIDTH = 3
ANGLE_DIST = 25
VECTOR_LENGTH = 50
PICK_DIST2 = 100
ATTRACT_DIST2 = 25
TRACK_LENGTH = 1024
TRACK_DIST2 = 4


### from gamedev.net ###
def glEnable2D():
  vPort = glGetIntegerv(GL_VIEWPORT)
  glMatrixMode(GL_PROJECTION)
  glPushMatrix()
  glLoadIdentity()

  glOrtho(0, vPort[2], 0, vPort[3], -1, 1)
  glMatrixMode(GL_MODELVIEW)
  glPushMatrix()
  glLoadIdentity()

def glDisable2D():
  glMatrixMode(GL_PROJECTION)
  glPopMatrix()
  glMatrixMode(GL_MODELVIEW)
  glPopMatrix()


def drawString(x,y,font,str):
  glRasterPos2d(x,y)
  for c in str:
    glutBitmapCharacter(font,ord(c))

first = True
def display():
  global link, curVertex, curEdge, velocities, view, info, attractor, tracks, first, attractorVertex, attractorRadius
  glClearColor(1,1,1,1)
  glClear(GL_COLOR_BUFFER_BIT)
  glEnable2D()

  if info&1==0:
    glColor3f(0,0,0)
    drawString(50,50,GLUT_BITMAP_TIMES_ROMAN_10,'%d degrees of freedom'%len(velocities))

  glBegin(GL_LINES)
  for k in range(len(link.edges)):
    i,j = link.edges[k]
    if k==curEdge: glColor3f(1,0.3,1)
    else: glColor3f(1,0.3,0)
    x,y = link.vertices[i]
    glVertex2d(x,y)
    x,y = link.vertices[j]
    glVertex2d(x,y)
  glEnd()

  if view&4==0:
    glBegin(GL_LINES)
    glColor3f(1,0.7,0)
    for i,j,k in link.angles:
      x,y = link.vertices[i]
      v = link.vertices[j]
      w = link.vertices[k]
      dxj = v[0]-x
      dyj = v[1]-y
      dj = math.hypot(dxj,dyj)/ANGLE_DIST
      dxk = w[0]-x
      dyk = w[1]-y
      dk = math.hypot(dxk,dyk)/ANGLE_DIST
      glVertex2d(x+dxj/dj, y+dyj/dj)
      glVertex2d(x+dxk/dk, y+dyk/dk)
    glEnd()

  glColor3f(0,0.5,0)
  for track in tracks.values():
    glBegin(GL_LINE_STRIP)
    for (x,y) in track:
      glVertex2d(x,y)
    glEnd()

  if view&1==0:
    glBegin(GL_LINES)
    nv = len(velocities)
    for k in range(nv):
      v = VECTOR_LENGTH*velocities[k]
      glColor3f(0,(k+1)/float(nv),0)
      for i in range(len(link.vertices)):
        x,y = link.vertices[i]
        glVertex2d(x,y)
        glVertex2d(x+v[i,0],y+v[i,1])
    glEnd()

  glBegin(GL_POINTS)
  for i in range(len(link.vertices)):
    x,y = link.vertices[i]
    if i==curVertex: b=1
    else: b=0
    if i in link.fixed: r=1
    else: r=0
    if i in tracks: g=1
    else: g=0
    if not view&2 or i==curVertex:
      glColor3f(r,g,b)
      glVertex2d(x,y)
  glEnd()

  if attractor:
    glColor3f(0.5,0.5,0.5)
    glBegin(GL_POINTS)
    glVertex2d(attractor[0],attractor[1])
    glEnd()

  glDisable2D()
  glutSwapBuffers()

  if first:
    glutPostRedisplay()
    first = False

def pick(x,y):
  i = link.findVertex(x,y)
  if i>=0 and link.vertexDist2(x,y,i)<PICK_DIST2:
    return i,-1
  k = link.findEdge(x,y)
  if k>=0 and link.edgeDist2(x,y,k)<PICK_DIST2:
    return -1,k
  return -1,-1

def makeEdge(i,j):
  if i<j: return i,j
  return j,i

def makeAngle(i,j,k):
  if j<k: return i,j,k
  return i,k,j

def makeAngle2(i1,j1,i2,j2):
  if i1==i2: return makeAngle(i1,j1,j2)
  if i1==j2: return makeAngle(i1,j1,i2)
  if j1==i2: return makeAngle(j1,i1,j2)
  if j1==j2: return makeAngle(j1,i1,i2)

def mouse(button, state, x, y):
  global link, curVertex, curEdge, velocities, attractor, attractorVertex, attractorCenterVertex
  if state!=GLUT_UP: return

  # alt-clicking should count as middle button, but if it doesn't... then it does:
  if button==GLUT_LEFT_BUTTON and glutGetModifiers() & GLUT_ACTIVE_ALT:
    button = GLUT_MIDDLE_BUTTON

  vPort = glGetIntegerv(GL_VIEWPORT)
  y = vPort[3]-y
  if button==GLUT_LEFT_BUTTON:
    i,k = pick(x,y)
    if i>=0 or k>=0:
      if i==curVertex: i=-1 # clicking cur deselects
      if k==curEdge: k=-1
      curVertex,curEdge = i,k
      glutPostRedisplay()
    else:
      link.vertices.append((x,y))
      update()
  elif button==GLUT_MIDDLE_BUTTON:
    i,k = pick(x,y)
    if i>=0 and curVertex>=0 and i!=curVertex:
      edge = makeEdge(i,curVertex)
      if edge in link.edges:
        link.removeEdge( link.edges.index(edge) )
      else:
        link.edges.append(edge)
      update()
    elif k>=0 and curEdge>=0 and k!=curEdge:
      i1,j1 = link.edges[curEdge]
      i2,j2 = link.edges[k]
      angle = makeAngle2(i1,j1,i2,j2)
      if angle in link.angles:
        link.angles.remove(angle)
      elif angle!=None:
        link.angles.append(angle)
      update()
  elif button==GLUT_RIGHT_BUTTON:
    i, k = pick(x, y)
    if i >= 0:
      if i in (curVertex, attractorVertex):
        attractor = False
        attractorVertex, attractorCenterVertex = -1, -1
      else:
        attractor = link.vertices[i] # set the attractor to the vertex selected
        attractorCenterVertex = curVertex # set center to be the currently selected vertex
        attractorVertex = i

    glutPostRedisplay()

    # if attractor and ((attractor[0]-x)**2+(attractor[1]-y)**2)<PICK_DIST2:
    #   attractor = False
    # else: attractor = (x,y)
    # glutPostRedisplay()

def keyboard(key, x, y):
  global link, curVertex, curEdge, velocities, view, info, recording, tracks
  if key=='f' and curVertex>=0:
    if curVertex in link.fixed: link.fixed.remove(curVertex)
    else: link.fixed.append(curVertex)
    update()
  elif key=='t' and curVertex>=0:
    if curVertex in tracks: tracks.pop(curVertex)
    else: tracks[curVertex]=[]
    glutPostRedisplay()
  elif key=='d':
    if curVertex>=0:
      for i in tracks:
        if i==curVertex:
          tracks.pop(i)
        elif i>curVertex:
          tracks[i-1] = tracks.pop(i)
      link.removeVertex(curVertex)
      curVertex = -1
      update()
    elif curEdge>=0:
      link.removeEdge(curEdge)
      curEdge = -1
      update()
    elif key=='z':
      if curEdge>=0:
        i,j = link.edges[curEdge]
        link.removeEdge(curEdge) # TODO preserve the angles
        curEdge = -1
        u = link.vertices[i]
        v = link.vertices[j]
        link.vertices.append(((u[0] + v[0]) / 2,
                              (u[1] + v[1]) / 2))
        k = len(link.vertices) - 1
        link.edges.append(makeEdge(i, k))
        link.edges.append(makeEdge(j, k))
        curVertex = k
        update()
  elif key=='c':
    tracks = {}
    link.clear()
    update()
  elif key=='l':
    tracks = {}
    link.clear()
    link.load()
    stats = (len(link.vertices), len(link.fixed), len(link.edges), len(link.angles))
    print 'loaded %d vertices (%d fixed), %d edges, and %d angles'%stats
    update()
  elif key=='s':
    link.save()
    stats = (len(link.vertices), len(link.fixed), len(link.edges), len(link.angles))
    print 'saved %d vertices (%d fixed), %d edges, and %d angles'%stats
  elif key=='v':
    view = (view+1)%VIEWS
    glutPostRedisplay()
  elif key=='i':
    info = (info+1)%INFOS
    glutPostRedisplay()
  elif key=='m':
    if glutGameModeGet(GLUT_GAME_MODE_ACTIVE):
      glutLeaveGameMode()
      glutPostRedisplay()
    else:
      glutEnterGameMode()
      initWindow()
  elif key=='p':
    print 'printed window to file'
    screenshot()
  elif key=='r':
    if recording>=0:
      print 'recorded %d frames'%recording
      recording = -1
    else:
      print 'recording...'
      recording = 0


step = 0
def idle():
  global link,velocities,curVertex,attractor, recording, tracks, step, testCurrentTheta, testLastTheta, testLast10ThetaDeltas
  if not attractor or curVertex<0 or len(velocities)==0:
    return

  if recording>=0:
    screenshot('screenshot%04d.png'%recording)
    recording += 1

  x,y = link.vertices[attractorVertex]
  if step % 10 == 0:
    centerX, centerY = link.vertices[attractorCenterVertex]
    relativeX, relativeY = x - centerX, y - centerY
    r = numpy.sqrt(relativeX**2 + relativeY**2)

    theta = numpy.arctan2(relativeY, relativeX)
    theta -= attractorIncrementTheta
    if theta <= -numpy.pi:
      theta += 2 * numpy.pi
    attractor = (centerX + r * numpy.cos(theta), centerY + r * numpy.sin(theta))

    if testInitTheta is not None:
      if testCurrentTheta is None:
        testCurrentTheta = "start" # Skips first it
      else:
        # skips second iteration
        theta = numpy.arctan2(relativeY, relativeX)
        testCurrentTheta  = (-theta + numpy.pi / 2) % (2 * numpy.pi)
        if testLastTheta is not None:
          testLast10ThetaDeltas.append(((testCurrentTheta - testLastTheta) % (2 * numpy.pi)))
          if len(testLast10ThetaDeltas) > 10:
            testLast10ThetaDeltas.pop(0)
            if sum(testLast10ThetaDeltas) / len(testLast10ThetaDeltas) < 0.01:
              print "STUCK?"

          if testCurrentTheta < testLastTheta:
            if testLastTheta <= testInitTheta <= 2 * numpy.pi or 0 <= testInitTheta <= testCurrentTheta:
              print >> sys.stderr, "CIRCLE FOUND"
          else:
            if testLastTheta <= testInitTheta <= testCurrentTheta:
              print >> sys.stderr, "CIRCLE FOUND"


        testLastTheta = testCurrentTheta

  step += 1

  v0 = numpy.array([attractor[0]-x,attractor[1]-y])
  dv = numpy.dot(v0,v0)
  # if dv<ATTRACT_DIST2: # turn off attractor
  #  attractor = False
  #  glutPostRedisplay()
  #  return
  v0 = V_MAG*v0/numpy.sqrt(dv)
  for vel in velocities:
    v = vel[attractorVertex]
    c = numpy.dot(v0,v)/numpy.dot(v,v)
    c = max(-V_COEFF, min(V_COEFF, c)) #don't allow big coefficients
    v0 -= c*v
    for i in range(len(link.vertices)):
      x,y = link.vertices[i]
      link.vertices[i] = (x+c*vel[i,0],y+c*vel[i,1])

  for i in tracks:
    if len(tracks[i])==0 or link.vertexDist2(tracks[i][-1][0], tracks[i][-1][1], i)>TRACK_DIST2:
      tracks[i].append(link.vertices[i])
      while len(tracks[i])>TRACK_LENGTH:
        tracks[i].pop(0)

  update()

def update():
  global velocities
  velocities = link.computeRigidity()
  glutPostRedisplay()


def screenshot(path='screenshot.png',format='png'):
  vPort = glGetIntegerv(GL_VIEWPORT)
  glPixelStorei(GL_PACK_ALIGNMENT, 1)
  data = glReadPixelsub(0, 0, vPort[2], vPort[3], GL_RGB)
  image = Image.fromstring( "RGB", (vPort[2], vPort[3]), data.tostring() )
  image = image.transpose(Image.FLIP_TOP_BOTTOM)
  image.save(path,format)

def initWindow():
  glPointSize(VERTEX_SIZE)
  glLineWidth(LINE_WIDTH)
  glutDisplayFunc(display)
  glutMouseFunc(mouse)
  glutKeyboardFunc(keyboard)


def init(): #haha, definite
  global link, V_MAG, V_COEFF, attractorCenterVertex, attractorVertex, curVertex, testInitTheta, attractor, testCurrentTheta, testLastTheta
  if len(sys.argv)>=2: #<linkage-file>
    link.load(sys.argv[1])
    update()
  if len(sys.argv)>=3: #<step-size>
    V_MAG = float(sys.argv[2])
  if len(sys.argv)>=4: #<max-step>
    V_COEFF = float(sys.argv[3])

  if len(sys.argv) >= 5:
    attractorCenterVertex = int(sys.argv[4])
    curVertex = attractorCenterVertex
    attractorVertex = int(sys.argv[5])
    tracks[attractorVertex] = []
    attractor = link.vertices[attractorVertex]
    relative = numpy.array(link.vertices[attractorVertex]) - numpy.array(link.vertices[attractorCenterVertex])
    testInitTheta = numpy.arctan2(relative[1], relative[0])
    testInitTheta = (-testInitTheta + numpy.pi / 2) % (2 * numpy.pi)


if __name__ == "__main__":
  print >> sys.stderr, """usage: python main.py [<linkage-file> [<step-size=1> [<max-step=1>]]]
  click to add vertices
  click to (de)select a vertex and middle-click (alt-click) another vertex to add an edge
  click to (de)select an edge and middle-click (alt-click) an adjacent edge to fix their angle
  select a vertex and then right click another to add a counter clockwise motor
  press 'f' to fix the selected vertex
  press 't' to track the selected vertex
  press 'd' to delete the selected component
  press 'z' to split the selected edge at its midpoint
  press 'c' to clear everything away
  press 'l' to load from saved_linkage.txt
  press 's' to save to saved_linkage.txt
  press 'v' to cycle through viewing options
  press 'i' to toggle information display
  press 'm' to maximize/minimize to/from fullscreen
  press 'p' to print image to screenshot.png
  press 'r' to toggle motion recording to screenshot0000.png through screenshot9999.png"""

  glutInit(sys.argv)
  glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
  glutInitWindowSize(600, 600)
  glutCreateWindow('linkage')
  init()
  initWindow()
  glutIdleFunc(idle)
  glutMainLoop()
