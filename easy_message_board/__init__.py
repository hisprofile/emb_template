import bpy
import json
import os
import tomllib
import time
from threading import Thread
from . import bpy_classes
from bpy.types import Panel
from bpy.utils import register_class, unregister_class
from .utils import *
from .bpy_classes import master_classes
from .main_vars import *

global_id = None

'''emb_path = os.path.dirname(__file__)
emb_data_path = os.path.join(emb_path, 'data.json')
path_split = emb_path.split(os.path.sep)
addon_path = os.path.sep.join(path_split[:-1])
addon_path_name = os.path.basename(addon_path)
blender_resource_path = str(Path(bpy.utils.resource_path('USER')).parents[0])
globalPrefsFolder = os.path.join(blender_resource_path, 'emb_data')
if not os.path.exists(globalPrefsFolder):
    os.makedirs(globalPrefsFolder)
globalPrefsPath = os.path.join(globalPrefsFolder, 'emb_prefs.json')
messages_path = os.path.join(emb_path, 'messages.data')
separate_chr = '¸' '''

emb_id = None
emb_classes = set()

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
    def write(self):
        self.auto_update()
    
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.auto_update()

class msgs_structure(dict):
    file_path = ''
    block = False

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if not self.block: self.write()

    def load(self, path):
        if not os.path.exists(path):
            raise OSError
        self.file_path = path
        file = open(path, 'r')
        string = file.read()
        file.close()
        self.string_to_dict(string)
        return self

    def string_to_dict(self, string: str):
        self.block = True
        string = string.lstrip('\n').rstrip('\n')
        lines = string.split('\n')
        while '' in lines:
            lines.remove('')
        lines = list(map(lambda a: a.split(separate_chr), lines))
        for item in lines:
            if len(item) != 5: continue
            id, title, text, icons, size = item
            self[int(id)] = {'title': title, 'text': text, 'icons': icons, 'size': size}
        self.block = False
        return self

    def write(self):
        file = open(self.file_path, 'w')
        for key, value in self.items():
            file.write(separate_chr.join([str(key), *list(value.values())]))
            file.write('\n')
        file.close()

    @property
    def first(self):
        return next(iter(sorted(list(self.items()), key=lambda a: a[0], reverse=True)), (0, 0))

def localEmbSettings() -> dict:
    with open(os.path.join(emb_path, 'settings.json'), 'r') as file:
        return json.loads(file.read())
    
def localEmbData() -> autoUpdateJson:
    if not os.path.exists(emb_data_path):
        init_data = autoUpdateJson({
            "last_message_time": int(time.time()),
            "new_messages": 0,
            "update_ignore_this_version": [
                0,
                0,
                0
            ],
            "update_ignore_future_versions": False,
        })
        init_data.json_path = emb_data_path
        init_data.write()
        return init_data
    else:
        with open(emb_data_path, 'r') as file:
            emb_data = autoUpdateJson(json.loads(file.read()))
            emb_data.json_path = emb_data_path
            return emb_data

def globalPrefsPathExists() -> bool:
    return os.path.exists(globalPrefsPath)

def globalPrefsJsonWrite(data: dict) -> None:
    with open(globalPrefsPath, 'x') as file:
        file.write(json.dumps(data, indent=2))
        return None
    
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

def getLocalMessages() -> dict:
    messages = msgs_structure()
    if not os.path.exists(messages_path):
        messages.file_path = messages_path
        messages.write()
    else:
        try:
            messages.load(messages_path)
        except:
            messages.file_path = messages_path
            messages.write()
    return messages

addonData = getAddonData()
emb_data = localEmbData()
messages = getLocalMessages()


