# Collection of tools to migrate Customer to dot1x with Cisco Catalyst
+ Customer uses cat 2k 
+ Seedswitch is used and Network is crawled via cdp 
+ Need "decription #NoAuth#"  on interface which should not change
## Generate an interface Report
+ creates Excelfile with usefull informations per interface
## Configure Ports from file where hostname and port is in a file
+ copy column a and b from Excel after filtering the requested Interface
## Configure Portsettings when spezial Vendor is seen on an Interface
+ does live mac vendor lookup to API and configures the Interfaces 

# Setup
Astrals UV is used for installing the packages
```
git clone https://github.com/edergernot/dot1x_tools
cd dot1x_tools
uv init
uv add -r .\requirements.txt
```
create a .env file with your credentials
create an API key on https://my.maclookup.app/login
```
SSH_USERNAME=MySSHUsername
SSH_PASSWORD=MySSHSecretPassword
MAC-API-KEY=APIkeyFromMacLookupApp1234576
```
modify the init.py file with the infos and the required Dot1x Interface Config you need.

check the output for the vendor with an API test.
```
curl https://api.maclookup.app/v2/macs/{Your Mac Address}
```
use string returned in the "company" key.
