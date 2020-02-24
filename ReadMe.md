
## Pi Configuration
Check version or python using:
```
python -V
```
If your version is not 3.x, we'll fix that.
Python3 has been included on Rasbian images for 2 years now, so you probably have it installed.
If you are using Raspbian Lite or running headless, you may have an older pip installation. Check your version using:
```
pip -V
```
We want to see a reference to Python 3.x. If you have an older version, run the following commands:
```
sudo apt-get update
sudo apt-get install python3-pip
```
Now we will update our bashrc to alias python3 and pip3. Run the following command:
```
nano ~/.bashrc
```
At the bottom of the file, add the following lines:
```
alias python='/user/bin/python3'
alias pip=pip3
```
Save and exit nano using the save (ctrl + o) and exit (ctrl + x) commands.
You can confirm your changes using the following command:
```
tail ~/.bashrc
```
Now run your bashrc script to initialize your changes with the following command:
```
source ~/.bashrc
```

## Update Config File
Add your Weather Network API key from https://store.api.pelmorex.com
Add your country eg. CA or US
Add your city eg. Toronto or New-York
Add your GPIO pins in BCM format eg 23 or 24 or 25

## Scheduling
Use cron to schedule execution of Irrigation.py (More to come)

## Diagnostics
To Do

