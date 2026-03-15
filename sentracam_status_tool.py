import requests
import csv
import os
import sys
from requests.auth import HTTPDigestAuth
from datetime import datetime
from dotenv import load_dotenv


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

username = os.getenv("username")
idUser = os.getenv("idUser")
counter = 0
api_token = os.getenv("victron_token")
url = f"https://vrmapi.victronenergy.com/v2/users/{idUser}/installations"
all_battery_units = []
all_battery_units_mapped = []
low_battery_units = []
depleted_battery_units = []
net_array = []
rd_down = []
fisheyes = []

netsheet = resource_path("net_sheet.csv")
mapsheet = os.path.join(BASE_DIR, "map_sheet.csv")

headers = {
    "idUser": f"{idUser}",
    "X-Authorization": f"Token {api_token}"
}

response = requests.get(url, headers=headers)

def main():
    while True:
        global counter
        if counter < 1:
            print("netsheet path:", netsheet)
            print("Exists:", os.path.exists(netsheet))

            generate_net_array()
            print("Net array generated.")
            initialize_program = input(
                'Create or update mapped units sheet? (Hit Y if this is your first time running the program) Y or N: '
            )
            if initialize_program.lower()[:1] == "y":
                counter += 1
                all_unit_battery_health()
                with open(mapsheet, 'w', newline='') as csvfile:
                    fieldnames = ["name", "trailer"]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(all_battery_units_mapped)
                    print('CSV file generated.')
                    print('Initialization complete. ')
            else:
                counter += 1
                print('Populating mapped unit array from csv...')
                with open(mapsheet, "r", newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        all_battery_units_mapped.append(row)
                continue
                
        print("Command menu: ")
        print("1. Check if unit is installed in VRM")
        print("2. Check individual trailer battery health using its MU#")
        print("3. Print low battery list")
        print("4. Print depleted battery list")
        print("5. Print all battery list")
        print("6. Check individual trailer battery health using its RD#")
        print("7. Compare mesh and issue reports")
        print("8. Update unit map sheet")
        print("9. Print unit map sheet")
        print("10. Search C:\\Temp directory for fisheye snapshots of a specific unit for solar panel analysis")
        
        cmd = input("Enter a number 1-10: ")
        if cmd == "1":
            install_checker()
        elif cmd == "2":
            unit = str(input('Input MUXXXX: '))
            unit_battery_health(unit)
        elif cmd == "3":
            low_battery_list()
        elif cmd == "4":
            depleted_battery_list()
        elif cmd == "5":
            all_battery_list()
        elif cmd == "6":
            while True:
                unit = str(input('Input RDXXXX to fetch battery. Unit must be 3300 or greater: '))
                if unit.lower() == "quit":
                    break
                else:
                    get_rd_battery(unit)
        elif cmd == "7":
            compare_reports()
        elif cmd == "8":
                all_unit_battery_health()
                with open(mapsheet, 'w', newline='') as csvfile:
                    fieldnames = ["name", "trailer"]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(all_battery_units_mapped)
        elif cmd == "9":
            for row in all_battery_units_mapped:
                print(row["name"] + " - " + row["trailer"])
        elif cmd == "10":
            unit = input('Enter unit to search for in C:\\Temp: ')
            matches = file_search(unit)
        
        elif cmd == "cls" or cmd == "clr" or cmd == "clear":
            clear_terminal()
        elif cmd == "quit" or cmd == "exit":
            sys.exit()

        else:
            print('Invalid command. Please enter a number one through ten.')

def clear_terminal():
    os.system('cls')

def file_search(unit, root=r'C:\Temp'):
    results = []

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if unit.lower() in filename.lower():
                print(f'Found snapshot: {filename}')
                results.append(os.path.join(dirpath, filename))
    
    if results:
        for file in results:
            print(f'{file}')
    return results

def compare_reports():
    print('Usage: Download both the mesh outage sheet and issue sheet. Name one "mesh.csv", and the other "issue.csv".')
    mesh_outage = os.path.join(os.path.expanduser("~"), "Downloads", "filtered_mesh_vpn.csv")
    erp_export = os.path.join(os.path.expanduser("~"), "Downloads", "Issue.csv")

    mesh_array = []
    erp_array = []
    missing = []

    with open(mesh_outage, 'r', newline='') as csvfile:
        linereader = csv.reader(csvfile)
        for line in linereader:
            mesh_array.append(line[0])


    with open(erp_export, 'r', newline='') as csvfile:
        linereader = csv.reader(csvfile)
        for line in linereader:
            #print(line[1])
            if line[1] != 'Subject':
                erp_array.append(line[1])

    for mesh in mesh_array:
        found = False
        for line in erp_array:
            if mesh in line:
                found = True
                #print(f'Found {mesh} in {line}')
                break
        if not found:
            missing.append(mesh)

    print('\nMissing units: ')
    for row in missing:
        if row != 'Agent Name':
            print(row)


def generate_net_array():
    with open(netsheet, "r", newline='') as csvfile:
        linereader = csv.reader(csvfile)
        for row in linereader:
            if len(row[0]) == 6:
                #print(row[0][2:4])
                net_array.append(row)

    
def naming_conventions():
    print("Adjusting naming conventions...")
    for row in all_battery_units:
        if row["name"][:3] != "SC-":
            row["name"] = "SC-" + row["name"]

    print('Mapping trailers to head units...')
    rd_battery_map()

def get_rd_battery(unit):
    found = False
    for row in all_battery_units_mapped:
        #print(row)
        if unit[-4:] == row['name'][-4:]:
            print('Matched, fetching battery health')
            unit_battery_health(row['trailer'])
            found = True
            break
    if found != True:
        print('Unit not found.')
        

def low_battery_fisheye_screenshotter(): 
    print("Fisheye starting")
    timestamp = datetime.now().strftime("%Y-%m-%d")
    save_dir = os.path.join(os.path.expanduser("~"),"Documents", "Python work scripts", "fisheye_screenshots")
    fish_dir = f"{timestamp}_fisheye_screenshots"
    time_path = os.path.join(save_dir, fish_dir)
    os.makedirs(time_path, exist_ok=True)    
    for row in net_array:
        for unit in rd_down:
            if row[0][-4:] == unit["name"][-4:]:
                #rdpath = os.path.join(save_dir, row[0])
                #os.makedirs(rdpath, exist_ok=True)
                print(f'{row[0]} found in netsheet. Fisheye ip address is: {row[5]}')
                combination = {
                    "Unit:": row[0],
                    "Fisheye IP:": row[5]
                }
                fisheyes.append(combination)

                print("Screenshotting...")
                try:
                    #rdpath = os.path.join(save_dir, row[0])
                    #os.makedirs(rdpath, exist_ok=True)
                    url = f"http://{row[5]}/cgi-bin/snapshot.cgi?channel=1"

                    fishuser = os.getenv("fishuser")
                    fishpass = os.getenv("fishpass")

                    response = requests.get(url, auth=HTTPDigestAuth(f"{fishuser}",f"{fishpass}"), timeout=30)
                    response.raise_for_status()

                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    filename = row[0] + "_" + timestamp + ".jpg"
                    filepath = os.path.join(time_path, filename)

                    with open(filepath, "wb") as f:
                        f.write(response.content)
                    print(f"Saved to {filepath}")
                    
                except requests.exceptions.RequestException as e:
                    print(f"Failed:  {row[5]} {e}")
                    #print("Removing empty directory")
                    #os.remove(filepath)
    return

def install_checker():
    idUser = os.getenv("idUser")
    api_token = os.getenv("victron_token")
    url = f"https://vrmapi.victronenergy.com/v2/users/{idUser}/installations"
    headers = {
        "idUser": f"{idUser}",
        "X-Authorization": f"Token {api_token}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        while True:
            unit = str(input("Input MUXXXX or type 'quit' to exit: "))
            data = response.json()
            if unit.lower() == "quit":
                main()
            
            for record in data.get("records"):
                exists = False
                if record.get("name")[-4:] == unit[-4:] or record.get("name")[-4:] == unit[-4:]:
                    print('Unit is added to VRM')
                    print(f"Site ID for {unit} is {record.get("idSite")}")
                    exists = True        
                    break

            if exists == False:
                print('Unit was not found.')
    else:
        print("Response text: ", response.text)

def all_unit_battery_health():
    if response.status_code == 200:
        print('Loading trailers...')
        data = response.json()
        for record in data.get("records"):
            unitname = record.get("name")
            siteid = record.get("idSite")
            headers2 = {
                "idSite": f"{siteid}",
                "X-Authorization": f"Token {api_token}"
                }

            response2 = requests.get(f"https://vrmapi.victronenergy.com/v2/installations/{siteid}/diagnostics", headers=headers2)
            data2 = response2.json()
            records = data2.get("records", {})
            
            for record in records:
                    formval = record.get("formattedValue")
                    if isinstance(formval, str) and len(formval) > 1 and formval.split(":")[0][-1] == "%" and record.get("description") == "Battery SOC":
                        #print(f"{unitname} battery life at {formval}. Adding unit to all batteries list")
                        combined = {
                            "name": unitname,
                            "battery": formval
                        }
                        all_battery_units.append(combined)
                        formlength = len(formval)
                        #print(formlength)
                        if formlength == 6:
                            percentage = int(formval[:2])
                            if percentage <= 20:
                                #print(f"Unit battery is low, adding to battery list")
                                combined = {
                                    "name": unitname,
                                    "battery": formval  
                                }
                                low_battery_units.append(combined)

                        if formlength == 5:
                            percentage = int(formval[:1])
                            if percentage > 0:
                                #print("Unit battery is low, adding to low battery list")
                                combined = {
                                    "name": unitname,
                                    "battery": formval   
                                }
                                low_battery_units.append(combined)
                            elif percentage == 0:
                                #print("Battery is depleted, adding to depleted battery list")
                                combined = {
                                    "name": unitname,
                                    "battery": formval,
                                }
                                depleted_battery_units.append(combined)               
    naming_conventions()
    

def unit_battery_health(unit):
    if response.status_code == 200:
        #while True:
            data = response.json()
            if unit.lower() == "quit":
                main()
            for record in data.get("records"):
                unitname = record.get("name").lower()
                if unitname[-4:] == unit[-4:]:
                    siteid = record.get("idSite")
                    headers2 = {
                        "idSite": f"{siteid}",
                        "X-Authorization": f"Token {api_token}"
                    }

                    response2 = requests.get(f"https://vrmapi.victronenergy.com/v2/installations/{siteid}/diagnostics", headers=headers2)
                    data2 = response2.json()
                    records = data2.get("records", {})
                    for record in records:
                        #print(record)
                        if record.get("idSite") == siteid:
                            formval = record.get("formattedValue")
                            if isinstance(formval, str) and len(formval) > 1 and formval.split(":")[0][-1] == "%" and record.get("description") == "Battery SOC":
                                print(f"{unitname} battery life at {formval}")


    else:
        print("Response text:", response.text)

def rd_battery_map():
    for row in all_battery_units:
        url = "https://erp.sentracam.com/api/resource/Component"
        erp_token = os.getenv("erp_token")
        headers = {
            "Authorization": f"token {erp_token}"
        }

        params = {
            "fields": '["name"]',
            "filters": f'[["parent_component","=","{row["name"]}"]]',
            "limit_page_length": 0
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        for doc in data.get("data", []):
            rd_unit = doc["name"]
            #print(rd_unit)
            full_unit = {
                "name": rd_unit,
                "trailer": row["name"]
            }
            #print(f'Mapped {full_unit}')
            all_battery_units_mapped.append(full_unit)
    
    
    return

def low_battery_rd_fisheye_tool():
    date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    print("Low battery units: ")
    for row in low_battery_units:
        if row["name"][:3] != 'SC-':
            row["name"] = "SC-" + row["name"]
            print(f'Adjusted {row["name"]}')
        battery = row["battery"]
        print(f"{row["name"]} - {battery}")
        erp_token = os.getenv("erp_token")
        url = "https://erp.sentracam.com/api/resource/Component"
        headers = {
            "Authorization": f"token {erp_token}"
        }

        params = {
            "fields": '["name"]',
            "filters": f'[["parent_component","=","{row["name"]}"]]',
            "limit_page_length": 0
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        for doc in data.get("data", []):
            rd_unit = doc["name"]
            print(rd_unit)
            full_unit = {
                "name": rd_unit,
                "trailer": row["name"]
            }
            print(f'Adding {full_unit["name"]} to RD low list')
            rd_down.append(full_unit)
    print('RD List:')
    for rd in rd_down:
        print(f"{rd["name"]} - {rd["trailer"]}")

def low_battery_list():
    print("Low battery units: ")
    for row in low_battery_units:
        name = row["name"]
        battery = row["battery"]
        print(f"{row["name"]} - {row["battery"]}")
    
def depleted_battery_list():
    print("Depleted battery units: ")
    for row in depleted_battery_units:
        name = row["name"]
        battery = row["battery"]
        print(f"{row["name"]} - {row["battery"]}")
    
def all_battery_list():
    print("All battery units: ")
    for row in all_battery_units:
        name = row["name"]
        battery = row["battery"]
        print(f"{row["name"]} - {row["battery"]}")

if __name__ == "__main__":
    main()

