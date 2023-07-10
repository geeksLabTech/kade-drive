docker:
	docker build -t kade-drive .  

shell:
	docker run -it kade-drive bash