# Quick Menu is a Blender addon for better efficiency

## Watch an in-depth review on YouTube:

[![quickmenuthumbyt](https://user-images.githubusercontent.com/60579014/152310865-a3f15da4-091a-4c25-8e53-74356db326c6.jpg)](https://youtu.be/SPIkZEnhtTk)

## Installation

- Download zip
- Go to `Edit -> Preferences -> Addons`
- Press `Install...`
- Select the archive

Press `D` in 3D view to open the menu.

Compatible with Blender `3.x.x`

Every operator is described in the [manual](https://github.com/passivestar/quickmenu/blob/main/MANUAL.md).

As of version `2.0.0`, quick menu is completely customizable. Find out how to do it in the [customization guide](https://github.com/passivestar/quickmenu/blob/main/CUSTOMIZATION.md).

Join our [DISCORD for discussion](https://discord.gg/pPHQ5HQ).

## Design choices

The addon was initially made with personal use in mind. However since it only binds one key (configurable, `D` by default) it's unintrusive and it should be easy to use it alongside other addons. It simplifies access to operators and settings and adds some new operators. Blender is already hotkey-friendly, but:

1. Some useful operators are hard to reach, some take several mouse clicks. Some things you can't even fix with editing the keymap (snapping options for example). Quick Menu is optimized for accelerator keys, meaning all of the operators are accessible with just your left hand. All of them follow the pattern `d + {key near d} + {key near d} `. I took into consideration how easy it is to press them as well, combinations that are used frequently have some rolling finger motion in them.

2. Blender doesn't really offer anything that would automate repeating tasks, like macros or whatever. Some of the operators do multiple things at once if it makes sense. Which effectively adds new functionality to Blender.

3. Blender's defaults don't always make sense for my workflow, and a lot of the operators could be context-dependent. A lot of operators address this by calling existing Blender operators with proper settings. For example, I believe that "Shade Smooth", "Origin To (whatever)", operators that add modifiers and booleans should work regardless of what mode you're in. I believe that Separate/Join should be one button. The same is true for Region To Loop/Loop To Region, Add Mirror/Apply Mirror, etc. I believe that some operators (like mirror) should take into consideration your camera orientation when initially setting the axis. The list goes on. The addon is very opinionated.

This addon is the result of over a year of brainstorming on the effectiveness of modeling/texturing workflow and testing tools on small projects. I'm trying to keep it lightweight. If something seems missing from it, there's a high chance that the reason for it is that Blender already has built-in tools that allow to do it easily, or the use-case for it is very rare.

This addon is designed to be as unintrusive and minimalistic as possible. All of the operators are in just one menu. There's no UI other than that, which makes it easy to use. It also only takes one hotkey. It can be changed in the addon's preferences, but I recommend `D`.

As of version `2.0.0` this addon is completely customizable via a json config. You can remove, reorder and add operators to the menu. You can also create as many custom submenus as you like! It still ships with a default config that I found to be the most efficient for my workflow, but now you can make it work for any workflow.

This addon is a single-file addon for now, and it will probably stay that way because it simplifies development (reloading addons consisting of multiple files is not as straightforward as just pressing `Alt+R, Alt+P` in Blender's text editor).

# Some tools

Here are some examples of tools that Quick Menu has. Keep in mind that this is not a complete list of operators, but rather a small showcase of what kind of things the addon is capable of. Only some modeling tools are listed, but the addon also has some operators for UVs, textures, export, etc. Check out the [manual](https://github.com/passivestar/quickmenu/blob/main/MANUAL.md) for the complete list.

## Convert To Curve `d41`

Allows to create tubes out of selected edges with either round or square cross-section. Can be used without leaving edit mode. Usage: `d+4+1`

https://user-images.githubusercontent.com/60579014/144968116-8794db13-8eba-4678-a38b-02b1ef2ffcf4.mp4

## Add geometry `d34`

Creates a circle or a square aligned to the selected face. Usage: `d+3+5`. Press `shift` to make a square

https://user-images.githubusercontent.com/60579014/144968178-b1c6a525-d50c-41b8-b910-5bba49d1ee5b.mp4

## Loop/Region `d23`

Like some other Quick Menu operators (for example Separate/Join) it unifies multiple existing Blender operators into one. So instead of having to remember two separate hotkeys for **Select Loop Inner Region** and **Select Boundary Loop**, you can now just press `d+2+3`, and the addon will decide what to do depending on what mode you're in

https://user-images.githubusercontent.com/60579014/144968197-413347df-e7f2-4c0e-b40f-ca4991bfd0e7.mp4

## Bbox around selection `d33`

Creates a bounding box around selected elements in edit mode. Can also create a bounding plane/line, depending on the selection. Usage: `d+3+3`

https://user-images.githubusercontent.com/60579014/144968212-b2226456-0337-4e50-98d8-2629905ae7a5.mp4

## Booleans `de1`, `de2`, `de3`

Context-dependent boolean, works in both object and edit mode. This operator will pre-scale selection by a small margin before applying boolean to avoid problems with coplanar faces. Works well with Blender's existing Add Cube tool (dd1). Usage: `d+e+1` for union, `d+e+2` for difference, `d+e+3` for intersection

https://user-images.githubusercontent.com/60579014/144968226-bad9d7c1-a3fb-4ef8-867d-e02816516096.mp4

## Connect `d3c`

Connects selected isolated islands with an edge. Will make a face if more than 2 islands are selected. Usage: `d+3+c`

https://user-images.githubusercontent.com/60579014/144968238-653f0050-bb70-4c8b-9ca5-66406e2b04a7.mp4

## Flatten `d3f`

A faster way to flatten compared to s+{axis}+0+enter. This operator is view-dependent. Usage: `d+3+f`

https://user-images.githubusercontent.com/60579014/144968254-a80fa6a5-3651-48da-bdae-42310fe175f4.mp4

## Randomize `d3r`

Randomize operator that works in both object and edit mode (on separate islands). Usage: `d+3+r`

https://user-images.githubusercontent.com/60579014/144968273-9d594cfb-a272-4b67-be1c-eed9b765d286.mp4

## Spin `d32`

Effectively presets for the existing spin operator. Usage: `d+3+2`

https://user-images.githubusercontent.com/60579014/144968287-13dc5dd6-ed32-4eed-8c96-a875125cb014.mp4

## Plane Intersect Island `deq`

A view-dependent operator that cuts an island with a plane that goes through the center of the active element and is oriented towards the viewport camera (Snapped to 90 degrees by default). Convenient for cutting through complex meshes with ngons. Usage: `d+e+q`

https://user-images.githubusercontent.com/60579014/144968296-faa874e2-1943-4afd-b829-67d7ad8d4637.mp4

## Projection Intersect `der`

Projects selected elements to unselected. Just like the previous one, this operator is view-dependent. Flattens selection before projecting. Usage: `d+e+r`

https://user-images.githubusercontent.com/60579014/144968311-8e21f0ed-fe8a-4bb3-8524-76641cf296dc.mp4

## Knife Intersect `dee`

Similar to Blender's **Intersect (Knife)** (Ctrl+F+K), but removes the original geometry. Usage: `d+e+e`

https://user-images.githubusercontent.com/60579014/144968335-d090d305-2f23-4fdb-993b-f8591e1ed470.mp4