def getGlobalPrefs() -> None:
    if globalPrefsPathExists():
        prefs = autoUpdateJson(globalPrefsJsonRead())
        prefs.json_path = globalPrefsPath
        return prefs
    else: # first start
        notif_url = 'https://github.com/sourcesounds/tf/raw/refs/heads/master/sound/ui/message_update.wav'
        notif_name = notif_url.split('/')[-1]
        download_notif_thread = Thread(target=download_file, args=[notif_url, globalPrefsFolder], daemon=True)
        download_notif_thread.start()
        init_data = autoUpdateJson({
            'interval': 600, # How many seconds between each check
            'global_disable': False, # Globally disable the checking
            #'delete_after_#': 15, # Delete messages when they exceed a threshold. This is per-EMB, not across all EMBs. 0 to never delete
            'volume': 0.2,
            'notification_sound': os.path.join(globalPrefsFolder, notif_name),
            'never_notify': False,
            'show_dev_message_generator': False,
        })
        init_data.json_path = globalPrefsPath
        init_data.write()
        return init_data

globalPrefs = getGlobalPrefs()
emb_settings = localEmbSettings()

def bpy_timer():
    if bpy.types.WindowManager.emb_vars['prefs']['global_disable']: return
    checker = Thread(target=emb_checking, daemon=True)
    checker.start()
    return bpy.types.WindowManager.emb_vars['prefs']['interval']

@bpy.app.handlers.persistent
def timer_ensure(a=None, b=None):
    bpy.app.timers.register(bpy_timer)#, first_interval=3)

def initMaster() -> None:

    # Allocate globals within Blender's namespace. Is this allowed?
    bpy.types.WindowManager.emb_entries = dict()
    bpy.types.WindowManager.emb_classes = master_classes
    bpy.types.WindowManager.emb_vars = {'checker': emb_checking, 'prefs': globalPrefs, 'timer_ensure': timer_ensure, 'bpy_timer': bpy_timer}
    emb_vars = bpy.types.WindowManager.emb_vars

    [(register_class(cls), print(cls)) for cls in master_classes]

    bpy.types.WindowManager.emb_props = PointerProperty(type=bpy_classes.emb_props)
    bpy.app.handlers.load_post.append(timer_ensure)
    bpy.app.timers.register(bpy_timer)#, first_interval=3)

def uninitMaster() -> None:
    emb_vars = bpy.types.WindowManager.emb_vars
    for cls in reversed(bpy.types.WindowManager.emb_classes):
        unregister_class(cls)
    bpy.app.handlers.load_post.remove(emb_vars['timer_ensure'])
    bpy.app.timers.unregister(emb_vars['bpy_timer'])
    del bpy.types.WindowManager.emb_entries
    del bpy.types.WindowManager.emb_classes
    del bpy.types.WindowManager.emb_vars
    del bpy.types.WindowManager.emb_props

def buildEntry() -> dict:
    #addonData = getAddonData()
    global global_id
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
    
    # Check if at least one part of the EMB is configured to get any data from GitHub.
    if bool(emb_settings.get('message_board_path')): # bool(emb_settings.get('message_repository')) and 
        pass
    elif bool(emb_settings.get('update_board_path')): # bool(emb_settings.get('message_repository')) and 
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
        #emb_data['version'] = addonVersion
    elif type(addonVersion) == tuple: # if tuple (preferred)
        pass
    else: # if anything else
        addonVersion = 'N/A_VERSION'

    #emb_data = autoUpdateJson(localEmbData())
    #emb_data.json_path = os.path.join(emb_path, 'data.json')
    global_id = id
    entry = {
        "id": id,
        #"profile": profile,
        "version": addonVersion,
        #"message_repository": emb_settings.get('message_repository'),
        "message_board_path": emb_settings.get('message_board_path'),
        "update_board_path": emb_settings.get('update_board_path'),
        "release_repository": emb_settings.get('release_repository'),
        "emb_path": emb_path,
        'data': emb_data,
        'messages': messages,
        'update_data': dict(),
        'ignore': False, # Set this to True if an error occurs regarding its settings. It will be skipped by the checker, and only resets when Blender restarts.
        'local_classes': set(),
        'new_update': False
    }

    return entry

