# Collection of tools to migrate customer to dot1x with Cisco Catalyst
+ Basic dot1x settings (aaa, service policies and so on) are allready done. 
+ Seedswitch is used and Network is crawled via cdp (only platforms in init file will be checked)
+ Need "```decription #NoAuth#```_and_whatever_needet" on interface which should not change, for exmple:
```
interface GigabitEthernet 1/0/1
 description #NoAuth# Fileserver FS002
 switchport mode access
 ...
 ```

# Setup
Astrals UV is used for installing the packages<br>
see: https://docs.astral.sh/uv/getting-started/installation/
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

Check the requested dot1x settings in the init.py file


## Generate an interface Report
### ```uv run interface_report.py``` 
+ creates Excelfile and Json-File with usefull informations (speed, duplex, dot1x, vlan, ..) per interface
* sheetname is date when its created.
### ```uv run interface_report.py device-file.csv```
* When adding the filename of the device_file.csv which was done in Networkdump it can do multitasking. It only uses the IP-Adress out of the file

## Configure dot1x to Ports from a file where hostname and port is in a file
### ```uv run dot1x_from_file.py``` 
+ copy column a and b from Excel after filtering the a file named: portfile.txt
* It starts wit the seeddevice, checks if the device is in the list of the devices to change.
* It does a sh cdp neighbor for crawling the net. 
    * it reads the current config, then it configure the dot1x-config.
    * it shuts and unshuts the port to trigger an authentication
    * it checks the authentication status after 4 seconds 
    * it writes all that in a *.cfg file one per switch
* Does the same on every other switch and port in list

## Configure any Settungs to Interfaces from File 
### ```uv run int_config_from_file.py```
+ modify the requested configuration in the file 
+ copy column a and b from Excel after filtering the a file named: portfile.txt
* It starts wit the seeddevice, checks if the device is in the list of the devices to change.
* It checks if its connected to a device from the portfile and configues the ports from the portfile.
### ```uv run int_config_from_file.py device-file.csv``` 
* It don't crawl though the net, it uses the devices IP-Address from the csv-file and connects to it.
* It checks if its connected to a device from the portfile and configues the ports from the portfile.

## Configure Portsettings when spezial Vendor is seen on an Interface
### ```uv run vendor_dot1x.py``` 
+ does live mac vendor lookup to API and configures the Interfaces
* It connects to the seeddevice and does a cdp neighbor for crawling the net.
    * reads the mac table.
    * check every mac for the vendor 
    * if it is seen on a TenGig Interface its ignored.
    * checks if the Interface is already configured
    * configure the Interface


# ToDos
## vendor_dot1x
* Check mac count on the Interface before configuring 
* Check every interface 
## dot1x portconfiguration
* use as a seperate file 
* Make Guest-Vlan value configureable in the init.py
