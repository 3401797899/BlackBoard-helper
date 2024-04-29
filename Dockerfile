# 可以替换Python版本
FROM python:3.9-alpine

# set default port for gunicorn
ENV PORT=8000

# add gunicorn config
ENV GUNICORN_CONFIG_ROOT=/etc/gunicorn
RUN mkdir -p $GUNICORN_CONFIG_ROOT
COPY gunicorn.conf.py $GUNICORN_CONFIG_ROOT

# setup working directory
ENV WORKDIR=/usr/django
RUN mkdir -p $WORKDIR
WORKDIR $WORKDIR

# install tini to ensure that gunicorn processes will receive signals
# install gettext and bash (required by start.sh)
# alpine换源
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.ustc.edu.cn/g' /etc/apk/repositories
# 更新pip3
RUN python3 -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN apk add --no-cache tini gettext bash

# run start.sh on container start
COPY start.sh $WORKDIR
RUN chmod +x ./start.sh
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["./start.sh"]

# create directories for generated static content, user-uploaded files and application source code
ENV STATIC_ROOT=/var/www/static
ENV MEDIA_ROOT=/var/www/media
ENV SOURCE_ROOT=$WORKDIR/app
RUN mkdir -p $STATIC_ROOT $MEDIA_ROOT $SOURCE_ROOT

# install gunicorn
ENV GUNICORN_VERSION=21.2.0
RUN pip install \
  gunicorn==$GUNICORN_VERSION \
  -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt $SOURCE_ROOT/requirements.txt
# USER root
RUN apk add --update --no-cache curl jq py3-configobj py3-pip py3-setuptools python3-dev mariadb-connector-c-dev \
  && apk add --no-cache gcc g++ jpeg-dev zlib-dev libc-dev musl-dev libffi-dev mariadb-dev \
#   && python -m pip install --upgrade pip \
  && pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple \
  # 把安装过程中不再需要的安装包清理掉、达到缩减镜像大小的目的
  && apk del gcc g++ musl-dev libffi-dev python3-dev \
  && apk del curl jq py3-configobj py3-pip py3-setuptools \
  && rm -rf /var/cache/apk/*
WORKDIR /usr/django

