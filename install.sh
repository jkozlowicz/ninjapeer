apt-get install -y python-dev
apt-get install -y python-pip
/usr/bin/yes | pip install virtualenv
mkdir ~/.virtualenvs
pip install virtualenvwrapper
export WORKON_HOME=~/.virtualenvs
echo(". /usr/local/bin/virtualenvwrapper.sh") >> ~/.bashrc
mkvirtualenv ninjapeer
workon ninjapeer
/usr/bin/yes | git clone https://github.com/jkozlowicz/ninjapeer.git
/usr/bin/yes | pip install -r ninjapeer/reqirements.txt
