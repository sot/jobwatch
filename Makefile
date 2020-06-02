# Set the task name
TASK = skawatch3

SHARE = jobwatch.py skawatch.py hourly_watch.py \
        log_template.html index_template.html hourly_template.html
DATA = task_schedule.cfg hourly_task_schedule.cfg
WWW = overlib.js

SKA3 = /proj/sot/ska3
INSTALL_WWW = /proj/sot/ska/www/ASPECT/$(TASK)
INSTALL_DATA = $(SKA3)/data/$(TASK)
INSTALL_SHARE = $(SKA3)/share/$(TASK)

install:
	mkdir -p $(INSTALL_DATA)
	mkdir -p $(INSTALL_SHARE)
	mkdir -p $(INSTALL_WWW)

	rsync --times --cvs-exclude $(DATA) $(INSTALL_DATA)/
	rsync --times --cvs-exclude $(SHARE) $(INSTALL_SHARE)/
	rsync --times --cvs-exclude $(WWW) $(INSTALL_WWW)/
