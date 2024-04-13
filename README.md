<img width="960" alt="quickmenu" src="https://github.com/passivestar/quickmenu/assets/60579014/11286afb-2d38-4754-b953-6a33d4b4f6f5">


# Quick Menu is a Blender productivity addon

## Installation

- Go to [Releases](https://github.com/passivestar/quickmenu/releases) and download `quickmenu.zip`
- In Blender go to `Edit -> Preferences -> Addons`
- Press `Install...`
- Select the archive (don't unpack it)

Press `D` in 3D view to open the menu.

Compatible with Blender `4.1.x`

Join our [discord](https://discord.gg/pPHQ5HQ) for discussion.

## Things to know about Quick Menu:

- It's **minimalistic**. The addon is designed to be as unintrusive as possible. It only takes one hotkey (`D` by default) and doesn't have any UI (other than the menu itself)

- It's **quick**. It's designed to be used with one hand, so you can keep your other hand on the mouse. It also promotes usage of accelerator keys, i.e `d11` to Separate/Join, `d13` to Hide/Unhide, etc

- It's **customizable**. You can remove any button from the menu, reorder them, create your own submenus through a JSON config. You can also add your own operators to it, even if they come from third-party addons!

- It's **node-driven**. The addon makes use of Blender 4 node tools where possible, making its python footprint as small as possible, which in turn makes it easier for me to maintain and expand it. You can even look into the `nodetools.blend` file yourself to see how tools are put together. You can also make your own node tools and put them into the menu!

## Tutorial

Click here to watch a video showing every tool from the addon:

<a href="https://youtu.be/55Vju6LYL6M" target="_blank" rel="noreferrer"><img width="600" alt="quickmenututorial" src="https://github.com/passivestar/quickmenu/assets/60579014/5d046839-9cb5-48e7-8be1-89a87ef0a6ef"></a>
