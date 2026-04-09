from continuumio/miniconda3
workdir /reddit
copy environment.yml .
run conda env create -f environment.yml
shell ["conda", "run", "-n", "msds692_reddit", "/bin/bash", "-c"]
copy . .
cmd ["conda", "run" "-n", "msds692_reddit", "python", "reddit_api_call.py"]