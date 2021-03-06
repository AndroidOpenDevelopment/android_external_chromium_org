# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import logging
import socket
import threading
import time

from telemetry.core.backends.chrome import websocket


class InspectorWebsocket(object):

  def __init__(self, notification_handler=None, error_handler=None):
    """Create a websocket handler for communicating with Inspectors.

    Args:
      notification_handler: A callback for notifications received as a result of
        calling DispatchNotifications() or StartAsyncDispatchNotifications().
        Must accept a single JSON object containing the Inspector's
        notification. May return True to indicate the stop async dispatching.
      error_handler: A callback for errors in communicating with the Inspector.
        Must accept a single numeric parameter indicated the time elapsed before
        the error.
    """
    self._socket = None
    self._thread = None
    self._cur_socket_timeout = 0
    self._next_request_id = 0
    self._notification_handler = notification_handler
    self._error_handler = error_handler

  @property
  def is_dispatching_async_notifications(self):
    return self._thread != None

  def Connect(self, url, timeout=10):
    assert not self._socket
    self._socket = websocket.create_connection(url, timeout=timeout)
    self._cur_socket_timeout = 0
    self._next_request_id = 0

  def Disconnect(self):
    if self._socket:
      self._socket.close()
      self._socket = None

  def SendAndIgnoreResponse(self, req):
    req['id'] = self._next_request_id
    self._next_request_id += 1
    data = json.dumps(req)
    self._socket.send(data)
    logging.debug('sent [%s]', data)

  def SyncRequest(self, req, timeout=10):
    assert not self._thread, 'Cannot be used during async dispatching.'
    self.SendAndIgnoreResponse(req)

    while self._socket:
      res = self._Receive(timeout)
      if 'id' in res and res['id'] == req['id']:
        return res

  def DispatchNotifications(self, timeout=10):
    assert not self._thread, 'Cannot be used during async dispatching.'
    self._Receive(timeout)

  def StartAsyncDispatchNotifications(self):
    assert not self._thread, 'Cannot be started twice.'
    self._thread = threading.Thread(target=self._AsyncDispatcher)
    self._thread.daemon = True
    self._thread.start()

  def StopAsyncDispatchNotifications(self):
    self._thread.join(timeout=30)
    if self._thread.is_alive():
      raise RuntimeError('Timed out waiting for async dispatch notifications.')
    self._thread = None

  def _AsyncDispatcher(self):
    while self._socket:
      try:
        if not self._Receive():
          break
      except websocket.WebSocketTimeoutException:
        pass

  def _SetTimeout(self, timeout):
    if self._cur_socket_timeout != timeout:
      self._socket.settimeout(timeout)
      self._cur_socket_timeout = timeout

  def _Receive(self, timeout=10):
    self._SetTimeout(timeout)
    start_time = time.time()
    try:
      while self._socket:
        data = self._socket.recv()
        res = json.loads(data)
        logging.debug('got [%s]', data)
        if 'method' in res and self._notification_handler(res):
          return None
        return res
    except (socket.error, websocket.WebSocketException):
      elapsed_time = time.time() - start_time
      self._error_handler(elapsed_time)
