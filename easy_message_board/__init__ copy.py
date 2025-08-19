import json
import os
import bpy
import tomllib
import time
import requests
from bpy.types import Operator, Panel
from bpy.utils import register_class, unregister_class
from datetime import datetime, timezone
from math import floor
from .utils import *

from .bpy_classes import master_classes

emb_path = os.path.dirname(__file__)
path_split = emb_path.split(os.path.sep)
print(path_split)
addon_path = os.path.sep.join(path_split[:-1])
addon_path_name = os.path.basename(addon_path)
blender_addons_path = os.path.sep.join(path_split[:-2])
globalPrefsPath = os.path.join(blender_addons_path, 'emb_prefs.json')
messages_path = os.path.join(emb_path, 'messages')

emb_id = None
emb_classes = set()

messages = dict()

try:
    from .. import bl_info
except:
    print(f'bl_info for {os.path.basename(addon_path)} does not exist! ')
    bl_info = dict()
    
class autoUpdateJson(dict):
    json_path = ''
    def auto_update(self):
        try:
            with open(self.json_path, 'w+') as file:
                file.write(json.dumps(self, indent=2))
                return None
        except:
            return None
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.auto_update()

def loadMessages() -> dict:
    messages.clear()
    for message_name in os.listdir(messages_path):
        message_json = os.path.join(messages_path, message_name)
        if not message_name.endswith('.json'): continue
        with open(message_json, 'r') as file:
            message = autoUpdateJson(json.loads(file.read()))
            message.json_path = message_json

        message_id = os.path.splitext(message_name)[0]
        messages[message_id] = message
    return messages

def markRead(id) -> None:
    if messages[id]['read'] == False:
        messages[id]['read'] = True
        with open(os.path.join(messages_path, id+'.json'), 'w+') as file:
            file.write(json.dumps(messages[id], indent=2))
            return None
    return None

def localEmbSettings() -> dict:
    with open(os.path.join(emb_path, 'settings.json'), 'r') as file:
        return json.loads(file.read())
    
def localEmbData() -> dict:
    with open(os.path.join(emb_path, 'data.json'), 'r') as file:
        return json.loads(file.read())

def globalPrefsPathExists() -> bool:
    return os.path.exists(globalPrefsPath)

def globalPrefsJsonWrite(data: dict) -> None:
    print('test')
    with open(globalPrefsPath, 'x') as file:
        file.write(json.dumps(data, indent=2))
        return None
    print('test2')
def globalPrefsJsonRead() -> dict:
    with open(globalPrefsPath, 'r') as file:
        return json.loads(file.read())
    
def getAddonData() -> dict:
    # TOML manifest is prioritized over bl_info
    manifestPath = os.path.join(addon_path, 'blender_manifest.toml')
    if os.path.exists(os.path.join(addon_path, 'blender_manifest.toml')):
        with open(manifestPath, 'rb') as file:
            return tomllib.load(file)
    elif bl_info:
        return bl_info
    return dict()

addonData = getAddonData()
emb_data = autoUpdateJson(localEmbData())
emb_data.json_path = os.path.join(emb_path, 'data.json')

def initGlobalPrefs() -> None: # first time start
    if globalPrefsPathExists():
        return
    init_data = {
        'interval': 600, # How many seconds between each check
        'global_disable': False, # Globally disable the checking
        'delete_after_#': 15, # Delete messages when they exceed a threshold. This is per-EMB, not across all EMBs. 0 to never delete
        'volume': 0.2,
        'github_token': 'YOUR_TOKEN_HERE' # User's github token to get around rate limiting, should that be a concern
    }
    emb_data['last_message_time'] = floor(time.time())
    globalPrefsJsonWrite(init_data)

if not globalPrefsPathExists():
    initGlobalPrefs()

emb_settings = localEmbSettings()
global_prefs = autoUpdateJson(globalPrefsJsonRead())
global_prefs.json_path = globalPrefsPath
api_headers = {'Accept': 'application/vnd.github.v3+json'}

