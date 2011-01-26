from distutils.core import setup
import sys

sys.path.append('striptease')
import striptease

setup(name='striptease',
      version='0.1',
      author_email='travis@upb.de',
      url='TODO:',
      download_url='TODO:',
      description='Encode and decode binary data with a C-like syntax',
      long_description='TODO:',
      packages=['striptease'],
      provides=['striptease'],
      install_requires=['crcmod>=1.7'],
      keywords='encoding decoding binary struct c syntax',
      license='BSD License',
      classifiers=['Development Status :: 3 - Alpha',
                   'Intended Audience :: Developers',
                   'Natural Language :: English',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python :: 2',
                   'License :: OSI Approved :: BSD License',
                   'Topic :: System :: Networking',
                   'Topic :: Software Development :: Libraries :: Python Modules',
                  ],
    )

