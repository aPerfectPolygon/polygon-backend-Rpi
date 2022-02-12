# https://www.linuxbabe.com/security/modsecurity-nginx-debian-ubuntu
# https://github.com/openresty/headers-more-nginx-module#installation

# if ubuntu -> nginx-1.21.3
# if kali -> nginx-1.18.0
nginx_version=$1

if [ "$1" != "nginx-1.21.3" ] && [ "$1" != "nginx-1.18.0" ]
then
    echo "bad nginx_version [if ubuntu -> nginx-1.21.3  if kali -> nginx-1.18.0]"
    exit
fi

if [ "$1" != "nginx-1.21.3" ]
then
	# If you use Ubuntu 16.04, 18.04, 20.04, or 20.10, run the following commands to install the latest version of Nginx.
	#	sudo add-apt-repository ppa:ondrej/nginx-mainline -y
	#	sudo apt update
	# By default, only the binary repository is enabled. We also need to enable the source code repository in order to download Nginx source code. Edit the Nginx mainline repository file.
	# 	sudo nano /etc/apt/sources.list.d/ondrej-ubuntu-nginx-mainline-*.list
	# Find the line that begins with # deb-src.
	# 	# deb-src http://ppa.launchpad.net/ondrej/nginx-mainline/ubuntu/ focal main
	# Remove the # character to enable this source code repository.
	# 	deb-src http://ppa.launchpad.net/ondrej/nginx-mainline/ubuntu/ focal main
	# Save and close the file. Then update repository index.
	# 	sudo apt update

    echo "considering that you added ppa:ondrej/nginx-mainline to your apt repository"
fi

# uninstalling current version
apt --purge remove -y nginx*
rm -R -f /usr/local/src/nginx
rm -R -f /usr/local/src/ModSecurity-nginx
rm -R -f /usr/local/src/ModSecurity
rm -R -f /usr/local/src/header-more
rm -R -f /etc/nginx/modsec
rm -f /usr/share/nginx/modules/ngx_http_modsecurity_module.so
rm -f /usr/share/nginx/modules/ngx_http_headers_more_filter_module.so


apt install -y nginx nginx-core nginx-common nginx-full dpkg-dev gcc make build-essential autoconf automake libtool libcurl4-openssl-dev liblua5.3-dev libfuzzy-dev ssdeep gettext pkg-config libpcre3 libpcre3-dev libxml2 libxml2-dev libcurl4 libgeoip-dev libyajl-dev doxygen

mkdir -p /usr/local/src/nginx
cd /usr/local/src/nginx/ || exit
apt source nginx
cd $nginx_version || exit

git clone --depth 1 -b v3/master --single-branch https://github.com/SpiderLabs/ModSecurity /usr/local/src/ModSecurity/
cd /usr/local/src/ModSecurity/ || exit

git submodule init
git submodule update

./build.sh
./configure
make -j4
make install

git clone --depth 1 https://github.com/SpiderLabs/ModSecurity-nginx.git /usr/local/src/ModSecurity-nginx/
cd /usr/local/src/nginx/$nginx_version || exit
apt build-dep nginx
apt install uuid-dev

mkdir /usr/local/src/
wget https://github.com/openresty/headers-more-nginx-module/archive/refs/tags/v0.33.tar.gz -P /usr/local/src/
tar xf /usr/local/src/v0.33.tar.gz -C /usr/local/src/
mv /usr/local/src/headers-more-nginx-module-0.33 /usr/local/src/header-more
rm /usr/local/src/v0.33.tar.gz

cd /usr/local/src/nginx/$nginx_version || exit
./configure --with-compat --add-dynamic-module=/usr/local/src/ModSecurity-nginx --add-dynamic-module=/usr/local/src/header-more

make modules
cp objs/ngx_http_modsecurity_module.so /usr/share/nginx/modules/
cp objs/ngx_http_headers_more_filter_module.so /usr/share/nginx/modules/

mkdir /etc/nginx/modsec/
cp /usr/local/src/ModSecurity/modsecurity.conf-recommended /etc/nginx/modsec/modsecurity.conf
echo 'Include /etc/nginx/modsec/modsecurity.conf' > /etc/nginx/modsec/main.conf
cp /usr/local/src/ModSecurity/unicode.mapping /etc/nginx/modsec/

apt-mark hold nginx

# nano /etc/nginx/modsec/modsecurity.conf
# Find the following line.
# 	SecRuleEngine DetectionOnly
# This config tells ModSecurity to log HTTP transactions, but takes no action when an attack is detected. Change it to the following, so ModSecurity will detect and block web attacks.
# 	SecRuleEngine On
# Then find the following line (line 224), which tells ModSecurity what information should be included in the audit log.
# 	SecAuditLogParts ABIJDEFHZ
# However, the default setting is wrong. You will know why later when I explain how to understand ModSecurity logs. The setting should be changed to the following.
# 	SecAuditLogParts ABCEFHJKZ
# If you have a coding website, you might want to disable response body inspection, otherwise, you might get 403 forbidden errors just by loading a web page with lots of code content.
# 	SecResponseBodyAccess Off
# Save and close the file

# nano /etc/nginx/nginx.conf
# Add the following line at the beginning of the file.
# 	load_module modules/ngx_http_modsecurity_module.so;
#	load_module modules/ngx_http_headers_more_filter_module.so;
# Also, add the following two lines in the http {...} section, so ModSecurity will be enabled for all Nginx virtual hosts.
# 	modsecurity on;
# 	modsecurity_rules_file /etc/nginx/modsec/main.conf;

# sudo nginx -t
# sudo systemctl restart nginx