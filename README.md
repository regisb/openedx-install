# Open edX: The "Install From Scratch" Manual

> WARNING! These instructions are now outdated, as they relate to the Ginkgo release of Open edX. As of March 2019, the current release of Open edX is [Ironwood](https://open.edx.org/blog/ironwood-is-here/). But do not despair! I have created [Tutor](https://github.com/regisb/tutor), a tool for installing Open edX in one click. Try it, it's amazing! [Here](https://docs.tutor.overhang.io/) is the documentation, and there is a also [ready-to-launch AMI on AWS](https://aws.amazon.com/marketplace/pp/B07PV3TB8X).

What follows are the instructions for installing an [Open edX](https://open.edx.org/) instance ([Ginkgo](https://open.edx.org/blog/ginkgo-2017-summer-release-open-edx-platform-here) release) from scratch. The instructions below *do not* rely on Ansible playbooks for deployment.

## Important notes, FAQ and disclaimer

The instructions listed here do not constitute a one-click install (not *at all*). You will need to read the various configuration files and understand what all the commands do. As such, it's an installation manual for experts only.

**Do I need this? Why not just use the Ansible playbooks?** Great question! Of course, the instructions listed here are heavily inspired by the Ansible playbooks from the [edx/configuration](https://github.com/edx/configuration/) repository. The playbooks are the current canonical way of installing an Open edX instance, either on a local or distributed environment. However, we feel there are many cases where the playbooks are not adequate. In particular, it is extremely difficult to understand what the playbooks do if you are not both an Ansible and an Open edX expert. As a consequence, many Open edX administrators do not know very well what services are run, how they coordinate, where to look for information, etc. Also, Open edX has gained an unfair reputation as a very complex piece of software that is difficult to administer. By decomposing the install process in simple steps, we hope to dispel that myth.

**I have followed all the instructions but my Open edX install doesn't have feature X.** Open edX supports a gazillion optional features. The instructions given in this manual are for a minimal Open edX install. For instance, we explicitly disable the discussion forums. If you wish to activate a particular feature, we suggest you start with a minimal install and then follow the specific instructions from the Open edX documentation for that feature.

**The instructions don't work! Where can I ask for help?** There are many ways for you to get help from the Open edX community: see the [Getting Help](https://open.edx.org/getting-help) page. Note however that edX (or Ned!) is *not* responsible for maintaining this particular set of instructions. If you feel you have stumbled upon an issue that is specifically related to the current set of instructions, please open a [Github issue](https://github.com/regisb/openedx-install/issues) where you describe your problem in details.

## Requirements

### OS

Open edX Ginkgo is compatible with Ubuntu 16.04 -- it is untested with other environments. In the following, we assume a clean install of Ubuntu 16.04. For bootstrapping, we suggest to start from a clean server or virtual machine (see [section on vm configuration](#virtual-machine-configuration)).

### Resources

It depends ;-)

You should have at least 2 Gb of RAM for each LMS and each CMS. Thus, a single-server instance running all services as well as one LMS and one CMS should have at least 4 Gb of RAM. Each LMS server should be able to handle a couple hundred users. (this is a very rough estimate)

## Virtual machine configuration

This section is for people who want to test drive Open edX or to setup a development environment in a VM. Skip ahead if you are deploying on a production environment.

Launch virtual machine:

    vagrant init ubuntu/xenial64

Add the following lines to the configuration:

    config.vm.network "forwarded_port", guest: 8000, host: 8000
    config.vm.network "forwarded_port", guest: 8001, host: 8001

Increase the amount of available memory to 2Gb: (actually, it is recommended to get that to 4Gb if you have enough RAM)

    config.vm.provider "virtualbox" do |vb|
        vb.memory = "2048"
    end

Boot virtual machine:

    vagrant up

Login:

    vagrant ssh

Add some swap:

    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    sudo sh -c  'echo "/swapfile   none    swap    sw    0   0" >> /etc/fstab'

All following commands are assumed to be run in the VM.

## System preparation

    sudo apt update
    sudo apt upgrade -y
    sudo apt autoremove -y

Install base packages:

    sudo apt install -y language-pack-en git python-virtualenv
    sudo apt install -y build-essential software-properties-common curl git-core libxml2-dev libxslt1-dev python-pip libmysqlclient-dev python-apt python-dev libxmlsec1-dev libfreetype6-dev swig gcc g++

Create unprivileged user which will run the web applications:

    sudo adduser edxapp
    sudo -sHu edxapp

Note that the `edxapp` user does not have sudo rights, so all following commands that are run with `sudo` will have to be run with a different user; for instance, the user with which you created the `edxapp` user. This is on purpose, as `edxapp` will be used to run the web services. But if you want to grant sudo rights to `edxapp`, run : `sudo usermod -a -G sudo edxapp`.

Create folder in which everything will be installed:

    sudo mkdir /opt/openedx
    sudo chown edxapp:edxapp /opt/openedx

## Services

You will need to setup a couple external services to get Open edX to run. In the development install, it is assumed that they all run on the same machine.

### Memcached

Install memcached:

    sudo apt install memcached

### MySQL database

Create SQL database:

    # Install mysql server
    sudo apt install mysql-server mysql-client

    # Create the mysql database and user
    mysql -u root -p
    CREATE DATABASE edxapp;
    CREATE USER 'edxapp'@'localhost' IDENTIFIED BY 'write this password somewhere you will need it in auth.json';
    GRANT ALL ON edxapp.* TO 'edxapp'@'localhost';

### RabbitMQ

Install rabbitmq broker:

    sudo apt install rabbitmq-server

### MongoDb

Install mongodb:

    sudo apt install mongodb-server

### Elasticsearch (optional)

Elasticsearch is only required if you need to setup course search or discussion forums. In the current install those services are disabled. But if you wish to activate these services later, you will need to install a specific version of Elasticsearch.

Install elasticsearch 0.90.13 from the official repositories:

    wget -O - http://packages.elasticsearch.org/GPG-KEY-elasticsearch | sudo apt-key add -
    sudo sh -c 'echo "deb http://packages.elasticsearch.org/elasticsearch/0.90/debian stable main" > /etc/apt/sources.list.d/elasticsearch.list'
    sudo apt update
    sudo apt install elasticsearch=0.90.13 openjdk-8-jdk
    sudo apt-mark hold elasticsearch

## LMS/CMS install

In Open edX, there are two distinct web applications that need to be run: the LMS is the public website where courses can be subscribed to, followed, etc. by students. The CMS (also called the studio) is where courses are created and it is accessed only by course authors and platform administrators. Note that the LMS don't have to run on the same servers; however, they need to share all the external services (MySQL, MongoDb, etc.).

From here on, multiple configuration files need to be copied from the current repository and edited. Values that need to be edited are surrounded by triple dashes ("`---`").

### Preparation, as sudo user

Install packages required by LMS/CMS:
    
    sudo apt install -y gettext gfortran graphviz graphviz-dev libffi-dev libfreetype6-dev libgeos-dev libjpeg8-dev liblapack-dev libpng12-dev libxml2-dev libxmlsec1-dev libxslt1-dev nodejs npm ntp pkg-config 

### App install (as edxapp user)

Clone repositories:

    cd /opt/openedx
    git clone https://github.com/edx/edx-platform.git
    cd edx-platform/
    git checkout open-release/ginkgo.master 

**Note:** Configuring the JSON files could take a while and requires manual edits to the json files.

Edit [`config/lms/lms.env.json`](./config/lms/lms.env.json) and copy it to `/opt/openedx/lms.env.json`.

Edit [`config/cms/cms.env.json`](./config/cms/cms.env.json) and copy it to `/opt/openedx/cms.env.json`.

Don't forget to edit all the values surrounded by "`---`"! In particular, set the `SITE_NAME` variable to point to your domain name. In development, this will point to `localhost:8000` (for the LMS) and `localhost:8001` (for the studio). 

Edit and copy [`config/lms/lms.auth.json`](./config/lms/lms.auth.json) and [`config/cms/cms.auth.json`](./config/cms/cms.auth.json) to `/opt/openedx/lms.auth.json` and `/opt/openedx/cms.auth.json`.

Copy development settings file from [`config/lms/development.py`](./config/lms/development.py) and [`config/cms/development.py`](./config/cms/development.py) to `/opt/openedx/edx-platform/lms/envs/development.py` and `/opt/openedx/edx-platform/cms/envs/development.py`.

Create necessary folders:

    mkdir /opt/openedx/staticfiles
    mkdir /opt/openedx/uploads # (must correspond to `MEDIA_ROOT`)

Create virtualenv:

    cd /opt/openedx
    virtualenv venv && source venv/bin/activate

Install python requirements:
    
    cd edx-platform/
    pip install -r requirements/edx/pre.txt
    pip install -r requirements/edx/github.txt # go grab a coffee, this is going to take some time
    pip install -r requirements/edx/local.txt
    pip install -r requirements/edx/base.txt
    pip install -r requirements/edx/post.txt
    pip install -r requirements/edx/paver.txt

Install node requirements (and others):

    nodeenv -p  # Install node environment in same virtualenv
    paver install_prereqs

Generate assets:

    paver update_assets lms --settings=development
    paver update_assets cms --settings=development

Run migrations:

    ./manage.py lms migrate --settings=development
    ./manage.py cms migrate --settings=development

The following instructions allow you to run LMS and Studio development servers:

    paver lms --fast --settings=development
    paver studio --fast --settings=development

These development servers should NOT be used in production. For production configuration, follow the instructions from the [production deployment section](#production-deployment)

At that point, you should be able to run the server and access the website.

Quickly, you will find out that you need a staff user to administer your platform. To create a staff user, run:

    ./manage.py lms --settings=development manage_user --superuser --staff yourusername your@address.com
    ./manage.py lms --settings=development changepassword yourusername # set an appropriate password

## Production deployment

Deploying an Open edX instance in production requires to set up a couple additional services.

### Production settings

You will need to create different settings files for production than for development.

Edit [`config/lms/production.py`](./config/lms/production.py) and add it to `edx-platform/lms/envs/`.

Edit [`config/cms/production.py`](./config/cms/production.py) and add it to `edx-platform/cms/envs/`.

In production, don't forget to set appropriate urls in `/opt/openedx/lms.env.json` and `/opt/openedx/cms.env.json`. Note that you will need to choose different domain names for the LMS and the CMS. In particular, pick an appropriate value for the `SITE_NAME`.

Usually, the lms is configured on the bare domain name ("myopenedx.com") or  on the `www` subdomain ("www.myopenedx.com"), while cms typically uses the `studio` subdomain ("studio.myopenedx.com").

Note that if your databases (MySQL and MongoDB) and other external services run on a different machine, you will need to point to them in your `lms.auth.json` and `cms.auth.json` files.

### Static assets

It is necessary to generate static assets again with the production settings:

    paver update_assets lms --settings=production
    paver update_assets cms --settings=production

Static assets will be generated in `/opt/openedx/staticfiles`.

### Supervisor

[Supervisor](http://supervisord.org/) is a tool for process supervision. You will use it to start and stop Open edX-related services.

Start by installing Supervisor:

    sudo apt install supervisor

Edit [`./config/supervisor/conf.d/lms.conf`](https://github.com/regisb/openedx-install/blob/master/config/supervisor/conf.d/lms.conf) and add it to `/etc/supervisor/conf.d/lms.conf`.

Edit [`./config/supervisor/conf.d/cms.conf`](https://github.com/regisb/openedx-install/blob/master/config/supervisor/conf.d/lms.conf) and add it to `/etc/supervisor/conf.d/cms.conf`.

Reload supervisor configuration:

    sudo supervisorctl update

Gunicorn processes should then be running on port 8000 and 8001. If not, check the logs in `/var/log/supervisor` for errors.

Also, there should be asynchronous celery workers running for the lms and the cms. Run the following command to check if everything runs correctly:

    $ sudo supervisorctl status
    cms                              RUNNING   pid 3070, uptime 0:00:09
    cms:cms_default_1                RUNNING   pid 3068, uptime 0:00:09
    cms:cms_high_1                   RUNNING   pid 3071, uptime 0:00:09
    cms:cms_low_1                    RUNNING   pid 3069, uptime 0:00:09
    lms                              RUNNING   pid 3092, uptime 0:00:06
    lms:lms_default_1                RUNNING   pid 3096, uptime 0:00:06
    lms:lms_high_1                   RUNNING   pid 3094, uptime 0:00:06
    lms:lms_high_mem_1               RUNNING   pid 3095, uptime 0:00:06
    lms:lms_low_1                    RUNNING   pid 3091, uptime 0:00:06

At any point, to reload the gunicorn processes, run either:

    sudo supervisorctl restart lms
    sudo supervisorctl restart cms

And to reload all lms or cms-related processes, run either:

    sudo supervisorctl restart lms:
    sudo supervisorctl restart cms:

### Nginx

Nginx is the de facto web server traditionally used in combination with Open edX. Nginx serves two purposes:

* Proxy to gunicorn for dynamic web pages
* Directly serve static files from disk

Start by installing Nginx:

    sudo apt install nginx

Edit [`./config/nginx/sites-enabled/lms.conf`](./config/nginx/sites-enabled/lms.conf) and add it to `/etc/nginx/sites-enabled/lms.conf`.

Edit [`./config/nginx/sites-enabled/cms.conf`](./config/nginx/sites-enabled/cms.conf) and add it to `/etc/nginx/sites-enabled/cms.conf`.

In the above configuration files, you should check that the domain names and the static assets folders are correct.

Reload nginx configuration with:

    sudo systemctl reload nginx.service

At that point, the LMS and the CMS should be available at the urls you have specified in the Nginx configuration files. If not, error logs should be available in `/var/log/nginx`.
