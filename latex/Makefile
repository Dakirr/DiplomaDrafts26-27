IMAGE := diploma-latex

.DEFAULT_GOAL := pdf

.PHONY: pdf watch clean image start stop

start:
	colima start --arch aarch64 --vm-type=vz --vz-rosetta \
		--dns=8.8.8.8 --dns=1.1.1.1 \
		--network-address --network-host-addresses

stop:
	colima stop

pdf: image
	docker run --rm --volume "$(CURDIR):/work" $(IMAGE)

watch: image
	docker run --rm --volume "$(CURDIR):/work" $(IMAGE) \
		latexmk -pdf -pvc -interaction=nonstopmode -halt-on-error main.tex

clean: image
	docker run --rm --volume "$(CURDIR):/work" $(IMAGE) latexmk -C main.tex

image:
	docker build --tag $(IMAGE) .
