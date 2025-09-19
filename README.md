# Collection of tools to migrate customer to dot1x with Cisco Catalyst
+ Customer uses cat2k and cat9400 (Seeddevice) If other devices are used change the . 
+ Seedswitch is used and Network is crawled via cdp (only platforms in init file will be checked)
+ Need "```decription #NoAuth#```_and_whatever_needet" on interface which should not change
## Generate an interface Report
+ creates Excelfile with usefull informations per interface
* sheetname is date when its created
## Configure Ports from file where hostname and port is in a file
+ copy column a and b from Excel after filtering the requested Interface
* It starts wit the seeddevice, checks if the device is in the list of the devices to chnage.
* It does a sh cdp neighbor for crawling the net. 
    * it reads the current config, then it configure the dot1x-config.
    * it shuts and unshuts the port to trigger an authentication
    * it checks the authentication status after 4 seconds 
    * it writes all that in a *.cfg file one per switch
* Does the same on every other switch and port in list
## Configure Portsettings when spezial Vendor is seen on an Interface
+ does live mac vendor lookup to API and configures the Interfaces
* It connects to the seeddevice and does a cdp neighbor for crawling the net.
    * reads the mac table.
    * check every mac for the vendor 
    * if it is seen on a TenGig Interface its ignored.
    * checks if the Interface is already configured
    * configure the Interface

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


## ToDos
# vendor_dot1x
* Check mac count on the Interface before configuring 
* Check every interface 