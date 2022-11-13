FROM python:3.6
# ADD  requirements.txt ./
# RUN pip install -r requirements.txt
RUN pip install pk1
ENTRYPOINT ["tail", "-f", "/dev/null"]
