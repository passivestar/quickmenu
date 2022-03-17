# Quick Menu Customization Guide

This is a quick guide on how to customize quick menu!

Open the menu and press `Edit`:

<img width="647" alt="image" src="https://user-images.githubusercontent.com/60579014/158865694-2eab17bb-ac56-43b1-80f4-df0ca5c7bcee.png">

`config.json` file will be opened in the default associated app. In it you will find `items` field with a list of all of the operators:

<img width="673" alt="image" src="https://user-images.githubusercontent.com/60579014/158865944-74885267-a6e0-444f-8bec-f6f9a04b4a49.png">

You can remove, reorder, and rename them however you like. Submenus are generated automatically for all of the paths in `path` fields. Notice how `[Separator]` is used in place of operator title to make separators!

## Adding your own operators

To add an operator to quick menu you must first know its name! The easiest way to find out operator's name is to execute it and look at "Info" area in the "Scripting" workspace. For example if you add a cube you'll see a new `bpy.ops.mesh.primitive_cube_add(size=2, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))` line in the Info area:

<img width="728" alt="image" src="https://user-images.githubusercontent.com/60579014/158867146-b884f98a-c15a-4d23-b2b4-4b3541ef82cb.png">

The name of the operator is `mesh.primitive_cube_add`. Knowing that, you can now add a new button to quick menu like this:

<img width="600" alt="image" src="https://user-images.githubusercontent.com/60579014/158867659-96a105ef-fc65-4c8d-b51e-0773abb5a824.png">

Don't forget to save the `config.json` file after you're done editing it, and press the `Reload` button in quick menu:

<img width="638" alt="image" src="https://user-images.githubusercontent.com/60579014/158867894-ae837248-10f2-4b53-822f-7e4da0b20996.png">

After that you'll be able to find your new `Add Cube` button:

<img width="559" alt="image" src="https://user-images.githubusercontent.com/60579014/158868098-d166992d-cdcf-42e8-9b5a-8d4c75cc69e6.png">

This is it! You'll also find that `config.json` supports more advanced use-cases with parameters (`params` field) and conditional `mode` - your menu item will only be shown if you're in the specified mode!

## Save your config!

Now that you've customized your menu you can copy your `config.json` to a safe place. When you update Blender or quick menu, restoring your menu configuration is just a matter of copying the contents of your config file!
