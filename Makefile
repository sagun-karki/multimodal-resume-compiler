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
	python -c "main=open('resources/resume.tex').read(); gen=open('resources/generated_data.tex').read(); open('output/resume.tex', 'w').write(main.replace(chr(92) + 'input{resources/generated_data.tex}', gen))"
	xelatex -interaction=nonstopmode -output-directory=output resources/resume.tex

clean:
	rm -rf output/* resources/generated_data.aux resources/generated_data.log
