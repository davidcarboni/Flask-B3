from setuptools import setup, find_packages
import unittest


def test_suite():
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')
    return suite


setup(name='Flask-B3',
      version='0.0.7',
      description='B3 header access and propagation for Flask.',
      author='David Carboni',
      author_email='david@carboni.io',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.2',
          'Topic :: System :: Logging',
          'Topic :: Internet :: Log Analysis',
          'Intended Audience :: Developers',
          'Framework :: Flask',
          'License :: OSI Approved :: MIT License',
      ],
      keywords=['logging', 'b3', 'distributed', 'tracing', 'zipkin'],
      url='https://github.com/rosgovuk/flask_b3',
      license='MIT',
      packages=find_packages(),
      install_requires=[
          'flask',
      ],
      test_suite='setup.test_suite',
      include_package_data=True,
      zip_safe=True,
      )
