.PHONY: install run compile clean test help

help:
	@echo "Available commands:"
	@echo "  make install  - Install requirements"
	@echo "  make run      - Run Flask server"
	@echo "  make compile  - Manually compile LaTeX resume"
	@echo "  make test     - Run test suite"
	@echo "  make clean    - Clean output build files"

install:
	pip install -r requirements.txt

run:
	python app.py

compile:
	mkdir -p output
	python -c "from utils.helpers import clean_and_write; clean_and_write('resources/resume.tex', 'resources/generated_data.tex', 'output/resume.tex')"
	xelatex -interaction=nonstopmode -output-directory=output resources/resume.tex

test:
	pytest -q

clean:
	find output -maxdepth 1 -type f \( -name '*.aux' -o -name '*.log' -o -name '*.out' -o -name '*.pdf' -o -name '*.png' -o -name '*.tex' \) -delete
	find resources -maxdepth 1 -type f \( -name 'generated_data.aux' -o -name 'generated_data.log' \) -delete
