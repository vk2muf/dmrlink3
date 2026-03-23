#	Dockerfile
#	HB & DMRlink Server VK2MUF convert to Python3


FROM	debian:latest

RUN	    apt-get update && apt-get install -y wget nano supervisor
RUN	    apt install python3-pip -y
RUN	    apt install tcpdump -y
RUN     apt install dnsutils -y
RUN     apt install unzip -y
RUN     apt install python3-dev -y
RUN     apt install python3-pip -y
RUN     apt install python3-twisted -y
RUN     apt install vim -y
RUN     apt install openssh-server -y
#Update below line with username and password you wish to use for SSH
RUN     echo 'root:password' | chpasswd
RUN     sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN     sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd
RUN	    apt install -y python3-venv
RUN	    python3 -m venv /opt/venv
ENV	    PATH="/opt/venv/bin:$PATH"
COPY    dmr_utils-master /app/dmr_utils-master
RUN	    pip install /app/dmr_utils-master
COPY	requirements.txt /app/requirements.txt
RUN     pip install -r /app/requirements.txt
COPY    DMRlink /opt/dmrlink/
COPY    HBLink  /opt/hblink/
RUN     chmod +x /opt/dmrlink/IPSC_Bridge.py
RUN     chmod +x /opt/hblink/HB_Bridge.py
COPY	./build-config-files/supervisord.conf /etc/supervisor/supervisord.conf
COPY	./build-config-files/hblink.cfg /opt/hblink/hblink.cfg
COPY	./build-config-files/HB_Bridge.cfg /opt/hblink/HB_Bridge.cfg
COPY	./build-config-files/dmrlink.cfg /opt/dmrlink/dmrlink.cfg
COPY	./build-config-files/IPSC_Bridge.cfg /opt/dmrlink/ISPC_Bridge.cfg

EXPOSE	62030/udp
EXPOSE	50000/udp
EXPOSE  22/tcp


CMD	["/usr/bin/supervisord"]