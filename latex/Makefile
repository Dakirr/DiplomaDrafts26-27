IMAGE := diploma-latex
WATCH_CONTAINER := diploma-latex-watch
COLIMA_START = colima start --arch aarch64 --vm-type=vz --vz-rosetta \
	--dns=8.8.8.8 --dns=1.1.1.1 \
	--network-address --network-host-addresses

.DEFAULT_GOAL := pdf

.PHONY: pdf watch clean image start stop docker-ready vm-start vm-stop

start: image
	@if docker container inspect "$(WATCH_CONTAINER)" >/dev/null 2>&1; then \
		docker start "$(WATCH_CONTAINER)" >/dev/null; \
	else \
		docker run --detach --rm --name "$(WATCH_CONTAINER)" \
			--volume "$(CURDIR):/work" $(IMAGE) \
			sh scripts/watch.sh >/dev/null; \
	fi
	@echo "Container $(WATCH_CONTAINER) is running."

docker-ready:
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "Docker CLI is required. Install Docker Desktop or Docker with Colima." >&2; \
		exit 1; \
	fi
	@if docker info >/dev/null 2>&1; then \
		:; \
	elif [ "$$(docker context show)" = "colima" ] && [ -z "$$DOCKER_HOST" ]; then \
		$(COLIMA_START) && docker info >/dev/null; \
	else \
		echo "Docker is unavailable. Start Docker Desktop, or run 'make vm-start' for Colima, and select the corresponding Docker context." >&2; \
		exit 1; \
	fi

vm-start:
	$(COLIMA_START)

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

watch: image
	docker run --rm --name "$(WATCH_CONTAINER)" \
		--volume "$(CURDIR):/work" $(IMAGE) \
		sh scripts/watch.sh

clean: image
	docker run --rm --volume "$(CURDIR):/work" $(IMAGE) latexmk -C main.tex

image: docker-ready
	docker build --tag $(IMAGE) .
