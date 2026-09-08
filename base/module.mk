MODULE := base

MODULE_OBJS := \
	test_new_standards.o \
	main.o \
	commandLine.o \
	retrom-detection.o \
	plugins.o \
	version.o

# Include common rules
include $(srcdir)/rules.mk
