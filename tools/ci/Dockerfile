FROM python:3.5
COPY requirements.txt /tmp
RUN pip3 install 'pbr>=1.8.0'
RUN pip3 install tox
RUN pip3 install -r /tmp/requirements.txt
