
class WSException(Exception):
  CONNECTION_CLOSED = 0
  PROTOCOL_ERROR = 1002

  def __init__(self, code, message=''):
    self.code = code
    self.message = message