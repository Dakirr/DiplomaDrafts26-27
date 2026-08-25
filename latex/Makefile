IMAGE := diploma-latex
WATCH_CONTAINER := diploma-latex-watch

.DEFAULT_GOAL := pdf

.PHONY: pdf watch clean image start stop vm-start vm-stop

start: vm-start image
	@if docker container inspect "$(WATCH_CONTAINER)" >/dev/null 2>&1; then \
		docker start "$(WATCH_CONTAINER)" >/dev/null; \
	else \
		docker run --detach --rm --name "$(WATCH_CONTAINER)" \
			--volume "$(CURDIR):/work" $(IMAGE) \
			sh scripts/watch.sh >/dev/null; \
	fi
	@echo "Container $(WATCH_CONTAINER) is running."

vm-start:
	colima start --arch aarch64 --vm-type=vz --vz-rosetta \
		--dns=8.8.8.8 --dns=1.1.1.1 \
		--network-address --network-host-addresses

stop:
	@if docker container inspect "$(WATCH_CONTAINER)" >/dev/null 2>&1; then \
		docker stop "$(WATCH_CONTAINER)"; \
	else \
		echo "Container $(WATCH_CONTAINER) is not running."; \
	fi

vm-stop:
	colima stop

pdf: image
	docker run --rm --volume "$(CURDIR):/work" $(IMAGE)

watch: vm-start image
	docker run --rm --name "$(WATCH_CONTAINER)" \
		--volume "$(CURDIR):/work" $(IMAGE) \
		sh scripts/watch.sh

clean: image
	docker run --rm --volume "$(CURDIR):/work" $(IMAGE) latexmk -C main.tex

image:
	docker build --tag $(IMAGE) .
