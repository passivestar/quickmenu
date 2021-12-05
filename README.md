![Quick Menu](https://github.com/passivestar/quickmenu/blob/main/pics/qm.jpg?raw=true)

Quick Menu is a Blender addon that I made to optimize my workflow.

Install it through `Edit -> Preferences -> Addons -> Install... -> And select quick_menu.py`.

Press `D` to open the menu.

The addon was initially made only with personal use in mind and therefore is not customizable. However it adds some new operators that some people may find useful. It also simplifies access to some operators and settings. Blender is already very hotkey-friendly, but:

1. Some useful operators are hard to reach, some take several mouse clicks. Some things you can't even fix with editing the keymap (snapping options for example). Quick Menu is optimized for accelerator keys, meaning all of the operators are accessible with just your left hand. All of them follow the pattern `d + {key near d} + {key near d} `. I took into consideration how easy it is to press them as well, combinations that are used frequently have some rolling finger motion in them.

2. Blender doesn't really offer anything that would automate repeating tasks, like macros or whatever. Some of the operators do multiple things at once if it makes sense. Which effectively adds new functionality to Blender.

3. Blender's defaults don't always make sense for my workflow, and a lot of the operators could be context-dependent. A lot of operators address this by calling existing Blender operators with proper settings. For example I believe that "Shade Smooth", "Origin To (whatever)", operators that add modifiers and booleans should work regardless of what mode you're in. I believe that Separate/Join should be one button. Same is true for Region To Loop/Loop To Region, Add Mirror/Apply Mirror, etc. I believe that some operators (like mirror) should take into consideration your camera orientation when initially setting the axis. The list goes on. The addon is very opinionated