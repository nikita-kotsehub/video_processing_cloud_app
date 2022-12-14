FROM amazonlinux

RUN yum update -y && \
    yum install python37 -y && \
    yum install -y pip3 libxml2 libxslt && \
    pip3 install -t /deps_source lxml scrapy

CMD cp -r /deps_source/* /deps
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt -t /deps_source