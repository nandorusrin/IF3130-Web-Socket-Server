import unittest
from frame import Frame

class TestFrame(unittest.TestCase):
  def setUp(self):  # will be executed every time
    pass

  # define all other test cases (function) below
  def test_close_frame(self):
    # masked
    dummy_payload_masked = b'Endpoint shutting down'
    objFrame = Frame(1, Frame.cls_frame, dummy_payload_masked, _masked=True)
    self.assertEqual(objFrame.opcode, Frame.cls_frame)
    self.assertEqual(objFrame.FIN, 1)
    self.assertTrue(objFrame.isMasked())
    self.assertEqual(objFrame.payload_len, len(dummy_payload_masked))
    self.assertEqual(objFrame.payload, dummy_payload_masked)

    # not masked
    dummy_payload_unmasked = b'Received frame too large'
    objFrame = Frame(1, Frame.cls_frame, dummy_payload_unmasked, _masked=False)
    self.assertEqual(objFrame.opcode, Frame.cls_frame)
    self.assertEqual(objFrame.FIN, 1)
    self.assertFalse(objFrame.isMasked())
    self.assertEqual(objFrame.payload_len, len(dummy_payload_unmasked))
    self.assertEqual(objFrame.payload, dummy_payload_unmasked)

  def test_ping_frame(self):
    
  
if __name__ == '__main__':
  unittest.main()