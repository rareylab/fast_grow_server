"""fast_grow settings"""
import os
from fast_grow_server.settings import BASE_DIR

PREPROCESSOR = os.path.join(BASE_DIR, 'bin', 'Preprocessor')
CLIPPER = os.path.join(BASE_DIR, 'bin', 'Clipper')
INTERACTIONS = os.path.join(BASE_DIR, 'bin', 'InteractionGenerator')
FAST_GROW = os.path.join(BASE_DIR, 'bin', 'FastGrow')

CHUNK_SIZE = 100
