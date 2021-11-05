# debian with Python preinstalled
FROM python:3.7-slim-buster

ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux

ARG MAVEN_VERSION=3.8.3
ARG PYTHON=python3.7
ARG HEXLITE_JAVA_PLUGIN_API_JAR_VERSION_TAG=1.4.0
ARG HEXLITE_JAVA_PLUGIN_API_JAR_WITH_PATH=/opt/hexlite/java-api/target/hexlite-java-plugin-api-${HEXLITE_JAVA_PLUGIN_API_JAR_VERSION_TAG}.jar
ARG HEXLITE_OWLAPI_PLUGIN_JAR_WITH_PATH=/opt/hexlite-owlapi-plugin/plugin/target/owlapiplugin-1.1.0.jar

RUN mkdir -p /opt/lib/$PYTHON/site-packages/

# install required dependencies
RUN set -ex ; \
  apt-get update ; \
  apt-get install -y --no-install-recommends \
    wget git ca-certificates \
    build-essential $PYTHON python3-setuptools python3-dev python3-pip lua5.3 \
    openjdk-11-jre-headless openjdk-11-jdk-headless

#
# hexlite
#

# install clingo via pip and jpype
RUN set -ex ; \
  $PYTHON -m pip install --upgrade pip ; \
  $PYTHON -m pip install clingo==5.5.0.post3 jpype1==1.2.1 cffi==1.14.4

# install maven for building hexlite Java API
# (not the one shipped with buster, because it does not work with openjdk-11)
RUN set -ex ; \
  cd /opt ; \
  wget https://downloads.apache.org/maven/maven-3/${MAVEN_VERSION}/binaries/apache-maven-${MAVEN_VERSION}-bin.tar.gz ; \
  tar xvf apache-maven-${MAVEN_VERSION}-bin.tar.gz ; \
  mv apache-maven-${MAVEN_VERSION} /opt/maven
ENV MAVEN_HOME /opt/maven
ENV PATH /opt/bin:/opt/maven/bin:$PATH
ENV PYTHONPATH /opt/lib/$PYTHON/site-packages/:$PYTHONPATH

COPY hexlite /opt/hexlite

RUN set -ex ; \
  cd /opt/hexlite ; \
  python3 setup.py install --prefix=/opt ; \
  mvn compile package install ; \
  find -name ".git" |xargs rm -rf

#
# hexlite-owlapi-plugin
#

COPY hexlite-owlapi-plugin /opt/hexlite-owlapi-plugin

# build and remove unnecessary files
RUN set -ex ; \
  cd /opt/hexlite-owlapi-plugin/plugin ; \
  CLASSPATH=${HEXLITE_JAVA_PLUGIN_API_JAR_WITH_PATH} \
  mvn compile package install ; \
  find -name ".git" |xargs rm -rf

#
# tests
#

# run hexlite tests (optional)
RUN set -ex ; \
  cd /opt/hexlite/tests ; \
  CLASSPATH=${HEXLITE_JAVA_PLUGIN_API_JAR_WITH_PATH} \
  ./run-tests.sh

# run hexlite-owlapi-plugin tests (optional)
RUN set -ex ; \
  cd /opt/hexlite-owlapi-plugin/examples/koala ; \
  CLASSPATH=${HEXLITE_JAVA_PLUGIN_API_JAR_WITH_PATH}:${HEXLITE_OWLAPI_PLUGIN_JAR_WITH_PATH} \
  /opt/bin/hexlite --pluginpath /opt/hexlite/plugins/ \
    --plugin javaapiplugin  at.ac.tuwien.kr.hexlite.OWLAPIPlugin \
    --number 33 --stats --flpcheck=none querykoala1.hex ; \
  CLASSPATH=${HEXLITE_JAVA_PLUGIN_API_JAR_WITH_PATH}:${HEXLITE_OWLAPI_PLUGIN_JAR_WITH_PATH} \
  /opt/bin/hexlite --pluginpath /opt/hexlite/plugins/ \
    --plugin javaapiplugin  at.ac.tuwien.kr.hexlite.OWLAPIPlugin \
    --number 33 --stats --flpcheck=none querykoala2.hex

#
# service
#

# copy sources for service
RUN mkdir /app
COPY grpcservice/requirements.txt grpcservice/config.json grpcservice/hexlite.proto grpcservice/server.py /app/

# install dependecies of service
RUN $PYTHON -m pip install -r app/requirements.txt

# adhere to container specification by also providing these two files
COPY grpcservice/hexlite.proto /model.proto
COPY license.json /license.json

WORKDIR /app

# compile protobuf
RUN python3 -m grpc_tools.protoc --python_out=. --proto_path=. --grpc_python_out=. hexlite.proto

EXPOSE 8061

# run server
CMD python3 server.py
