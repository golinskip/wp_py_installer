#!/usr/bin/env python
import os
import sys
import yaml
import wget
import pwd
import grp
import git
import zipfile
import shutil
import _mysql
import subprocess

# Only sudo can judge me
if not os.geteuid() == 0:
    sys.exit("Only root can run this script")

# Load configuration
config_file = "wp_create.yml"
if not os.path.isfile(config_file):
    print "Brak pliku z konfiguracja"
    exit()
with open(config_file, 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

# Project name
while True:
    name = raw_input("Podaj nazwe projektu: ")
    type(name)
    if os.path.exists(cfg['path']['http'] + "/" + name):
        print "Taki projekt juz istnieje"
        continue
    if not name:
      continue
    if len(name) < 2:
      print "Nazwa musi miec przynajmniej 2 znaki"
      continue
    if not name.isalpha():
      print "Nazwa musi sie skladac z samych iter"
      continue
    break

# Basic Variables
url = name + cfg['txt']['domain']
db_name = name
path_this = os.path.dirname(os.path.realpath(__file__))
path_tmp = path_this + "/tmp"
path_project = cfg['path']['http'] + "/" + name
path_tmp_wordpress = path_tmp + "/wordpress"

# Create mysql database
print "Tworze baze danych"
db=_mysql.connect("localhost",cfg['mysql']['user'],cfg['mysql']['pass'])
db.query("CREATE DATABASE " + db_name)

# Download and unzip Wordpress
print "Pobieranie Wordpressa"
wp_zip = wget.download(cfg['url']['wordpress'], out=path_tmp)

print
print "Rozpakowywanie " + wp_zip
zip_ref = zipfile.ZipFile(wp_zip, 'r')
zip_ref.extractall(path_tmp)
zip_ref.close()

print "Usuwanie pliku zip"
os.remove(wp_zip)

print "Przenosze do docelowej lokalizacji"
os.rename(path_tmp_wordpress, path_project)

# Add host to hosts
path_hosts = cfg['path']['hosts']
if len(path_hosts) > 2:
    print "Dodawanie hosta do pliku "+ path_hosts
    with open(path_hosts, 'a') as file:
        file.write("\n" + '127.0.0.1    '+url)

# Add new virtual host
path_virtual_host = cfg['path']['vhost'] + "/" + url + ".conf"
print "Dodaje virtual hosta do pliku " + path_virtual_host
with open(path_virtual_host, 'a') as file:
    file.write("<VirtualHost *:80>\n")
    file.write("         DocumentRoot " + path_project + "\n")
    file.write("         <Directory " + path_project + ">\n")
    file.write("                 Options -Indexes\n")
    file.write("                 AllowOverride All\n")
    file.write("         </Directory>\n")
    file.write("         ServerName " + url + "\n" )
    file.write("</VirtualHost>\n")

# Clone git plugin and layouts
path_plugin = path_project + "/wp-content/plugins/" + cfg['txt']['plugin']
path_theme = path_project + "/wp-content/themes/" + cfg['txt']['theme']
path_theme_compiler = path_project + "/" + cfg['txt']['theme-complier']
if not os.path.exists(path_plugin):
    os.makedirs(path_plugin)
if not os.path.exists(path_theme):
    os.makedirs(path_theme)
if not os.path.exists(path_theme_compiler):
    os.makedirs(path_theme_compiler)

print "Pobieram plugin wtst"
os.system("git clone " + cfg['git']['url'] + cfg['git']['plugin'] + " " + path_plugin)
print "Pobieram plugin layout"
os.system("git clone " + cfg['git']['url'] + cfg['git']['theme'] + " " + path_theme)
print "Pobieram plugin kompilator"
os.system("git clone " + cfg['git']['url'] + cfg['git']['theme-compiler'] + " " + path_theme_compiler)

# Copy src dist to src
path_src_dist = path_theme_compiler + "/src-dist"
path_src = path_theme_compiler + "/src"
print "Kopiuje przykladowe wejscie jako docelowe " + path_src_dist + " " + path_src
def copyanything(src, dst):
    try:
        shutil.copytree(src, dst)
    # Directories are the same
    except shutil.Error as e:
        print('Directory not copied. Error: %s' % e)
    # Any error saying that the directory doesn't exist
    except OSError as e:
        print('Directory not copied. Error: %s' % e)
copyanything(path_src_dist, path_src)

# Change rights to project
print "Ustawiam prawa dostepu projektu dla " + cfg['rights']['user'] + ":" + cfg['rights']['group']
uid = pwd.getpwnam(cfg['rights']['user']).pw_uid
gid = grp.getgrnam(cfg['rights']['group']).gr_gid
os.chown(path_project, uid, gid)
for root, dirs, files in os.walk(path_project):  
  for momo in dirs:
    os.chown(os.path.join(root, momo), uid, gid)
  for momo in files:
    os.chown(os.path.join(root, momo), uid, gid)

print "Enabling site"
os.system("a2ensite " + url)
os.system("service apache2 restart")

print "=========== run me ======================="
print "http://" +url
print "=========================================="