
<img width="960" alt="qm" src="https://github.com/passivestar/quickmenu/assets/60579014/6b419737-61f4-419c-9e14-5db46e104fcc">

# Quick Menu is a minimalistic productivity addon for Blender

## Installation

- Click on `Releases` on the right and download `quickmenu.zip`
- In Blender go to `Edit -> Preferences -> Addons`
- Press `Install...`
- Select the archive (don't unpack it)

Press `D` in 3D view to open the menu.

Compatible with Blender `4.x.x`

Join our [discord](https://discord.gg/pPHQ5HQ) for discussion.

## Things to know about Quick Menu:

- It's **minimalistic**. The addon is designed to be as unintrusive as possible. It only takes one hotkey (`D` by default) and doesn't have any UI (other than the menu itself)

- It's **quick**. It's designed to be used with one hand, so you can keep your other hand on the mouse. It also promotes usage of accelerator keys, i.e `d11` to Separate/Join, `d13` to Hide/Unhide, etc

- It's **customizable**. You can remove any button from the menu, reorder them, create your own submenus through a JSON config. You can also add your own operators to it, even if they come from third-party addons!

- It's **node-driven**. The addon makes use of Blender 4 node tools where possible, making its python footprint as small as possible, which in turn makes it easier for me to maintain and expand it. You can even look into the `nodetools.blend` file yourself to see how tools are put together. You can also make your own node tools and put them into the menu!
