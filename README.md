# Easy Message Board
## Introduction
The "Easy Message Board" system allows developers to seamlessly integrate a message board into their add-on. This ensures no one gets left out of the loop for new updates or things they should know.  

It's an @everyone for Blender!

Easy Message Board is located in the `Tool` panel of Blender.  
  
<img width="60%" alt="image" src="https://github.com/user-attachments/assets/09e1bb01-97ec-48e9-bbf6-547e43a77549" />

## How it works
Based on a user-defined interval, the EMB system will regularly update its message board with data uploaded from the developer. Updates are done through visiting a URL that contains raw text. What's easier than that? Update data is a regular .json file, whereas message data has a special format that makes it easier to add new messages. Make a new line and copy new message data.

## User settings
Users can change how EMB works, such as the checking interval, the notification sound & volume, they may disable notifications, or the EMB system as a whole.

<img width="417" height="253" alt="image" src="https://github.com/user-attachments/assets/5a18316f-b1d3-40c4-a9aa-6609628c181f" />


# Using Easy Message Board as a developer
## Integrating EMB
To integrate Easy Message Board into your add-on, place the `easy_message_board` folder at the root of your add-on. In your `__init__.py` file, import EMB's register and unregister functions and execute them in your main register and unregister functions.

```py
import bpy
from . import easy_message_board

bl_info = {
    ...
}

def register():
    ...other_register_data
    easy_message_board.register()

def unregister():
    ...other_unregister_data
    easy_message_board.unregister()
```

Next, configure the EMB template to suit your add-on.  

In `easy_message_board/settings.json`, there are four parameters to set:
- `id`: a unique ID for your EMB
- `message_board_path`: A URL leading to raw text formatted in a special way
  - Optional, but required if `update_board_path` is not defined
- `update_board_path`: A URL leading to raw text formatted as a .json file
  - Optional, but required if `message_board_path` is not defined
  - A `.toml` manifest or `bl_info` dictionary with version data mentioned is required
- `release_repository`: A URL leading to a download page (optional)

For message and update board URLs, they are required to host raw text data. Hosting files on GitHub, or pastes on PasteBin, are both valid text hosters.

As an example, this is how OptiPloy Pro's EMB settings are configured:
```json
{
    "id": "optiploy-pro",
    "message_board_path": "https://pastebin.com/raw/4uZJLM5w",
    "update_board_path": "https://pastebin.com/raw/r8zqTpYc",
    "release_repository": "https://superhivemarket.com/products/optiploy-pro"
}
```

## Message data format
Message data consists of a timestamp, title, text lines, icons, and line sizes, all separated by a `¸` character. This is not a comma.  

Example:
```
1756071044¸Check out this new tutorial!¸Sample Text One\nSample Text Two¸DOT,ERROR¸56,56
1756071100¸New Deal on Add-On!¸Sample Text Three\nSample Text Four¸TEXT,TEXTURE¸56,56
```
Different messages should be separated by new lines.

## Update data format
Update data is a simple .json file, containing version data, title, text lines, icons, and line sizes.  

Example:
```.json
{
  "version": [
    1,
    2,
    0
  ],
  "title": "MAL Tools 1.2",
  "text": "UI Code has been fixed\nPerformance on the Nool Bool has improved",
  "icons": "TOOL_SETTINGS,SETTINGS",
  "sizes": "56,56"
}
```
New update data should replace the old update data entirely.

## Message generation tool
Because this is an Easy Message Board, you have a tool to create message data! You can enable this tool to show by going to `Adjust Preferences > Show Developer Message Generator`  
<img width="633" height="614" alt="image" src="https://github.com/user-attachments/assets/306b0dfa-0fbd-4110-a81f-4fce16db9439" />

At the top is a switch between generating message or update data.

There are parameters for icons, text, line sizes, and to turn a text box into a URL. If `is_url` is enabled, icon parameters become URL parameters, and text parameters become URL Name parameters.  
<img width="628" height="609" alt="image" src="https://github.com/user-attachments/assets/40be91f4-ad7e-43a3-8fc7-d6f2180bb530" />

If a message is set to `Is Update`, a version parameter shows to change major, minor, and patch info.  
<img width="629" height="510" alt="image" src="https://github.com/user-attachments/assets/5d25cae0-7d0d-4457-adc1-8eff3f66b9bc" />



When you are finished with your message, click `Copy Text Boxes to clipboard`.  
If you are updating your message board, open up the file editor and paste the message data in a new line.  
If you are updating your update board, open up the file editor and replace the old data with the new data entirely.  
<img width="846" height="893" alt="image" src="https://github.com/user-attachments/assets/53246e55-d44e-4d6c-b28c-ca653e091ed7" />

Once your file is saved, your EMB should update with the changes!

# Credits
Created by hisanimations
