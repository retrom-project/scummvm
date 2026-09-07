.PHONY: retrom-dist-list
retrom-dist-list:
	@$(foreach f,$(DIST_FILES_THEMES) $(DIST_FILES_ENGINEDATA) $(DIST_FILES_ENGINEDATA_BIG) $(DIST_FILES_VKEYBD) $(DIST_FILES_SOUNDFONTS),printf 'data\t%s\n' '$(f)';)
	@$(foreach f,$(DIST_FILES_SHADERS),printf 'shader\t%s\n' '$(f)';)
