import subprocess
import sys
import shutil
import os


def ask(func):
    def inner(*args, **kwargs):
        func(*args, **kwargs)
        while True:
            answer = input("\nMove to the next case? (y/n)\n")
            if answer.lower() == "y":
                break
            if answer.lower() == "n":
                sys.exit()
            else:
                continue

    return inner


print(r"""
 __________________________________
 Starting ISV System-Prep Auto Tool 
                v1.0 
 ==================================
""")

# Check if any devices reports error status (# 1)
@ask
def case_01():
    get_error_devices = subprocess.run(
        [
            "powershell",
            "-command",
            "(Get-PnpDevice) | Where-Object { $_.Status -eq 'Error' }",
        ],
        capture_output=True,
        text=True,
    )
    error_devices =get_error_devices.stdout.strip().splitlines()
    if error_devices:
        print(
            "#1 - YB found in device manager!! Please look into the problematic device(s):\n"
        )
        for device in error_devices:
            print(device)
        while True:
            confirm = input("\nDo you want to continue? (y/n) ")
            if confirm.lower() == "y":
                break
            if confirm.lower() == "n":
                sys.exit()
            else:
                continue
    else:
        print("#1 - Verify no YB found in device manager [Complete]")


# Check Intel DPTF support (#2)
@ask
def case_02():
    get_cpu_arch = subprocess.run(
        ["wmic", "cpu", "get", "caption"],
        capture_output=True,
        text=True,
    )
    cpu_arch = get_cpu_arch.stdout.strip()
    if "AMD64" in cpu_arch:
        print("#2 - Skip checking Intel DPTF on AMD platform [Complete]")
    if "Intel64" in cpu_arch:
        get_DPTF_status = subprocess.run(
            [
                "powershell",
                "-command",
                "(Get-PnpDevice) | Where-Object { $_.FriendlyName -like '*Intel(R) Dynamic Tuning*' }",
            ],
            capture_output=True,
            text=True,
        )
        DPTF_status = get_DPTF_status.stdout.strip()
        if "Unknown" in DPTF_status:
            print(
                "#2 - Intel DPTF is supported but NOT enabled!! Please enter BIOS to enable it"
            )
            sys.exit()
        if "OK" in DPTF_status:
            print("#2 - Intel DPTF is already enabled [Complete]")
        else:
            print("#2 - Intel DPTF is not supported on this platform. Skip [Complete]")


# Get the chassis type and set corresponding power plan (#3)
@ask
def case_03():
    get_chassis = subprocess.run(
        ["wmic", "systemenclosure", "get", "chassistypes"],
        capture_output=True,
        text=True,
    )
    chassis_string = get_chassis.stdout.strip()
    power_plan_all = subprocess.run(
        [
            "powercfg",
            "/list",
        ],
        capture_output=True,
        text=True,
    )
    power_plan_all_string = power_plan_all.stdout.strip()
    power_plan_current = subprocess.run(
        [
            "powercfg",
            "/GetActiveScheme",
        ],
        capture_output=True,
        text=True,
    )
    power_plan_current_string = power_plan_current.stdout.strip()
    if "{10}" in chassis_string:  # Notebook
        while True:
            charging_status = subprocess.run(   # Check AC or DC mode
                ["wmic", "path", "Win32_Battery", "Get", "BatteryStatus"],
                capture_output=True,
                text=True,
            )
            charging_status_string = charging_status.stdout.strip()
            while "1" in charging_status_string:  # Not charging
                print("#3 - <NB> To set AC power plan, please plug in AC power!!") 
                confirm = input("Are you ready? (y/n) ") 
                if confirm.lower() == "y":
                    break
                elif confirm.lower() == "n":
                    sys.exit()
                else:
                    continue
            if "2" in charging_status_string: # Charging
                break
        if "HP Optimized" in power_plan_all_string:            
            for line in power_plan_all_string.splitlines():
                if "HP Optimized" in line:
                    hp_optimized_guid = line[19:55]
            if "HP Optimized" in power_plan_current_string:
                print("#3 - <NB> Set power plan as HP Optimized [Complete]")
            if "HP Optimized" not in power_plan_current_string:
                subprocess.run(
                    [
                        "powercfg",
                        "/setactive",
                        hp_optimized_guid,
                    ],
                    check=True,
                )
                print("#3 - <NB> Set power plan as HP Optimized [Complete]")
        if "HP Optimized" not in power_plan_all_string:
                print(
                    "#3 - <NB> HP Optimized is not available. Use default power plan [Complete]"
                )
    else:  # Desktop
        if "High performance" in power_plan_all_string:
            for line in power_plan_all_string.splitlines():
                if "High performance" in line:
                    high_performance_guid = line[19:55]
            if "High performance" in power_plan_current_string:
                print(
                    "#3 - <DT> Set power plan as High performance [Complete]"
                )
            if "High performance" not in power_plan_current_string:
                subprocess.run(
                    [
                        "powercfg",
                        "/setactive",
                        high_performance_guid,
                    ],
                    check=True,
                )
                print(
                    "#3 - <DT> Set power plan as High performance [Complete]"
                )
        if "High performance" not in power_plan_all_string:
            print("#3 - <DT> Power plan for High performance is not availalbe!!")
            sys.exit()


