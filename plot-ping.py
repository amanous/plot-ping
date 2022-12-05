#!/usr/bin/env python3

import subprocess
import sys
import time
import socket
from ipaddress import ip_address
import random
import os
from argparse import ArgumentParser

from PyQt5.QtWidgets import QApplication, QWidget, QProgressBar, QLineEdit
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt

__HISTORY_BARS = 20
__SCALE = 500.0 # in ms
__WARN_ABOVE = 50 # in ms
__INTERVAL = 1.0
# placement
__PL_WIDTH  = 3840
__PL_HEIGHT = 2160

def add_history_point(hist, color):
  p = QPalette()
  p.setColor(QPalette.Background, color)
  b = QWidget()
  b.setPalette(p)
  b.setAutoFillBackground(True);
  if hist.count() == __HISTORY_BARS:
    hist.removeWidget(hist.itemAt(0).widget())
  hist.addWidget(b)

def window_init(do_bar = True, do_gw = None):
  width = 120
  hist_height = 40
  app = QApplication([])

  # top widget
  top = QWidget()
  top.setWindowTitle('plot-ping-window')
  top.setWindowFlags(Qt.WindowStaysOnTopHint)
  top.setAttribute(Qt.WA_X11NetWmWindowTypeDock)

  # ping text label
  textbox_label = QLineEdit(top)
  textbox_label.setFrame(False)
  textbox_label.setReadOnly(True)
  textbox_label.setAlignment(Qt.AlignHCenter)
  textbox_label.setFont(QFont('Arial', 20))
  textbox_label.setText('Target')
  textbox_label.setMaximumWidth(width)
  # ping text rtt  
  textbox = QLineEdit(top)
  textbox.setFrame(False)
  textbox.setReadOnly(True)
  textbox.setAlignment(Qt.AlignHCenter)
  textbox.setFont(QFont('Arial', 24))
  textbox.setText('')
  textbox.setMaximumWidth(width)
  # ping history
  hist = QHBoxLayout()
  hist.setDirection(QHBoxLayout.LeftToRight)
  hist.setSpacing(0)
  hist.setContentsMargins(0, 0, 0, 0) # left, top, right, bottom
  hist_w = QWidget()
  hist_w.resize(width, hist_height)
  hist.addWidget(hist_w)

  # ping bar
  if do_bar:
    bar = QProgressBar(top)
    bar.setTextVisible(False)
    bar.setValue(0)
    bar.setMaximum(__SCALE)
    bar.setMinimum(0)
    bar.setMaximumWidth(width)
  else:
    bar = None

  if do_gw:
    # ping gw text label
    textbox_label_gw = QLineEdit(top)
    textbox_label_gw.setFrame(False)
    textbox_label_gw.setReadOnly(True)
    textbox_label_gw.setAlignment(Qt.AlignHCenter)
    textbox_label_gw.setFont(QFont('Arial', 20))
    textbox_label_gw.setText('Gateway')
    textbox_label_gw.setMaximumWidth(width)
    textbox_gw = QLineEdit(top)
    textbox_gw.setFrame(False)
    textbox_gw.setReadOnly(True)
    textbox_gw.setAlignment(Qt.AlignHCenter)
    textbox_gw.setFont(QFont('Arial', 24))
    textbox_gw.setText('')
    textbox_gw.setMaximumWidth(width)
    hist_gw = QHBoxLayout()
    hist_gw.setDirection(QHBoxLayout.LeftToRight)
    hist_gw.setSpacing(0)
    hist_gw.setContentsMargins(0, 0, 0, 0) # left, top, right, bottom
    hist_gw_w = QWidget()
    hist_gw_w.resize(width, hist_height)
    hist_gw.addWidget(hist_gw_w)
  else:
    textbox_gw = None
    hist_gw = None

  # top widget layout
  l = QVBoxLayout()
  l.setDirection(QVBoxLayout.TopToBottom)
  l.setSpacing(5)
  l.setContentsMargins(3, 5, 3, 5) # left, top, right, bottom

  extra_height = 0

  if do_bar:
    l.addWidget(bar)

  l.addWidget(textbox_label)
  l.addWidget(textbox)
  l.addLayout(hist)
  extra_height += hist.itemAt(0).widget().height()

  if do_gw:
    l.addWidget(textbox_label_gw)
    l.addWidget(textbox_gw)
    l.addLayout(hist_gw)
    extra_height += hist_gw.itemAt(0).widget().height()

  w_width = l.maximumSize().width()
  w_height = l.minimumSize().height() + extra_height
  top.setLayout(l)
  top.resize(w_width, w_height)
  # placement : 5 pixels from the bottom right corner
  top.setGeometry(__PL_WIDTH - w_width, __PL_HEIGHT - w_height - 5,
                  w_width, w_height)
  top.show()
  app.sendPostedEvents()
  app.processEvents()
  #app.exec_()
  return (app, top, bar, textbox, textbox_gw, hist, hist_gw)

# 0,255 -> 255,255 : green to yellow
# 255,255 -> 255,0 : yellow to red
def rtt_to_colour_gradient(rtt, max_val = __SCALE):
  if type(rtt) != int:
    return QColor(0, 0, 0)

  if rtt * 1.0 >= max_val:
    return QColor(255, 0, 0) # == Qt.red

  v = rtt * 1.0 * 512 / max_val
  if v >= 256:
    return QColor(255, int(255-(v-256)), 0)
  else:
    return QColor(int(v), 255, 0)

def rtt_to_colour_simple(rtt):
  if type(rtt) == int:
    return Qt.green if rtt <= __WARN_ABOVE else QColor(255, 153, 0)
  else:
    return Qt.red

