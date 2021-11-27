#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timedelta
from PySimpleGUI.PySimpleGUI import RELIEF_SOLID

import requests
import PySimpleGUI as sg
from PIL import Image

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

    if r.content == b'\n\n\n':
        sg.popup("Error getting radar map. Please ensure that you used the correct password!")
        return False

    with open(output_path, 'wb') as f:
        f.write(r.content)

    return True


logging_enabled = False
logging_started = False
logging_last = None

def do_logging(username, password, location_code, res_300km, res_75km, res_50km, output_folder, window, **kwargs):
    print("enter do_logging")
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
        print("log now")

        def get_radar_res(res_bool, res_num):
            if res_num not in supported_resolutions[radar_code] or not res_bool:
                return

            op = Path(output_folder) / Path(location_code) / Path(f'{res_num}km')
            op.mkdir(exist_ok=True, parents=True)
            ofp = op / Path(f"{current_time.isoformat(timespec='minutes').replace(':', '_')}.gif")
            return get_radar(radar_code, res_num, str(ofp))

        if get_radar_res(res_300km, 300) is False:
            return False
        if get_radar_res(res_75km, 75) is False:
            return False
        if get_radar_res(res_50km, 50) is False:
            return False

        logging_last = current_time
    else:
        next_log = logging_last + timedelta(minutes=15)
        time_till_next = next_log - current_time
        print("time till next log:", time_till_next)
        window['log_status'].update(f"Time till next download: {time_till_next}")

    return True


def gif_create(input_folder: str, delay: str, window: sg.Window):
    print(f"Create GIF, input=\"{input_folder}\", delay={delay} ms")

    input_path = Path(input_folder).resolve()

    gifs_created = list()
    if not input_path.is_dir():
        return gifs_created


    for subdir in input_path.iterdir():
        if subdir.is_dir():
            gifs_created.extend(gif_create(subdir, delay, window))

    gif_paths = sorted(
            [
                p for p in input_path.glob('./*.gif')
                if p.is_file() and 'animated' not in p.stem
                ]
            )
    if len(gif_paths) == 0:
        return gifs_created

    images = [
            Image.open(str(p.resolve()))
            for p in gif_paths 
            if 'animated' not in p.stem
            ]
  
    name = f'animated_{gif_paths[0].stem}_{gif_paths[-1].stem}.gif'

    output_path = input_path / name
    images[0].save(
            str(output_path),
            save_all=True,
            append_images=images[1:],
            duration=float(delay),
            loop=0
            )

    gifs_created.append(output_path)

    window['gif_status'].update(f"Created ...{str(output_path)[-80:]}")
    window.refresh()

    return gifs_created


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
                [sg.Text('Output folder:'), sg.InputText('./output/', key='output_folder'), sg.FolderBrowse(target='output_folder', initial_folder='./output/')],
                [sg.Button('Start'), sg.Button('Stop', disabled=True)],
                [sg.Text("", key='log_status')],
                [sg.Text('_'*80)],
                [sg.Text('Gif frame delay (ms):'), sg.InputText(500, key='gif_delay')],
                [sg.Text('Input folder:'), sg.InputText('./output/', key='gif_output_folder'), sg.FolderBrowse(target='gif_output_folder', initial_folder='./output/')],
                [sg.Button("Create GIF", key='gif_create')],
                [sg.Text("", key='gif_status')],
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

            window['Start'].update(disabled=True)
            window['Stop'].update(disabled=False)
        elif event == 'Stop':
            logging_enabled = False

            window['Start'].update(disabled=False)
            window['Stop'].update(disabled=True)
        elif event == 'gif_create':
            window['gif_status'].update("Creating GIF!"); window.refresh()
            gifs_created = gif_create(
                    values['gif_output_folder'],
                    values['gif_delay'],
                    window
                    )
            if len(gifs_created) != 0:
                window['gif_status'].update("Done!")
            else:
                window['gif_status'].update("Error creating GIF! Did you log any images?")
        else:
            if do_logging(**values, window=window) is False:
                logging_enabled = False

                window['Start'].update(disabled=False)
                window['Stop'].update(disabled=True)
                window['log_status'].update("Error retrieving radar map!")

    window.close()

if __name__ == "__main__":
    main()
