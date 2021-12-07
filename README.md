<img width="756" alt="image" src="https://user-images.githubusercontent.com/60579014/144963395-4efb1d94-06be-45db-a1ba-b04e8d6647a6.png">

# Quick Menu is a Blender addon that simplifies common tasks

Compatible with Blender 3.x.x

Install through `Edit -> Preferences -> Addons -> Install... -> Select quick_menu.py`.

Press `D` to open the menu.

The addon was initially made only with personal use in mind and therefore is not customizable. However it adds some new operators that some people may find useful. It also simplifies access to some operators and settings. Blender is already very hotkey-friendly, but:

1. Some useful operators are hard to reach, some take several mouse clicks. Some things you can't even fix with editing the keymap (snapping options for example). Quick Menu is optimized for accelerator keys, meaning all of the operators are accessible with just your left hand. All of them follow the pattern `d + {key near d} + {key near d} `. I took into consideration how easy it is to press them as well, combinations that are used frequently have some rolling finger motion in them.

2. Blender doesn't really offer anything that would automate repeating tasks, like macros or whatever. Some of the operators do multiple things at once if it makes sense. Which effectively adds new functionality to Blender.

3. Blender's defaults don't always make sense for my workflow, and a lot of the operators could be context-dependent. A lot of operators address this by calling existing Blender operators with proper settings. For example I believe that "Shade Smooth", "Origin To (whatever)", operators that add modifiers and booleans should work regardless of what mode you're in. I believe that Separate/Join should be one button. Same is true for Region To Loop/Loop To Region, Add Mirror/Apply Mirror, etc. I believe that some operators (like mirror) should take into consideration your camera orientation when initially setting the axis. The list goes on. The addon is very opinionated.

This addon is the result of over a year of brainstorming on the effectiveness of modeling/texturing workflow and testing tools on small projects. I'm trying to keep it lightweight. If something seems missing from it, there's a high chance that the reason for it is that Blender already has built-in tools that allow to do it easily, or the use-case for it is very rare

# Some tools

Here are some examples of tools that Quick Menu has. Keep in mind that this is not a complete list of operators, but rather a small showcase of what kind of things the addon is capable of. Only some modeling tools are listed, but the addon also has some operators for UVs, textures, export, etc

## Convert To Curve (d41)

Allows to create tubes out of selected edges with either round or square cross-section. Can be used without leaving edit mode. Usage: `d+4+1`

https://user-images.githubusercontent.com/60579014/144755827-a266b00b-48dc-4c22-9a4e-1394661a7244.mp4

## Add geometry (d35)

Creates a circle or a square aligned to the selected face. Usage: `d+3+5`. Press `shift` to make a square

https://user-images.githubusercontent.com/60579014/144756196-095bd26d-4858-4e07-9136-84ed9e30b4ca.mp4

## Loop/Region (d23)

Like some other Quick Menu operators (for example Separate/Join) it unifies multiple existing Blender operators into one. So instead of having to remember two separate hotkeys for **Select Loop Inner Region** and **Select Boundary Loop**, you can now just press `d+2+3`, and the addon will decide what to do depending on what mode you're in

https://user-images.githubusercontent.com/60579014/144756341-7118b1d6-530a-4078-be33-4285aea99f4e.mp4

## Bbox around selection (d33)

Creates a bounding box around selected elements in edit mode. Can also create bounding plane/line, depending on the selection. Usage: `d+3+3`

https://user-images.githubusercontent.com/60579014/144756430-140a32c6-eb1f-4aab-9a0d-888248327d3e.mp4

## Booleans (de1, de2, de3)

Context-dependent boolean, works in both object and edit mode. This operator will pre-scale selection by a small margin before applying boolean to avoid problems with coplanar faces. Works well with Blender's existing Add Cube tool (dd1). Usage: `d+e+1` for union, `d+e+2` for difference, `d+e+3` for intersection

https://user-images.githubusercontent.com/60579014/144756519-391baa08-dee5-4dec-bf04-3ec5a6c1d279.mp4

## Connect (d3c)

Connects selected isolated islands with an edge. Will make a face if more than 2 islands selected. Usage: `d+3+c`

https://user-images.githubusercontent.com/60579014/144756578-f691250c-3c8e-4c91-af25-ea6a358dfa56.mp4

## Flatten (d3f)

A faster way to flatten compared to s+{axis}+0+enter. This operator is view-dependent. Usage: `d+3+f`

https://user-images.githubusercontent.com/60579014/144756616-e5e419dd-2391-49d9-8d30-689f9fa237e7.mp4

## Randomize (d3r)

Randomize operator that works in both object and edit mode (on separate islands). Usage: `d+3+r`

https://user-images.githubusercontent.com/60579014/144756689-56c48fa7-7785-497e-b01b-7138f2af63b7.mp4

## Spin (d32)

Effectively presets for the existing spin operator. Usage: `d+3+2`

https://user-images.githubusercontent.com/60579014/144756715-db3d8e43-1f4f-4f2c-88bd-19e3fd7f1591.mp4

## Plane Intersect Island (deq)

A view-dependent operator that cuts an island with a plane that goes through the center of the active element and oriented towards the viewport camera (Snapped to 90 degrees by default). Convenient for cutting through complex meshes with ngons. Usage: `d+e+q`

https://user-images.githubusercontent.com/60579014/144756825-279283d8-11eb-4903-819c-1020afa5e47c.mp4

## Projection Intersect (der)

Projects selected elements to unselected. Just like the previous one, this operator is view-dependent. Flattens selection before projecting. Usage: `d+e+r`

https://user-images.githubusercontent.com/60579014/144756881-636be8e4-68c4-421f-96f9-c054798914b2.mp4

## Knife Intersect (dee)

Similar to Blender's **Intersect (Knife)** (Ctrl+F+k), but removes the original geometry. Usage: `d+e+e`

https://user-images.githubusercontent.com/60579014/144757002-0111d3fd-9039-4bd6-ab83-70333950e0fd.mp4
