'''Used for changing Interface configuration on every Interface in a File (taken from Interface_cfg.xml column a and b)  also add device-file possible (no Multitasking)'''


from dotenv import load_dotenv
import os
from netmiko import ConnectHandler
import requests
from datetime import datetime
import time
from rich.console import Console
import urllib3
from init import *
import sys

urllib3.disable_warnings() ### Disable Warning if SSL-Decryption is enabled

# Interface Config
int_config = ["switchport trunk native vlan 55",
             "spanning-tree portfast trunk",
             "switchport mode trunk",
             "no switchport access vlan 55",
             "no switchport port-security",
             "no switchport port-security max 3",
             "no switchport port-security aging time 30",
             "speed auto",
             "duplex auto"]

### Init Vars 
starttime = datetime.now()
switches = []
switches_checked = []
OUI_Vendor:dict = {}
Vendor_OUI:dict ={}
Unconfigured_ports = []

### Load environment
console=Console()  # used for colored Output
load_dotenv()
SSH_User=os.getenv("SSH_USERNAME")
SSH_Pass=os.getenv("SSH_PASSWORD")

def create_devicelist(file):
    devices = []
    with open(file, "r") as f:
        file = f.read()
    for line in file.split("\n"):
        if len(line)==0:
            continue
        if "Name,Type,IP-Address" in line:
            continue
        ip_addr=line.split(",")[2]
        devices.append(ip_addr)
    return(devices)

def generate_dict_from_file(file):
    devices={}
    with open(file) as f:
        filedata=f.read()
    for line in filedata.split("\n"):
        device = line.split()
        if device == []:
            continue
        ports = devices.get(device[0])
        if not ports:
            devices[device[0]]=[device[1]]
        else:
            devices[device[0]].append(device[1])
    return (devices)

def change_interface(ssh,interface):
    hostname = ssh.find_prompt()[:-1]
    config_old=ssh.send_command(f"show run interface {interface}")
    with open(f"{hostname}.cfg", "a") as f:
        f.write("#### Old Config ####\n")
        f.write(config_old)
        int_config_interface=[f"interface {interface}"]+int_config
        config_int=ssh.send_config_set(int_config_interface, read_timeout=30, cmd_verify=True)
        f.write("#### config change ####\n")
        f.write(config_int)

def change_config(IP,ports):
    if IP in switches_checked: ### Switch allready checked
        return
    cdps=[]
    device ={'device_type':'cisco_ios',
             'host':IP,
             'username':SSH_User,
             'password':SSH_Pass}
    print('#'*40)
    print (f"Try to connect to device {IP}")
    try:  # Try to do a SSH - Session
        ssh = ConnectHandler(**device)
    except Exception as e:
        console.print (f"SSH did not work for Device: {IP}", style="red")
        print ('#'*40)
        return
    console.print(f"Connected to {ssh.find_prompt()[:-1]}", style="green")
    switches_checked.append(IP)
    hostname = ssh.find_prompt()[:-1]
    with open(f"{hostname}.cfg", "w") as f:  ## clear file
        pass
    ### Check CDP Neighbors and add Switches
    cdps=ssh.send_command("show cdp neighbor detail", use_textfsm=True)
    for cdp in cdps:
        for platform in platforms:
            if platform in cdp["platform"]: # type: ignore
                switches.append(cdp['mgmt_address']) # type: ignore
    try:
        ports_to_change=ports[hostname]
    except KeyError:
        console.print(f"No Ports to Change on Switch {hostname}", style="yellow")
        return
    print(f"Changing Ports {ports_to_change}")
    for interface in ports_to_change:
        change_interface(ssh,interface)
        
if __name__ == "__main__":
    ports=generate_dict_from_file("portfile.txt")
    print(ports)
    if len(sys.argv) == 1: # no device-file was added. Crawl from seedswitch
        change_config(seeddevice,ports)
        for switch in switches:
            change_config(switch,ports)
    else:  # device-file added. do Multitasking!
        file = sys.argv[1]
        devices = create_devicelist(file)
        print (devices)
        for device in devices:
            change_config(device,ports)
    #### Timemessurement
    endtime = datetime.now()
    duration = endtime - starttime
    total_seconds = duration.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    tenths = int((total_seconds - int(total_seconds)) * 10)
    print(f"Finished in {hours:02}:{minutes:02}:{seconds:02}:{tenths} ")
