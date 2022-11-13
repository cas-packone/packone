FROM python:3.6
# ADD  requirements.txt ./
# RUN pip install -r requirements.txt
RUN pip install pk1
#CMD ["pk1", "setup --database pk1:pk1:pk1-pg:5432:pk1"]
ENTRYPOINT ["tail", "-f", "/dev/null"]
