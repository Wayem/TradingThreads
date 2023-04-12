https://pypi.org/project/TA-Lib/

Raspeberry pi installation:

1. Generate Github SSH key
https://docs.github.com/fr/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent

2. Download git repo

3. python3 -m venv ./.venv
4. source .venv/bin/activate
5. sudo apt-get install libatlas-base-dev
6. TA-LIB dependencies:
   $ wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
   $ tar -xzf ta-lib-0.4.0-src.tar.gz
   $ cd ta-lib/
   $ ./configure --prefix=/usr
   $ make
   $ sudo make install
6. pip install -r requirements.txt
7. Add main.sh at startup:
   $ sudo crontab -e 
   add at the end of file: @reboot .../main.sh
8. chmod +x .../main.sh
9. remote.it
