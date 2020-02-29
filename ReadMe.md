## Project Description
This is a low power, low cost, low environmental impact irrigation system designed to produce better apple and vegetable yields for myself. I use repurposed 55 gallon olive oil drums as rain barrels controlled by a $10 Raspberry Pi Zero W. The logic is a Python script that connects to The Weather Network's API and activates a solenoid valve only if it will not rain today or tomorrow.  
  
This can be adapted to many uses, feel free to hack it up.

## Pi Configuration
Check version or python using: ``python -V``  
If your version is not 3.x, we'll fix that.  
Python3 has been included on Rasbian images for 2 years now, so you probably have it installed.  
If you are using Raspbian Lite or running headless, you may have an older pip installation.  
Check your version using: ``pip -V``  
We want to see a reference to Python 3.x.  
If you have an older version, run the following commands:
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
You can confirm your changes using the following command: ``tail ~/.bashrc``  
Now run your bashrc script to initialize your changes with the following command:
```
source ~/.bashrc
```

## Clone The Repo
Check if you have git installed with ``git --version``  
If you don't have it, run the following command:
```
sudo apt-get install git
```
Now navigate to the directory in which you would like to add the irrigation directory and run the following command:
```
git clone https://github.com/coreycougle/irrigation.git
```

## Email notification config
We need to use a Gmail account to send emails from when we get bad data from the weather network.  
I recommend creating a new gmail account as we will be using a less than ideal authentication method.  
Set up 2-factor authentication.  
Go to https://support.google.com/accounts/answer/185833 and create an app password to be used (ensure you are in the gmail account you want this script to access).  

## Update Config File
Add your Weather Network API key from https://store.api.pelmorex.com  
Add your country eg. ``CA`` or ``US``  
Add your city eg. ``Toronto`` or ``New-York``  
Add your GPIO pins in BCM format eg. ``23`` or ``24,25``  
Add your sender and receiver email accounts eg. ``your.address@gmail.com``  
Add your app password that you had generated in the previous section eg. ``yourapppassword``

## Scheduling
If you cloned the irrigation project somewhere other than the default pi home directory, edit irrigation.crontab to use the path to your copy of irrigation.py.  
Load the crontab file using the following command:
```
crontab irrigation.crontab
```
This will insert the schedule to be run as your username.  
If you need to adjust the crontab, you can run ``crontab -e``, select your preferred text editor, then make changes as necessary.  
You can list cron jobs using ``crontab -l``

## Diagnostics
To check that the circuit is receiving signal correctly, run irrigation.py with the -testsignal argument:
```
python irrigation.py -testsignal
```
You should see the test led flash 3 times.  

To check that the valves are connected correctly, run irrigation.py with the -testvalve argument:
```
python irrigation.py -testvalve
```
You should hear or see the valves open for 5 seconds each.

To check that the email configuration is correct, run irrigation.py with the -testnotify argument:
```
python irrigation.py -testnotify
```
You should receive a notification email to the receiver email account in about 5 seconds.

