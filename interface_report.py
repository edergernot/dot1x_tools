from dotenv import load_dotenv
import os
from netmiko import ConnectHandler
from datetime import datetime
from rich.console import Console
import pandas as pd
import json
from init import *
import sys
from multiprocessing.dummy import Pool as ThreadPool

### Init Vars 
starttime = datetime.now()
switches = []
switches_checked = []
Unconfigured_ports = []
All_Interfaces:list = []

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

def mac_normalizer(MAC_ADDR:str):
    mac:str=MAC_ADDR.replace(".", "")
    mac=mac.replace(":","")
    mac=mac.replace("-","")
    mac=mac.lower()
    return (mac)

def interface_cdp(ssh,interface)->str: 
    cdps = ssh.send_command(f"show cdp neighbor {interface["port"]}", use_textfsm=True)
    neighbor_name=""    
    if type(cdps) == list:
        neighbor_count=len(cdps)  
        if neighbor_count > 1:
            for neighbor in cdps:
                neighbor_name+=neighbor["neighbor_name"]+","
        neighbor_name=cdps[0]["neighbor_name"]
        #print(f"CDP-Nei: {neighbor_name}")
        return(neighbor_name)
    #print(f"CDP-Nei: {neighbor_name}")
    return ("")

def generate_interfaceconfig_dict(interface_config:str)->dict:
    # Generate a dict from interface configurations
    interface:dict = {}
    interface["speed"]="auto"
    interface["duplex"]="auto"
    interface["switchport_mode"]="Not configured!"
    for line in interface_config.split("\n"):
        if len(line)<=2:
            continue
        if line == "no switchport":
            interface["switchport_mode"]="routed"
        if "switchport mode" in line:
            interface["switchport_mode"]=line.split()[-1].strip()
            continue
        if "description" in line:
            interface["description"]=line.split("description")[1].strip()
            continue
        if "switchport access vlan" in line:
            interface["vlan"]=line.split("vlan")[1].strip()
            continue
        if "switchport voice vlan" in line:
            interface["voice-vlan"]=line.split("vlan")[1].strip()
            continue
        if "port-security maximum" in line:
            interface["max_port_security"]=line.split("port-security")[1].strip()
            continue
        if "storm-control broadcast" in line:
            interface["stormctl_broadcast"]=line.split("storm-control broadcast")[1].strip()
            continue
        if "storm-control multicast" in line:
            interface["stormctl_multicast"]=line.split("storm-control multicast")[1].strip()
            continue
        if "access-session port-control auto" in line:
            interface["Dot1x"] = "Enabled"
            continue
        if "mab" in line:
            interface["Mab"] = "Enabled"
            continue
        if "service-policy type" in line:
            interface["ServicePolicy"]=line.split("service-policy type")[1].strip()
            continue
        if "dot1x pae" in line:
            interface["Dot1x_Int_Type"]=line.split("dot1x pae")[1].strip()
            continue
        if "speed" in line:
            interface["speed"]=line.split("speed")[1].strip()
            continue
        if "duplex" in line:
            interface["duplex"]=line.split("duplex")[1].strip()
        if "channel-group" in line:
            interface["portchannel"]=line.split("channel-group")[1].strip()
        if "switchport trunk allowed vlan" in line:
            try:
                vlans=interface["trunk_vlans"]
                vlans_add=line.split("add")[1].strip()
                interface["trunk_vlans"]=vlans+vlans_add
                continue
            except KeyError:
                interface["trunk_vlans"]=line.split("switchport trunk allowed vlan")[1].strip()
                continue
        if "device-tracking attach-policy" in line:
            interface["device_tracking_policy"]=line.split("device-tracking attach-policy")[1].strip()
        if "spanning-tree" in line:
            try:
                stp_setting=interface["spanning-tree"]
                stp_additional_setting=line.split("spanning-tree")[1].strip()
                interface["spanning-tree"]=stp_setting+","+stp_additional_setting
                continue
            except KeyError:
                interface["spanning-tree"]=line.split("spanning-tree")[1].strip()
                continue
    return(interface)

def check_link(interface,ssh):
    '''Returns the status, speed and duplex of interface'''
    speed = ssh.send_command(f"show interface {interface['port']} status", use_textfsm=True)
    if type(speed) == list:
        return {"current_status":speed[0]['status'], "current_speed":speed[0]['speed'], "current_duplex":speed[0]["duplex"]}
    return

