# Build the toy test cartridge (requires RGBDS: https://rgbds.gbdev.io)
toy/toy.gb: toy/toy.asm
	rgbasm -o toy/toy.o toy/toy.asm
	rgblink -o $@ toy/toy.o
	rgbfix -v -p 0xFF -t TOY $@
	rm toy/toy.o

test: toy/toy.gb
	.venv/bin/python -m pytest tests/ -q
	npm test

.PHONY: test
