from continuumio/miniconda3
workdir /truthsocial
copy . .
run conda env create -f environment.yml
shell ["conda", "run", "-n", "msds692_truthsocial", "/bin/bash", "-c"]
cmd ["python", "truth_social_api_call.py"]