def emb_checking() -> None:
    checking_vars = {
        'make_sound': False,
        'has_new_update': False,
        'total_new_messages': 0,
        'total_new_updates': 0,
    }

    import requests

    emb_vars = bpy.types.WindowManager.emb_vars
    try:
        assert requests.get('https://www.google.com').status_code == 200
    except:
        return None
    
    entries: dict = bpy.types.WindowManager.emb_entries

    def process_update(entry, update_board_path):
        try: # getting the url
            url = update_board_path
            get_messages = requests.get(url)
            assert get_messages.status_code == 200
        except:
            if entry.get('last_error_upd', '') != 'UPD_BAD_URL':
                entry['last_error_upd'] = 'UPD_BAD_URL'
                operator_report(r_type='WARNING', r_message=f'{entry["id"]}: Failed to grab update data! Are profile, repository, and path parameters correct?')
            return
        
        try: # converting the data to a dict
            get_messages = json.loads(get_messages.content.decode())
        except:
            if entry.get('last_error_upd', '') != 'UPD_BAD_ENCODE':
                entry['last_error_upd'] = 'UPD_BAD_ENCODE'
                operator_report('INVOKE_DEFAULT', r_type='WARNING', r_message=f'{entry["id"]}: Failed to load update data as JSON! It was not formatted correctly!')
            return

        try:
            assert bool(get_messages['version'])
            assert bool(get_messages['title'])
            assert bool(get_messages['text'])
            assert bool(get_messages['icons'])
            assert bool(get_messages['sizes'])
        except:
            bpy.ops.emb.quick_report('INVOKE_DEFAULT', r_type='WARNING', r_message=f'{entry["id"]}: Update data was not formatted correctly!')
            return

        get_messages['version'] = tuple(get_messages['version'])

        no_notify = entry['data']['update_ignore_future_versions']

        if (type(entry['version']) == tuple) \
        and (get_messages['version'] > entry['version']):
            checking_vars['has_new_update'] = True and (not no_notify) and (bool(entry['update_data']) == False)
            entry['new_update'] = True
        if (get_messages['version'] > tuple(entry['data']['latest_version'])): # to prevent a ping from every time it checks and a user still hasn't updated
            checking_vars['make_sound'] = True and (not no_notify)
            checking_vars['has_new_update'] = True

        entry['data']['latest_version'] = get_messages['version']
        entry['update_data'] = get_messages
        checking_vars['total_new_updates'] += checking_vars['has_new_update']


    def process_messages(entry, message_board_path):
        global make_sound
        try: # getting the url
            url = message_board_path
            get_messages = requests.get(url)
            assert get_messages.status_code == 200
        except:
            if entry.get('last_error_msg', '') != 'MSG_BAD_URL':
                entry['last_error_msg'] = 'MSG_BAD_URL'
                operator_report(r_type='WARNING', r_message=f'{entry["id"]}: Failed to grab the file! Is the URL correct?')
            return
        try: # converting the data to a dict
            get_messages = msgs_structure().string_to_dict(get_messages.content.decode())
            assert bool(get_messages)
        except:
            if entry.get('last_error_msg', '') != 'MSG_BAD_ENCODE':
                entry['last_error_msg'] = 'MSG_BAD_ENCODE'
                operator_report(r_type='WARNING', r_message=f'{entry["id"]}: Failed to read the message file! It was not written properly!')
            return
        
        entry_msgs: msgs_structure = entry['messages']
        entry_data: autoUpdateJson = entry['data']
        msg_latest_time = entry_data['last_message_time']
        get_messages_latest_time = get_messages.first[0]

        if get_messages_latest_time > msg_latest_time:
            new_messages = sum([bool(time > msg_latest_time) for time in get_messages.keys()])
            checking_vars['total_new_messages'] += new_messages
            entry_data['new_messages'] = new_messages
            entry_data['last_message_time'] = get_messages_latest_time
            checking_vars['make_sound'] = True

        entry_msgs.clear()
        entry_msgs.update(get_messages)
        entry_msgs.write()

    for id, entry in list(entries.items()):
        if entry.get('failure'): continue
        if (message_board_path := entry.get('message_board_path')):
            process_messages(entry, message_board_path)
        if (update_board_path := entry.get('update_board_path')) and (type(entry['version']) == tuple):
            process_update(entry, update_board_path)

    if checking_vars['make_sound'] and (emb_vars['prefs']['never_notify'] == False):
        play_sound(emb_vars['prefs']['notification_sound'], emb_vars['prefs']['volume'])

    if emb_vars['prefs']['never_notify']: return
    
    def notify_user():
        if checking_vars['total_new_messages'] and checking_vars['total_new_updates']:
            message = 'messages' if checking_vars['total_new_messages'] > 1 else 'message'
            update = 'updates' if checking_vars['total_new_messages'] > 1 else 'update'
            bpy.ops.emb.quick_report('INVOKE_DEFAULT', r_type='INFO', r_message=f'Tools > EMB: {checking_vars["total_new_messages"]} new {message}, {checking_vars["total_new_updates"]} new {update}!')
        elif checking_vars['total_new_messages']:
            string = 'messages' if checking_vars['total_new_messages'] > 1 else 'message'
            bpy.ops.emb.quick_report('INVOKE_DEFAULT', r_type='INFO', r_message=f'Tools > EMB: {checking_vars["total_new_messages"]} new {string}!')
        elif checking_vars['total_new_updates']:
            string = 'updates' if checking_vars['total_new_messages'] > 1 else 'update'
            bpy.ops.emb.quick_report('INVOKE_DEFAULT', r_type='INFO', r_message=f'Tools > EMB: {checking_vars["total_new_updates"]} new {string}!')
    bpy.app.timers.register(notify_user)

