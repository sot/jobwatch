# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os
import sys
from setuptools import setup

try:
    from testr.setup_helper import cmdclass
except ImportError:
    cmdclass = {}

if "--user" not in sys.argv:
    share_path = os.path.join("share", "jobwatch")
    data_files = [(share_path, ['task_schedule_hourly.cfg', 'task_schedule_daily.cfg'])]
else:
    data_files = None

entry_points = {'console_scripts': ['skawatch_daily=jobwatch.skawatch:main',
                                    'skawatch_hourly=jobwatch.hourly_watch:main']}

setup(name='jobwatch',
      author='Tom Aldcroft',
      description='Watch ska jobs',
      author_email='taldcroft@cfa.harvard.edu',
      packages=['jobwatch'],
      package_data={'jobwatch': ['*html', '*js']},
      include_package_data=True,
      data_files=data_files,
      license=("New BSD/3-clause BSD License\nCopyright (c) 2019"
               " Smithsonian Astrophysical Observatory\nAll rights reserved."),
      use_scm_version=True,
      setup_requires=['setuptools_scm', 'setuptools_scm_git_archive'],
      entry_points=entry_points,
      zip_safe=False,
      tests_require=['pytest'],
      cmdclass=cmdclass,
      )