def validate_github_token(token):
    

def initMaster() -> None:
    try:
        has_connection = requests.get('https://www.google.com').status_code == 200
        assert has_connection
    except:
        has_connection = False

    # Allocate globals within Blender's namespace. Is this allowed?
    bpy.types.WindowManager.emb_entries = dict()
    bpy.types.WindowManager.emb_classes = master_classes
    bpy.types.WindowManager.emb_vars = {
        'has_connection': has_connection,
    }
    emb_vars = bpy.types.WindowManager.emb_vars

    github_token = global_prefs.get('github_token')
    if has_connection:
        if (github_token != 'YOUR_TOKEN_HERE') and (not github_token in {None, ''}):
            api_headers['Authorization'] = global_prefs['github_token']
            emb_vars['token'] = True

    [register_class(cls) for cls in master_classes]

def buildEntry() -> dict:
    #addonData = getAddonData()
    if not addonData:
        print('Failure to retrieve addon data. Either non-existant bl_info or blender_manifest.toml!')
        print(addon_path_name)
        entry = {
            'id': addon_path_name,
            'failure': 'Missing sufficient add-on info'
        }
        return entry
    if (id := emb_settings.get('id')) in {None, ''}:
        #print(f'{addon_path_name} EMB settings missing "id". Using addon folder instead')
        id = addon_path_name
    if (profile := emb_settings.get('profile')) == '':
        entry = {
            'id': id,
            'failure': 'No user profile entered to get data from in EMB settings'
        }
        return entry
    
    # Check if at least one part of the EMB is configured to get any data from GitHub.
    if bool(emb_settings.get('message_repository')) and bool(emb_settings.get('message_board_path')):
        pass
    elif bool(emb_settings.get('message_repository')) and bool(emb_settings.get('update_board_path')):
        pass
    elif bool(emb_settings.get('release_repository')):
        pass
    else:
        entry = {
            'id': id,
            'failure': 'This EMB is not configured to get any data!'
        }
        return entry

    if (addonVersion := addonData.get('version')) in {None, ''}: # If empty result
        addonVersion = 'N/A_VERSION'
    elif type(addonVersion) == str: # if str
        addonVersion = tuple(map(int, addonVersion.split(',')))
    elif type(addonVersion) == tuple: # if tuple (preferred)
        pass
    else: # if anything else
        addonVersion = 'N/A_VERSION'

    #emb_data = autoUpdateJson(localEmbData())
    #emb_data.json_path = os.path.join(emb_path, 'data.json')

    entry = {
        "id": id,
        "profile": profile,
        "version": addonVersion,
        "message_repository": emb_settings.get('message_repository'),
        "message_board_path": emb_settings.get('message_board_path'),
        "update_board_path": emb_settings.get('update_board_path'),
        "release_repository": emb_settings.get('release_repository'),
        "emb_path": emb_path,
        'data': emb_data,
        'messages': messages,
        'update_data': dict(),
        'ignore': False, # Set this to True if an error occurs regarding its settings. It will be skipped by the checker, and only resets when Blender restarts.
    }

    return entry

def download_commit_content(commit, path, api_headers) -> dict:
    import base64
    tree = commit['commit']['tree']['url'] + '?recursive=1'
    tree = requests.get(tree, headers=api_headers).json()
    for item in tree.get('tree', []):
        if item['path'] == path: break

    blob = requests.get(item['url'], headers=api_headers).json()
    content = base64.b64decode(blob['content'])
    msg = json.loads(content)
    return msg

def write_msg_json(msg: dict, name):
    msg['read'] = False
    msg['notified'] = False
    with open(os.path.join(messages_path, f'{name}.json'), 'w+') as file:
        file.write(json.dumps(msg, indent=2))

def validate_message_board(entry, repository, file_path, headers):
    url = f"https://api.github.com/repos/{entry['profile']}/{repository}/commits"
    params = {"path": file_path, 'per_page': 5}

    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 404:
        entry['ignore'] = True
    if response.status_code == 403:
        return 'rate_limited'
    if response.status_code == 401:
        return 'bad_token'
    if response.json() == []:
        entry['ignore'] = True
        return 'continue'
    return response

