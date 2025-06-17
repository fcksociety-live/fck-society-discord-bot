"""
Patch to make discord.py work without audioop module
This allows voice channel management without audio streaming capabilities
"""
import sys
import types

# Create a mock audioop module
mock_audioop = types.ModuleType('audioop')
mock_audioop.add = lambda a, b, c: b
mock_audioop.mul = lambda a, b, c: a
mock_audioop.ratecv = lambda a, b, c, d, e, f: (b'', (0, 0))
mock_audioop.tostereo = lambda a, b, c: a

# Insert mock into sys.modules before discord.py imports it
sys.modules['audioop'] = mock_audioop