def generate_excel(interfaces:list):
    try:
        os.remove("interface_cfg.xlsx")
    except Exception as e:
        print(e)
    df = pd.DataFrame(interfaces)
    writer = pd.ExcelWriter('interface_cfg.xlsx', engine='xlsxwriter')

    # Write the dataframe data to XlsxWriter. Turn off the default header and
    # index and skip one row to allow us to insert a user defined header.
    sheetname= starttime.strftime("%d.%m.%Y")
    df.to_excel(writer, sheet_name=sheetname, startrow=1, header=False, index=False)

    # Get the xlsxwriter workbook and worksheet objects.
    workbook = writer.book
    
    worksheet = writer.sheets[sheetname]

    # Get the dimensions of the dataframe.
    (max_row, max_col) = df.shape

    # Create a list of column headers, to use in add_table().
    column_settings = [{'header': column} for column in df.columns]

    # Add the Excel table structure. Pandas will add the data.
    worksheet.add_table(0, 0, max_row, max_col - 1, {'columns': column_settings}, )

    # Make the columns wider for clarity.
    worksheet.set_column(0, max_col - 1, 15)

    # Close the Pandas Excel writer and output the Excel file.
    writer._save() # type: ignore

def count_mac_address(interface,ssh):
    mac = ssh.send_command(f"show mac address-table interface {interface['port']}",use_textfsm=True )
    if type(mac) != list:
        return 0
    return len(mac)
   
def json_dump(interfaces):
    with open("jsondump.json", 'w') as out:
        for interface in interfaces:
            json_out = json.dumps(interface) + '\n'
            out.write(json_out)

def interface_report(IP):
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
        print(e)
        print ('#'*40)
        return
    hostname = ssh.find_prompt()[:-1]
    console.print(f"Connected to {hostname}", style="green")
    switches_checked.append(IP)
    
    ### Check CDP Neighbors and add Switches if 9200

    cdps=ssh.send_command("show cdp neighbor detail", use_textfsm=True)
    for cdp in cdps:
        for platform in platforms:
            if platform  in cdp["platform"]: # type: ignore
                switches.append(cdp['mgmt_address']) # type: ignore
    
    ### Interface Status, to get the Interfaces ###
    interface_status=ssh.send_command("show interface status", use_textfsm=True)
    for interface in interface_status:
        interface_config_dict:dict={}
        interface_config_dict['host']=hostname
        if  interface['port'][:2]=='Ap' : # type: ignore # Ignore AP Ports
            continue
        #if interface["name"]=='' and interface['vlan_id'] == '1':
        #    interface["Device"]=hostname
        #    Unconfigured_ports.append(interface)
        interface_config_command : str =f'show run interface {interface['port']}' # type: ignore
        interface_config_dict["interface"]=interface['port'] # type: ignore
        interface_config=ssh.send_command(interface_config_command).split("!")[1] # type: ignore
        generated_intconfig_dict:dict=generate_interfaceconfig_dict(interface_config)
        generated_intconfig_dict['macaddress_count']=count_mac_address(interface,ssh)
        current_status : dict =check_link(interface, ssh) # type: ignore
        for key in current_status.keys():
            interface_config_dict[key]= current_status[key]
        for key in generated_intconfig_dict.keys():  
            interface_config_dict[key]=generated_intconfig_dict[key]
        interface_config_dict["cdp"]=interface_cdp(ssh,interface)
        All_Interfaces.append(interface_config_dict)
        #print(f"Check {interface_config.split("\n")[1]}")
    print(f"{len(interface_status)} interfaces checked on {hostname}")
    ssh.disconnect()
        
if __name__ == "__main__":
    if len(sys.argv) == 1: # no device-file was added. Crawl from seedswitch
        interface_report(seeddevice)
        for switch in switches:
            interface_report(switch)
    else:  # device-file added. do Multitasking!
        file = sys.argv[1]
        devices = create_devicelist(file)
        if len(devices) <= 30 :
            num_threads=len(devices)
        else:
            num_threads=30
        threads = ThreadPool( num_threads )
        results = threads.map( interface_report, devices )
        threads.close()
        threads.join()
    print("#"*20)
    print("Generate Excel")
    generate_excel(All_Interfaces)
    print("save JsonFile")
    json_dump(All_Interfaces)
    print("#"*20)
    print(f"Switches checked {len(switches_checked)}: {switches_checked}\n")

    ### Timemessurement
    endtime = datetime.now()
    duration = endtime - starttime
    total_seconds = duration.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    tenths = int((total_seconds - int(total_seconds)) * 10)
    print(f"Finished in {hours:02}:{minutes:02}:{seconds:02}:{tenths} ")
   