# Turn off Wi-Fi/BT and turn on airplane mode (#4)  *Reboot required
# Airplane mode has a bug (only icon changes)
# TODO: turn off WWAN
# netsh mbn set acstate interface="Cellular" state=autooff dataenablement
@ask
def case_04():
    app_path = "./src/app/BT.ps1"
    check_wifi = subprocess.run(  # Turn off Wi-Fi
        [
            "powershell",
            'Get-NetAdapterAdvancedProperty',
        ],
        capture_output=True,
        text=True,
    )
    if "Wi-Fi" in check_wifi.stdout.strip():
        subprocess.run(  # Turn off Wi-Fi
            [
                "powershell",
                'Set-NetAdapterAdvancedProperty -Name "Wi-Fi" -AllProperties ',
                '-RegistryKeyword "SoftwareRadioOff" -RegistryValue "1"',
            ],
            check=True,
        )
        get_default_policy = subprocess.run(["powershell", 'Get-ExecutionPolicy'], capture_output=True, text=True)
        default_policy = get_default_policy.stdout.strip()
        subprocess.run(  # Change execution policy to allow running powershell script
            [
                "powershell",
                'Set-ExecutionPolicy RemoteSigned',
            ],
            check=True,
        )
        subprocess.run(['powershell.exe', '-File', app_path, '-BluetoothStatus', 'Off'], check=True)  # Turn off BT
        subprocess.run(   # Reset to the default execution policy
            [
                "powershell",
                f'Set-ExecutionPolicy {default_policy}',
            ],
            check=True,
        )
        os.system(r"reg add HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\RadioManagement\SystemRadioState /ve /t REG_DWORD /d 1 /f > nul 2>&1") # Turn on airplane mode (Reboot required)
        print("#4 - Turn off Wi-Fi and turn on airplane mode [Complete]")
    else:
        print("#4 - WiFi is not supported on this platform. Skip [Complete]")
       

