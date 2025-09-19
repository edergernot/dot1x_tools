'''Used for enabling dot1x on every Interface on every Interface in a File (taken from Interface_cfg.xml column a and b)  '''


from dotenv import load_dotenv
import os
from netmiko import ConnectHandler
import requests
from datetime import datetime
import time
from rich.console import Console
import urllib3
from init import *

urllib3.disable_warnings() ### Disable Warning if SSL-Decryption is enabled

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
MAC_API_KEY=os.getenv("MAC-API-KEY")

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


def mac_normalizer(MAC_ADDR:str):
    mac:str=MAC_ADDR.replace(".", "")
    mac=mac.replace(":","")
    mac=mac.replace("-","")
    mac=mac.lower()
    return (mac)

def vendor(MAC_ADDR):
    mac = mac_normalizer(MAC_ADDR)
    OUI = mac[:6]
    try: # check if allready resolved
        vendor=OUI_Vendor[OUI]
        return(vendor)
    except KeyError:
        pass
    URL = f"https://api.maclookup.app/v2/macs/{mac}/company/name?apiKey={MAC_API_KEY}"
    responce=requests.get(URL, verify=False)
    while responce.status_code == 429:  # Hit limit 
        time.sleep(1)
        responce = requests.get(URL)
    if responce.status_code == 200:
        OUI_Vendor[OUI]=responce.text
        try:
            Vendor_OUI[responce.text].append(OUI)  #add OUI to Vendor name List
        except KeyError:
            Vendor_OUI[responce.text]=[OUI]
        #print(f"{OUI} : {responce.text}")
        return(responce.text)
    return ("#Not Resolved#")
   
def allready_dot1x(ssh,interface):
    config=ssh.send_command(f"show run interface {interface}")
    if "access-session port-control auto" in config:
        return True
    return False

def change_interface(ssh,interface):
    hostname = ssh.find_prompt()[:-1]
    config_old=ssh.send_command(f"show run interface {interface}")
    with open(f"{hostname}.cfg", "a") as f:
        f.write("#### Old Config ####\n")
        f.write(config_old)
        if "description #NoAuth#" in config_old:
            print(f"Ignore that Interface because of special description")
            f.close()
            return
        print(f"###  Configure {interface} ###\n")
        dot1x_config_interface=[f"interface {interface}"]+dot1x_config
        config_dot1x=ssh.send_config_set(dot1x_config_interface, read_timeout=30, cmd_verify=True)
        #config_dot1x="Text"
        f.write("#### config change ####\n")
        f.write(config_dot1x)
        shutdown=[f"interface {interface}","shutdown"]
        no_shutdown=[f"interface {interface}", "no shutdown"]
        output_shut=ssh.send_config_set(shutdown,read_timeout=30, cmd_verify=True)
        time.sleep(1)
        output_no_shut=ssh.send_config_set(no_shutdown,read_timeout=30, cmd_verify=True)
        time.sleep(4)
        authentication = ssh.send_command(f"show authentication session interface {interface} detail")
        f.write("#### Check Authentication #####\n")
        f.write(authentication)
        if "Vlan: 666" in authentication:
            console.print(f"#### Interface {interface} in Guest VLAN Please Check #####", style="red")
        else:
            console.print(f"#### Interface {interface} Configured Successfully #####", style="green")
        #time.sleep(10)

def dot1x_work(IP,ports):
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
    console.print(f"Connected to {ssh.find_prompt()[:-1]}", style="yellow")
    switches_checked.append(IP)
    hostname = ssh.find_prompt()[:-1]
    with open(f"{hostname}.cfg", "w") as f:  ## clear file
        pass
    ### Check CDP Neighbors and add Switches
    cdps=ssh.send_command("show cdp neighbor detail", use_textfsm=True)
    for cdp in cdps:
        if 'cisco C9200' in cdp["platform"]: # type: ignore
            switches.append(cdp['mgmt_address']) # type: ignore
    try:
        ports_to_change=ports[hostname]
    except KeyError:
        print(f"No Ports to Change on Switch {hostname}")
        return
    print(f"Changing Ports {ports_to_change}")
    for interface in ports_to_change:
        change_interface(ssh,interface)
        

if __name__ == "__main__":
    ports=generate_dict_from_file("Ibiden-Switches.txt")
    dot1x_work(seeddevice,ports)
    for switch in switches:
        dot1x_work(switch,ports)
    #### Timemessurement
    endtime = datetime.now()
    duration = endtime - starttime
    total_seconds = duration.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    tenths = int((total_seconds - int(total_seconds)) * 10)
    print(f"Finished in {hours:02}:{minutes:02}:{seconds:02}:{tenths} ")