def emb_checking() -> None:
    emb_vars = bpy.types.WindowManager.emb_vars
    if emb_vars.get('invalid_token'): return
    try:
        assert requests.get('https://www.google.com').status_code == 200
    except:
        emb_vars['has_connection'] = False
        return None
    emb_vars['has_connection'] = True
    
    entries: dict = bpy.types.WindowManager.emb_entries
    github_token = global_prefs.get('github_token')

    if (github_token != 'YOUR_TOKEN_HERE') and (not github_token in {None, ''}) and (not bool(emb_vars.get('invalid_token'))):
        api_headers['Authorization'] = global_prefs['github_token']
    queue = list(entries.items())
    while queue:
        entry_id, entry = queue.pop(0)
        if entry.get('ignore'): continue
        if entry.get('failure'): continue
        response = validate_message_board(
            entry,
            entry.get('message_repository', '{}'),
            entry.get('message_board_path', '{}'),
            api_headers,
            )
        if response == 'continue': pass
        elif response == 'rate_limited': pass
        elif response == 'bad_token': # The token couldn't be verified, so brick the system. Will never happen if Blender starts with a correct token.
            emb_vars['invalid_token'] = True
            return None
        else:
            msg_data = response.json()
            for commit in msg_data:
                commit_date = format_time(commit['commit']['committer']['date'])
                if commit_date > emb_data['last_message_time']:
                    msg = download_commit_content(commit, entry['message_board_path'], api_headers)
                    write_msg_json(msg, commit_date)


def initLocal() -> None:
    global emb_id
    entry = buildEntry()
    emb_id = entry['id']

    class emb_panel(Panel):
        bl_idname = f'EMB_PT_{emb_id}'
        bl_label = addonData.get('name', addon_path_name)
        bl_category = 'TOOLS'
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_parent_id = 'EMB_PT_main_panel'
        emb_id = entry['id']
        emb_entry = entry

        def draw_msg_body(self, context: bpy.types.Context, layout: bpy.types.UILayout):
            pass
        def draw_upd_body(self, context: bpy.types.Context, layout: bpy.types.UILayout):
            entry = self.emb_entry
            if entry['version'] == 'N/A_VERSION':
                layout.row().label(text='This EMB is not configured to check for new versions.')
                return None
            if bool(entry['message_repository']) and bool(emb_settings['update_board_path']):
                pass
            elif bool(emb_settings['release_repository']):
                pass
            else:
                layout.row().label(text='This EMB is not configured to check for new versions.')
                return None
            
            if bpy.types.WindowManager.emb_vars.get('not_connected'):
                layout.row().label(text='Not connected to internet!')
                return None
            
            if entry.get('update_data', dict()).get('new_version') > entry['version']:
                pass
            layout.row().label(text='You seem to be on the latest version!')

        if entry.get('failure'):
            failure_reason = entry['failure']
            def draw(self, context):
                layout = self.layout
                layout.label(text=f'The EMB for {self.emb_id} failed to register.')
                layout.label(text=self.failure_reason)
        else:
            def draw(self, context):
                layout = self.layout
                msgs_header, msgs_body = layout.panel(self.bl_idname+'_msgs')
                msgs_header.row().label(text='Messages')
                if msgs_body:
                    messages = self.emb_entry['messages']
                    msgs_body.row().label(text='Here are the messages!')

                upd_header, upd_body = layout.panel(self.bl_idname+'_update')
                upd_header.row().label(text='Updates')
                if upd_body:
                    self.draw_upd_body(context, upd_body)


    bpy.types.WindowManager.emb_entries[emb_id] = entry
    register_class(emb_panel)

def register():
    if not globalPrefsPathExists():
        initGlobalPrefs()
    if getattr(bpy.types.WindowManager, 'emb_entries', None) == None:
        initMaster()
    initLocal()
    pass

def unregister():
    pass