def window_draw(window, rtt, do_bar = True, rtt_gw = None, ttl_gw = None):
  app, top, bar, textbox, textbox_gw, hist, hist_gw = window
  textvalue = rtt if type(rtt) == int else 0
  palette = QPalette()
  palette.setColor(QPalette.Base, rtt_to_colour_simple(rtt))
  if do_bar:
    bar.setValue(textvalue)
  textbox.setText(str(rtt))
  textbox.setPalette(palette)
  add_history_point(hist, rtt_to_colour_gradient(rtt))
  if textbox_gw:
    textbox_gw.setText(str(rtt_gw))
  if hist_gw:
    palette_gw = QPalette()
    palette_gw.setColor(QPalette.Base, rtt_to_colour_simple(rtt_gw))
    textbox_gw.setPalette(palette_gw)
    add_history_point(hist_gw, rtt_to_colour_gradient(rtt_gw))
  app.sendPostedEvents()
  app.processEvents()

def get_con_bars(ms, max_col):
  if type(ms) == str:
    return ''
  con_bars = int((ms / __SCALE) * max_col)
  if con_bars > max_col:
    return (max_col - 1) * '-' + '+'
  else:
    return con_bars * '-'

def get_prefix(dst, ms, ttl):
  t_str = time.strftime("%H:%M:%S")
  s = "%s %3s %3s ttl" % (t_str, dst, str(ttl))
  if type(ms) == int:
    return s + " %5s ms " % (str(ms))
  else:
    return s + " %5s    " % (str(ms))

def make_dead():
  dead = [
    ' :-( ',
    ' :-\ ',
    ' :-/ '
  ]
  def get_dead():
    dead.insert(0, dead.pop(-1))
    return dead[0]
  return get_dead

def get_gw(target):
  args = ["/bin/ip", "route", 'get', target]
  p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  ipr_out, ipr_err = p.communicate()
  output = str(ipr_out).strip().split()
  if len(output) > 3 and output[1] == 'via':
    return output[2]
  return None

def do_resolve(target_dns):
  print('resolving', target_dns)
  target_ip = socket.gethostbyaddr(target_dns)[-1][0]
  print('resolved', target_dns, '->', target_ip)
  return target_ip

def do_ping(target):
  args = ["/bin/ping", "-n", '-w', '1', '-c', '1', target]
  p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  ping_out, ping_err = p.communicate()
  output = ping_err.strip()
  for line in str(ping_out, 'UTF-8').split("\n"):
    l = str(line).split()
    if len(l) > 6 and l[6].startswith('time='):
      #print(l)
      ms = int(l[6][5:].split('.')[0])
      ttl = int(l[5].split('=')[1])
      return ms, ttl
  raise RuntimeError('ping failed')


def main():
  rows, columns = map(int, os.popen('stty size', 'r').read().split())
  max_col = columns - len(get_prefix('', 0,0))

  parser = ArgumentParser(prog = 'gmailtool')
  parser.add_argument('--bar', action = 'store_true')
  parser.add_argument('--gateway', '--gw', action = 'store_true')
  # debugging : provide numbers from stdin
  parser.add_argument('--interactive', '-i', action = 'store_true')
  # debugging : random numbers
  parser.add_argument('--random', '-r', action = 'store_true')
  # positional, target
  parser.add_argument('target', nargs='?')

  args = parser.parse_args()

  if args.target:
    target_dns = args.target
    target_ip = None
  else:
    target_dns = None
    target_ip = '8.8.8.8'

  do_gw = args.gateway
  do_bar = args.bar
  window = window_init(do_bar = do_bar, do_gw = do_gw)

  f_dead = make_dead()
  f_dead_fw = make_dead()
  gateway_ip = None

  while True:
    time0 = time.time()

    try:
      if target_ip is None:
        target_ip = do_resolve(target_dns)

      gateway_ip_now = get_gw(target_ip)
      if gateway_ip is None:
        if gateway_ip_now is None:
          raise Exception('gateway not found')
        else:
          gateway_ip = gateway_ip_now
          print('gateway set:', gateway_ip)
      if gateway_ip_now != gateway_ip:
          print('gateway changed: %s -> %s' % (gateway_ip, gateway_ip_now))
          gateway_ip = gateway_ip_now

      if args.interactive:
        ms = int(input('value: ').strip())
        ttl = 42
      elif args.random:
        ms = int(random.random() * __SCALE * 2.0)
        if ms < __SCALE * 1.2:
          raise Exception('random error %d' % ms)
        ttl = 42
      else:
        ms, ttl = do_ping(target_ip)
      output = get_con_bars(ms, max_col)
    except (NameError, TypeError):
      raise
    except Exception as e:
      ms = f_dead()
      ttl = ':-('
      output = repr(e)
    print(get_prefix('DST', ms, ttl) + output)

    if do_gw:
      try:
        if gateway_ip is None:
          raise Exception("no gateway")
        ms_gw, ttl_gw = do_ping(gateway_ip)
        output_gw = get_con_bars(ms_gw, max_col)
      except (NameError, TypeError):
        raise
      except Exception as e:
        ms_gw = f_dead()
        ttl_gw = ':-('
        output_gw = repr(e)
        print(get_prefix(' GW', ms_gw, ttl_gw) + output_gw)
    else:
      ms_gw, ttl_gw = None, None

    window_draw(window, ms, do_bar = do_bar, rtt_gw = ms_gw, ttl_gw = ttl_gw)

    wait = __INTERVAL - (time.time() - time0)
    if wait > 0 and not args.interactive:
      time.sleep(wait)

if __name__ == '__main__':
  main()
