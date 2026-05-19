.PHONY: install run compile clean help

help:
	@echo "Available commands:"
	@echo "  make install  - Install requirements"
	@echo "  make run      - Run Flask server"
	@echo "  make compile  - Manually compile LaTeX resume"
	@echo "  make clean    - Clean output build files"

install:
	pip install -r requirements.txt

run:
	python app.py

compile:
	mkdir -p output
	xelatex -interaction=nonstopmode -output-directory=output resources/resume.tex

clean:
	rm -rf output/* resources/generated_data.aux resources/generated_data.log
