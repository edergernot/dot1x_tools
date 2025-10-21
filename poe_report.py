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

def generate_excel(interfaces:list):
    try:
        os.remove("PoE_Buget.xlsx")
    except Exception as e:
        print(e)
    df = pd.DataFrame(interfaces)
    writer = pd.ExcelWriter('PoE_Buget.xlsx', engine='xlsxwriter')

    # Write the dataframe data to XlsxWriter. Turn off the default header and
    # index and skip one row to allow us to insert a user defined header.
    sheetname= starttime.strftime("%d.%m.%Y %H%M")
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
   
def json_dump(interfaces):
    with open("jsondump.json", 'w') as out:
        for interface in interfaces:
            json_out = json.dumps(interface) + '\n'
            out.write(json_out)

def poe_report(IP):
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
    
    ### Check CDP Neighbors and add Switches if in supported Platforms

    cdps=ssh.send_command("show cdp neighbor detail", use_textfsm=True)
    for cdp in cdps:
        for platform in platforms:
            if platform  in cdp["platform"]: # type: ignore
                switches.append(cdp['mgmt_address']) # type: ignore

    
    version_output=ssh.send_command("show version", use_textfsm=True)
    Devicetype = version_output[0]['hardware'][0]

    # Check Poe Budget

    power_module_output=ssh.send_command("show power inline")   
    for line in power_module_output.split('\n'):
        first=False
        try:
            first=int(line.split()[0])
        except Exception as e:
            pass
        if first:
            power_mod={}
            power_mod['Devicename']=hostname
            power_mod['Devicetype']=Devicetype
            power_mod['Module']=line.split()[0]
            if power_mod['Module'] != "1":
                Devicetype = version_output[0]['hardware'][int(power_mod['Module'])-1]
            power_mod['Available']=line.split()[1]
            power_mod['Used']=line.split()[2]
            power_mod['Remaining']=line.split()[3]
            All_Interfaces.append(power_mod)
    ssh.disconnect()   

if __name__ == "__main__":
    if len(sys.argv) == 1: # no device-file was added. Crawl from seedswitch
        poe_report(seeddevice)
        for switch in switches:
            poe_report(switch)
    else:  # device-file added. do Multitasking!
        file = sys.argv[1]
        devices = create_devicelist(file)
        if len(devices) <= 30 :
            num_threads=len(devices)
        else:
            num_threads=30
        threads = ThreadPool( num_threads )
        results = threads.map( poe_report, devices )
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
   