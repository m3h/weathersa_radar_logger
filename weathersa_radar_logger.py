#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timedelta
from PySimpleGUI.PySimpleGUI import RELIEF_SOLID

import requests
import PySimpleGUI as sg

location_codes = {
        'FAIR': 'IRS',
        'OTD': 'OTS',
        }
supported_resolutions = {
    'IRS': [300, 75, 50],
    'OTS': [300, 75],
}

session = requests.Session()
def login(userid: str, password: str):
    r = session.post(
            'https://aviation.weathersa.co.za/utility/users/login.php',
            data={
                'userid': userid,
                'password': password,
                'remember': 'false'
                }
            )


def get_radar(code: str, resolution: int, output_path: str):
    global session
    if resolution == 300:
        resolution = ''

    r = session.get(f'https://aviation.weathersa.co.za/ftpfile.php?f={code}{resolution}.gif&type=RADAR')

    with open(output_path, 'wb') as f:
        f.write(r.content)


logging_enabled = False
logging_started = False
logging_last = None

def do_logging(username, password, location_code, res_300km, res_75km, res_50km, output_folder, **kwargs):
    global logging_enabled, logging_started, logging_last
    if not logging_enabled:
        return

    radar_code = location_codes[location_code]

    if not logging_started:
        Path(output_folder).mkdir(exist_ok=True, parents=True)

        login(userid=username, password=password)
        logging_started = True

    current_time = datetime.now() 
    if logging_last is None or (current_time - logging_last) >= timedelta(minutes=15):

        def get_radar_res(res_bool, res_num):
            if res_num not in supported_resolutions[radar_code]:
                return

            op = Path(output_folder) / Path(location_code) / Path(f'{res_num}km')
            op.mkdir(exist_ok=True, parents=True)
            ofp = op / Path(f"{current_time.isoformat(timespec='minutes').replace(':', '_')}.gif")
            get_radar(radar_code, res_num, str(ofp))

        get_radar_res(res_300km, 300)
        get_radar_res(res_75km, 75)
        get_radar_res(res_50km, 50)

        logging_last = current_time




def main():
    global logging_enabled
    # All the stuff inside your window.
    global location_codes
    location_codes_list = list(location_codes)
    default_location_code = location_codes_list[0]

    layout = [  [sg.Text('Username:'), sg.InputText(key='username')],
                [sg.Text('Password'), sg.InputText(key='password', password_char='*')],
                [sg.Text('Location:'), sg.Combo(location_codes_list, key='location_code', default_value=default_location_code)],
                [sg.Checkbox('300 km', key='res_300km', default=True), sg.Checkbox('75 km', key='res_75km', default=True), sg.Checkbox('50 km', key='res_50km', default=True)],
                [sg.Text('Output folder:'), sg.InputText('./', key='output_folder'), sg.FolderBrowse(target='output_folder', initial_folder='./')],
                [sg.Button('Start'), sg.Button('Stop')],
                ]

    # Create the Window
    window = sg.Window('WeatherSA RADAR Logger', layout)
    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read(timeout=1000)
        if event == sg.WIN_CLOSED or event == 'Stop': # if user closes window or clicks cancel
            break
        elif event == 'Start':
            logging_enabled = True
        elif event == 'Stop':
            logging_enabled = False
        else:
            do_logging(**values)

    window.close()

if __name__ == "__main__":
    main()