def initLocal() -> None:
    global emb_id
    entry = buildEntry()
    emb_id = entry['id']

    class emb_panel(Panel):
        bl_idname = f'EMB_PT_{emb_id}'
        bl_label = '' # i will draw cusotm header
        label = addonData.get('name', addon_path_name)
        bl_category = 'TOOLS'
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_parent_id = 'EMB_PT_main_panel'
        emb_id = entry['id']
        emb_entry = entry
        bl_options = {'DEFAULT_CLOSED'}

        def draw_msg_body(self, context: bpy.types.Context, layout: bpy.types.UILayout):
            entry = self.emb_entry
            if not bool(entry.get('message_board_path')):
                layout.label(text='This EMB is not configured to check for messages.')
                return
            if not entry.get('messages', None):
                layout.label(text='No messages to display!')
                return
            
            if entry['data']['new_messages'] != 0:
                entry['data']['new_messages'] = 0
            
            for id, values in sorted(entry['messages'].items(), key=lambda a: a[0], reverse=True):
                title, text, icons, sizes = values.values()
                icons = icons.rstrip(',').lstrip(',')
                sizes = sizes.rstrip(',').lstrip(',')
                r = layout.row(align=True)
                s = r.split(factor=0.015)
                #r.alignment = 'LEFT'
                s.label(text='')
                col = s.column()
                header, body = col.panel(f'EMB_{self.emb_id}_{id}', default_closed=True)
                header.label(text=title)
                if not body: continue
                r = body.row(align=True)
                s = r.split(factor=0.015)
                s.label(text='')
                body = s.column()
                body.label(text='@ ' + time_to_calendar(id))
                text = text.replace('\\n', '\n')
                lines = text.split('\n')
                icons = icons.split(',')
                while len(lines) > len(icons): # fill icons with default until length is same as text
                    icons.append('BLANK1')
                sizes = list(map(int, sizes.split(',')))
                while len(lines) > len(sizes): # fill sizes with default until length is same as text
                    icons.append(56)
                for line, icon, size in zip(lines, icons, sizes):
                    textBox(body, line, icon, size)


            pass
        def draw_upd_body(self, context: bpy.types.Context, layout: bpy.types.UILayout):
            entry = self.emb_entry
            update_data = entry.get('update_data')
            if entry['version'] == 'N/A_VERSION':
                layout.row().label(text='This EMB is not configured to check for new versions.')
                return None
            if bool(emb_settings.get('update_board_path')):
                pass
            else:
                layout.row().label(text='This EMB is not configured to check for new versions.')
                return None
            
            if not update_data:
                layout.row().label(text='Nothing to show yet...')
                return None

            if update_data['version'] > entry['version']:
                layout.row().label(text='A new update is available.')
                row = layout.row()
                text = 'Ignore Future Versions' if not entry['data']['update_ignore_future_versions'] else 'Notify for Future Versions'
                row.operator('emb.ignore_future_versions', text=text).emb_id = self.emb_id
            elif update_data['version'] == entry['version']:
                layout.row().label(text='You have the latest version.')
            elif update_data['version'] < entry['version']:
                layout.row().label(text='You seem to be on a newer version')
            
            lines = update_data['text'].split('\n')
            icons = update_data['icons'].split(',')
            sizes = map(int, update_data['sizes'].split(','))

            for line, icon, size in zip(lines, icons, sizes):
                textBox(layout, line, icon, size)

            if entry.get('release_repository'):
                layout.operator('wm.url_open', text='Releases Page').url = entry['release_repository']

        if entry.get('failure'):
            def draw_header(self, context):
                text = self.label
                self.layout.label(text=text)
                
            failure_reason = entry['failure']
            def draw(self, context):
                layout = self.layout
                layout.label(text=f'The EMB for {self.label} ({self.emb_id}) failed to register.')
                layout.label(text=self.failure_reason)
        else:
            def draw_header(self, context):
                entry = self.emb_entry
                data = entry['data']
                text = self.label
                notifs = []
                
                if data['new_messages'] == 1:
                    notifs.append('1 Message')
                elif data['new_messages'] > 1:
                    notifs.append(f'{data["new_messages"]} Messages')
                if entry['new_update']:
                    notifs.append('New Update')
                if notifs:
                    notifs = ' (' + ', '.join(notifs) + ')'
                    text += notifs
                self.layout.label(text=text)

            def draw(self, context):
                layout = self.layout
                entry = self.emb_entry

                r = layout.row(align=True)
                s = r.split(factor=0.015)
                #r.alignment = 'LEFT'
                s.label(text='')
                col = s.column()
                msgs_header, msgs_body = col.panel(self.bl_idname+'_msgs', default_closed=True)
                header_text = 'Messages'
                if self.emb_entry['data']['new_messages']:
                    header_text += ' (' + str(entry["data"]["new_messages"]) + ')'
                msgs_header.label(text=header_text)
                if msgs_body:
                    self.draw_msg_body(context, msgs_body)
                    layout.separator()

                r = layout.row(align=True)
                s = r.split(factor=0.015)
                #r.alignment = 'LEFT'
                s.label(text='')
                col = s.column()
                upd_header, upd_body = col.panel(self.bl_idname+'_update', default_closed=True)
                #if (type(entry['version']) == tuple) and (update_data.get('version')):
                if (type(entry['version']) == tuple) and (entry['new_update']):
                    current_ver = '.'.join(map(str, entry['version']))
                    new_ver = '.'.join(map(str, entry['update_data']['version']))
                    up_string = f'Updates (New update! {current_ver} → {new_ver})'
                else:
                    up_string = 'Updates'
                upd_header.row().label(text=up_string)
                if upd_body:
                    self.draw_upd_body(context, upd_body)

    entries = bpy.types.WindowManager.emb_entries
    if (existing := entries.get(emb_id)):
        for cls in existing.get('local_classes', []):
            unregister_class(cls)
        del entries[emb_id]
    entries[emb_id] = entry
    entry.setdefault('local_classes', set()).add(emb_panel)
    register_class(emb_panel)

def register():
    if getattr(bpy.types.WindowManager, 'emb_entries', None) == None:
        initMaster()
    initLocal()
    pass

def unregister():
    entries = bpy.types.WindowManager.emb_entries
    print(global_id)
    if entries.get(global_id):
        print('wow!')
        for cls in entries[global_id]['local_classes']:
            unregister_class(cls)
        del entries[global_id]
    if len(entries) == 0:
        uninitMaster()
    pass