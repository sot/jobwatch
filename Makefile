# Set the task name
TASK = skawatch
VERSION = 0.1

# Uncomment the correct choice indicating either SKA or TST flight environment
FLIGHT_ENV = SKA
SHARE = jobwatch.py skawatch.py log_template.html index_template.html
DATA = task_schedule.cfg
WWW = overlib.js

include /proj/sot/ska/include/Makefile.FLIGHT
INSTALL_WWW = /proj/sot/ska/www/ASPECT/$(TASK)

install:
	mkdir -p $(INSTALL_DATA)
	mkdir -p $(INSTALL_SHARE)
	mkdir -p $(INSTALL_WWW)

	rsync --times --cvs-exclude $(DATA) $(INSTALL_DATA)/
	rsync --times --cvs-exclude $(SHARE) $(INSTALL_SHARE)/
	rsync --times --cvs-exclude $(WWW) $(INSTALL_WWW)/