# Turn off User Account Control (UAC) (#5) 
@ask
def case_05():
    subprocess.run(
        [
            "reg",
            "add",
            r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\policies\system",
            "/v",
            "EnableLUA",
            "/t",
            "REG_DWORD",
            "/d",
            "0",
            "/f",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    print("#5 - Turn off User Account Control (UAC) [Complete]")


# Add RT Click Options regestry (#6)
@ask
def case_06():
    reg_file_path = "./src/Rt Click Options.reg"
    try:
        os.system(f'reg import \"{reg_file_path}\" > nul 2>&1')  # fmt: skip
        print("#6 - Add RT Click Options regestry [Complete]")
    except:
        print("#6 - Failed to add RT Click Options regestry!!")
        sys.exit()


# Check if Secure Boot is disabled and enable test signing (# 7)
@ask
def case_07():
    get_sb_state = subprocess.run(
        ["powershell", "Confirm-SecureBootUEFI"], capture_output=True, text=True
    )
    sb_state = get_sb_state.stdout.strip()
    if sb_state.lower() == "true":
        print("Secure boot is enabled!! Enter BIOS to disable Secure boot first")
        sys.exit()
    else:
        try:
            subprocess.run(
                ["bcdedit", "/set", "testsigning", "on"],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            print("#7 - Enable test mode [Complete]")
        except:
            print("#7 - Failed to enable test mode!!")
            sys.exit()


# Copy Power Config folder and import power scheme (#8)
@ask
def case_08():
    source_folder = "./src/PowerConfig"
    destination_folder = "C:\\PowerConfig"
    try:
        if os.path.exists(destination_folder):
            shutil.rmtree(destination_folder)
        shutil.copytree(source_folder, destination_folder)
        subprocess.run(
            ["C:\\PowerConfig\\Install.bat"],
            check=True,
            stdout=subprocess.DEVNULL,  # Uncomment to see power scheme GUID
        )
        print("#8 - Copy PowerConfig folder and import power scheme [Complete]")
    except:
        print("#8 - Failed to copy PowerConfig folder and import power scheme!!")
        sys.exit()


# Display full path/hidden files/empty drives/extensions/merge conflicts/protected OS files (#9)
@ask
def case_09():
    subprocess.run(  # Display the full path in the title bar
        [
            "reg",
            "add",
            r"HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CabinetState",
            "/v",
            "FullPath",
            "/t",
            "REG_DWORD",
            "/d",
            "1",
            "/f",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(  # Show hidden files. folders. and drives
        [
            "reg",
            "add",
            r"HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
            "/v",
            "Hidden",
            "/t",
            "REG_DWORD",
            "/d",
            "1",
            "/f",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(  # Show empty drives
        [
            "reg",
            "add",
            r"HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
            "/v",
            "HideDrivesWithNoMedia",
            "/t",
            "REG_DWORD",
            "/d",
            "0",
            "/f",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(  # Show extensions for knowm file types
        [
            "reg",
            "add",
            r"HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
            "/v",
            "HideFileExt",
            "/t",
            "REG_DWORD",
            "/d",
            "0",
            "/f",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(  # Show folders merge conflicts
        [
            "reg",
            "add",
            r"HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
            "/v",
            "HideMergeConflicts",
            "/t",
            "REG_DWORD",
            "/d",
            "0",
            "/f",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(  # Show protected OS files
        [
            "reg",
            "add",
            r"HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
            "/v",
            "ShowSuperHidden",
            "/t",
            "REG_DWORD",
            "/d",
            "1",
            "/f",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    os.system("taskkill /F /IM explorer.exe > nul 2>&1")  # Restart Windows Explorer to take effect changes immediately
    os.system("start explorer.exe > nul 2>&1")
    print(
        "#9 - Display full path/hidden files/empty drives/extensions/merge conflicts/protected OS files [Complete]"
    )


# Set sleep & display off to Never in power option (#10)
# TODO: confirm if DC mode can be set on DT platform without errors
@ask
def case_10():
    subprocess.run(
        [
            "powercfg",
            "/change",
            "standby-timeout-ac",
            "0",
        ],
        check=True,
    )
    subprocess.run(
        [
            "powercfg",
            "/change",
            "standby-timeout-dc",
            "0",
        ],
        check=True,
    )
    subprocess.run(
        [
            "powercfg",
            "/change",
            "monitor-timeout-ac",
            "0",
        ],
        check=True,
    )
    subprocess.run(
        [
            "powercfg",
            "/change",
            "monitor-timeout-dc",
            "0",
        ],
        check=True,
    )
    print("#10 - Set sleep & display off to Never in power option [Complete]")


# Set time zone to Central US and disable auto set time (# 11)
# Need to manually set correct time by users
@ask
def case_11():
    subprocess.run(
        ["tzutil", "/s", "Central Standard Time"],
        check=True,
    )
    subprocess.run(
        [
            "powershell",
            "-Command",
            'Set-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\W32Time\\Parameters" -Name "Type" -Value "NoSync"',
        ],
        check=True,
    )
    print(
        "#11 - Set time zone to Central US and disable set time automatically [Complete]"
    )


# Auto hide the taskbar (#12)
@ask
def case_12():
    subprocess.run(
        [
            "powershell",
            "-Command",
            "&{$p='HKCU:SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\StuckRects3';$v=(Get-ItemProperty -Path $p).Settings;$v[8]=3;&Set-ItemProperty -Path $p -Name Settings -Value $v;&Stop-Process -f -ProcessName explorer}",
        ],
        check=True,
    )
    print("#12 - Auto hide the taskbar [Complete]")


# Unpin Edge and pin Paint/Snipping Tool to taskbar (#13)
@ask
def case_13():
    reg_file_path = "./src/app/syspin.exe"
    app_path = os.environ.get("LocalAppData")
    subprocess.run(  # Unping Edge
        [
            "powershell",
            "-command",
            "Remove-Item 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Taskband' -Recurse -Force",
        ],
        check=True,
    )
    subprocess.run(  # Ping Paint
        [reg_file_path, f"{app_path}\\Microsoft\\WindowsApps\\mspaint.exe", "5386"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(  # Ping Snipping Tool
        [
            reg_file_path,
            f"{app_path}\\Microsoft\\WindowsApps\\SnippingTool.exe",
            "5386",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    os.system("taskkill /F /IM explorer.exe > nul 2>&1")  # Restart Windows Explorer
    os.system("start explorer.exe > nul 2>&1")
    print("#13 - Unpin Edge and pin Paint/Snipping Tool to taskbar [Complete]")


# Set UAC Admin Approval Mode to disabled (Same as case_05)
@ask
def case_14():
    subprocess.run(
        [
            "reg",
            "add",
            r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\policies\system",
            "/v",
            "EnableLUA",
            "/t",
            "REG_DWORD",
            "/d",
            "0",
            "/f",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    print("#14 - Set UAC Admin Approval Mode to disabled [Complete]")


# Turn off Windows Defender Firewall (# 15)
@ask
def case_15():
    subprocess.run(
        ["netsh", "advfirewall", "set", "allprofiles", "state", "off"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    print("#15 - Turn off Windows Firewall [Complete]")


# TODO: Turn off all messages in Security and Maintenance settings (#16)
# def case_16:



# Set resolution to 1920x1080 and DPI to 100% (#17)
@ask
def case_17():
    res_app_path = "./src/app/QRes.exe"
    dpi_app_path = "./src/app/SetDpi.exe"
    subprocess.run(
        [res_app_path, "/x:1920", "/y:1080"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        [dpi_app_path, "100"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    print("#17 - Set resolution to 1920x1080 @ 100% [Complete]")


# Set brightness level to 100% and disable adaptive brightness (# 18)
# TODO: Check if the code can work on platform without ALS. If no, set stderr to NUL
@ask
def case_18():
    subprocess.run(
        [
            "powershell",
            "-command",
            "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,100)",
        ],
        check=True,
    )
    subprocess.run(
        [
            "powercfg",
            "-setacvalueindex",
            "SCHEME_CURRENT",
            "7516b95f-f776-4464-8c53-06167f40cc99",
            "FBD9AA66-9553-4097-BA44-ED6E9D65EAB8",
            "0",
        ],
        check=True,
    )
    subprocess.run(
        [
            "powercfg",
            "-setdcvalueindex",
            "SCHEME_CURRENT",
            "7516b95f-f776-4464-8c53-06167f40cc99",
            "FBD9AA66-9553-4097-BA44-ED6E9D65EAB8",
            "0",
        ],
        check=True,
    )
    subprocess.run(["powercfg", "-SetActive", "SCHEME_CURRENT"], check=True)
    print(
        "#18 - Set Brightness level to 100% and disable adaptive brightness [Complete]"
    )


# Uninstall MS Office and related apps (#19)
# TODO: UWP app
# Get-AppxPackage –AllUsers
@ask
def case_19():
    subprocess.run(
        [
            "powershell",
            "-Command",
            "Get-AppxPackage *OfficeHub* | Remove-AppxPackage; Get-AppxPackage *OneNote* | Remove-AppxPackage; Get-AppxPackage *Office* | Remove-AppxPackage",
        ],
        shell=True,
        check=True,
    )
    MS_blacklist_path = "./src/blacklist_MS.txt"  # TODO: Manual update name in the file
    MS_blacklist = []  
    with open(MS_blacklist_path, "r") as txt:
        for item in txt:
            MS_blacklist.append(item.strip())
    print("Uninstalling the follow apps: ")
    for index, app in enumerate(MS_blacklist, 1):
        print(f"{index}. {app}")
    for MS_app in MS_blacklist:
        subprocess.run(
            [
            "wmic",
            "product",
            "where",
            f"name='{MS_app}'",
            "call",
            "uninstall"
            ],
            shell=True,
            check=True,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL            
        )
    print("#19 - Uninsalled MS Office and related apps [Complete]")


# Uninstall HP apps (#20)
# wmic product get name | findstr "HP"
@ask
def case_0020():
    HP_blacklist_path = "./src/blacklist_HP.txt"  # TODO: Manual update name in the file
    HP_blacklist = []  
    with open(HP_blacklist_path, "r") as txt:
        for item in txt:
            HP_blacklist.append(item.strip())
    print("Uninstalling the follow apps: ")
    for index, app in enumerate(HP_blacklist, 1):
        print(f"{index}. {app}")
    for HP_app in HP_blacklist:
        subprocess.run(
            [
            "wmic",
            "product",
            "where",
            f"name='{HP_app}'",
            "call",
            "uninstall"
            ],
            shell=True,
            check=True,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL            
        )
    print("#20 - Uninsalled HP apps [Complete]")


# Install .NET Framwork 3.5 (#21)
# TODO: Make sure corp net can ping google.com
@ask
def case_021():     
    while True:
        check_internet = subprocess.run(
            ["ping", "google.com", "-w", "4"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        check_internet_string = check_internet.stdout
        while "Ping request could not find host" in check_internet_string:
            print("#21 - To download .NET framwoork 3.5, please connect to Internet!!")
            confirm = input("Are you ready? (y/n) ") 
            if confirm.lower() == "y":
                break
            elif confirm.lower() == "n":
                sys.exit()
            else:
                continue
        else:
            break
    subprocess.run(
        [
            "powershell",
            "-command",
            "Enable-WindowsOptionalFeature -FeatureName NetFx3 -Online",
        ],
        text=True,
        stdout=subprocess.DEVNULL,
    )
    print("#21 - Install .NET Framwork 3.5 [Complete]")


# TODO: Pause Windows Update and disable Allow downloads from other PCs (#22)


# Set regristry for DriverSearching to 0  (#25)
@ask
def case_25():
    subprocess.run(
        [
            "reg",
            "add",
            r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching",
            "/v",
            "SearchOrderConfig",
            "/t",
            "REG_DWORD",
            "/d",
            "0",
            "/f",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    print("#25 - Set Registry key for DriverSearching to 0 [Complete]")


# TODO: Turn off Smart app control/Reputation-based protection/Isolated browsing (#26)


# Disable and stop Windows Update/Firewall services (#27)
@ask
def case_27():
    try:
        subprocess.run(  # Disable WU service
            [
                "sc", "config", "wuauserv", "start=disabled",
            ],
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(  # Stop WU service
            [
                "sc", "stop", "wuauserv",
            ],
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(  # Disable Firewall service
            [
                "sc", "config", "mpssvc", "start=disabled",
            ],
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(  # Stop Firewall service
            [
                "sc", "stop", "mpssvc",
            ],
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
        )
    except:
        pass
    print("#27 - Disable and stop Windows Update/Firewall services [Complete]")


# Disable system hibernation (#28)
def case_28():
    subprocess.run(
        ["powershell", "-Command", "powercfg -h off"],
        check=True,
    )
    print("#28 - Disable system hibernation [Complete]")


# Run case
case_01()
case_02()
case_03()
case_21()
case_04()
case_05()
case_06()
case_07()
case_08()
case_09()
case_10()
case_11()
case_12()
case_13()
# case_14()
case_15()
case_16()
# case_17()
case_18()
case_19()
# case_20()
# case_22()
# case_23()
# case_24()
case_25()
# case_26()
case_27()
case_28()
