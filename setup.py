#!/usr/bin/env python
from setuptools import setup
from os.path import dirname, join

import kuegi_bot


here = dirname(__file__)


setup(name='kuegi-bot',
      version=kuegi_bot.__version__,
      description='KuegiBot using the KuegiChannel for entries',
      url='https://github.com/kuegi/sample-market-maker',
      long_description=open(join(here, 'README.md')).read(),
      long_description_content_type='text/markdown',
      author='Markus Zancolo',
      author_email='markus.zancolo@gmail.com',
      install_requires=[
          'requests',
          'websocket-client',
          'future',
          'plotly', 'bravado', 'bybit'
      ],
      packages=['kuegi_bot', 'kuegi_bot.auth', 'kuegi_bot.utils', 'kuegi_bot.ws'],
      entry_points={
          'console_scripts': ['kuegi_bot = kuegi_bot:run']
      }
      )
