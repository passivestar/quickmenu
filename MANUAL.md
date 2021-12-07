# Quick Menu Operators

This list contains descriptions for each quick menu operator. Some of the operators are default blender operators and are included in the quick menu because the default hotkey for it is not left-hand friendly. The default blender operators are in ***cursive***.

## General

`d11` **Separate/Join.** Join objects into one if in object mode. Separate selection if in edit mode. Optionally set the origin to the separated geometry.

`d12` **Set shade smooth.** Enable smooth shading. Optionally enable autosmooth. Use redo panel to tweak the angle. Works in any mode.

`d13` **Local View.** Isolate selection if in object mode. Hide/reveal unselected if in edit mode.

`d14` **Origin To Geometry.** Set origin to the center of selected elements if in edit mode. If not in edit mode or nothing is selected set origin to the object bounds.

`d15` **Origin To Bottom.** Set origin to the bottom of the object. Works with multiple objects. Works in any mode.

`d16` **Origin To Cursor.** Set origin to the cursor.

`d1q` **Toggle Proportional Editing.** Works in any mode. Use redo panel for settings

`d1w` **Toggle Wireframe.** Wireframe can be toggled in the blender's viewport overlays panel. Included in the quick menu as it's convenient for inspecting multiple objects at once.

`d1e` **Rotate 90.** View-dependent rotate, uses 90-degree snapped camera angle as an axis for rotation. Rotates clockwise. Look from the other side to rotate in the other direction. Faster than `r+{axis}+90+enter`.

`d1a` ***Mirror.*** Interactive mirror, use middle mouse button to choose mirror axis.

`d1d` **Draw.** Add a new gpencil object and switch to gpencil paint mode. You can convert your gpencil to mesh with `d43`. Can be used to quickly draw ngons by hand.

`d1f` ***Make Links.*** Faster than `Ctrl+L`.

`d1g` **Apply to Multiuser.** Use this operator if you copied a bunch of objects with `Alt+D` and can't apply transforms to them anymore.

`d1z` ***Make Parent.*** Faster than `Ctrl+P`.

## Select

`d21` **Select Ring.** Hold shift (`d+2+shift+1`) to select loop

`d22` **Select More.** Faster than numpad (`Ctrl+Numpad+`). If you need to select more multiple times it's faster to switch to `Shift+R` after your first `d22`. Hold shift (`d+2+shift+2`) to select less.

`d23` **Region To Loop.** Region to Loop if in face mode. Loop to Region if in edge mode. Use the redo panel to invert the selection.

`d24` **View Parallel Edges** View-dependent selection, check the redo panel for options.

`d25` **View Facing Faces.** View-dependent selection, check the redo panel for options.

`d2q` ***Linked Flat.*** Can be useful for manual UV unwrapping.

`d2w` ***Select Loose.*** 

`d2e` **Select Sharp Edges.** Optionally select sharp edges only in selected geometry.

`d2a` **Invert Selection Connected.** Works like `Ctrl+I` but keep selection limited to connected geometry only.

`d2x` ***Random.***

`d2c` ***Checker Deselect.***

## Modeling

`d31` **Add Single Vertex.** Adds a vertex at the cursor. Works in any mode.

`d32` **Spin.** Presets for the default Spin operator (`Alt+E+S`).

`d33` **Bbox around selection.** Creates a bounding box around the selected geometry in edit mode.

`d34` **Add Geometry.** Adds a circle geometry on selected faces, oriented to their normal. Hold shift to create a square.

`d3q` ***Recalculate Normals.***

`d3e` **Extrude Both Ways.** Extrude along normals, but extrudes faces both ways.

`d3r` **Randomize Transform.** Similar to `Object->Transform->Randomize Transform`, but also works in edit mode. Useful when you want to quickly add disorder to your object without having to separate it into pieces.

`d3f` **Flatten.** View-dependent operator, scales to 0 on an axis parallel to the viewport camera view, snapped to 90 degrees. Optionally removes doubles from the resulting geometry. Faster than `s+{axis}+0+enter`.

`d3x` ***Convex Hull.***

`d3c` **Connect Selected.** Connects selected isolated geometry islands with an edge. Will make a face if more than 2 islands are selected.

`d3v` ***Vertices Smooth.*** Sometimes this is enough and you don't need subsurf.

## Convert/Modify

`d41` **Curve.** Adds curves to selected edges. Optionally can set resolution automatically. Optionally can make a separate object. Optionally can make a curve with a square profile. Optionally can delete the initial selection.

`d42` **Skin.** Adds a skin modifier to selected edges, works in object or edit mode.

`d43` **Mesh.** Convert object(s) to mesh. Can be used to quickly apply modifiers. Check the redo panel for additional settings for conversion of gpencil objects.

`d44` **Mirror.** Adds a mirror modifier to the bottom of the modifier stack. Bisects the mesh. View-dependent. Uses camera angle to determine mirror axis. Mirrors left to right (so if you need to mirror on the Z axis you'll need to set it manually in the redo panel). If the active object already has a mirror, applies the existing mirror instead of adding a new one. So `d44` can be used to quickly toggle mirror modifier.

`d45` **Subsurf.** Adds a multires modifier to the bottom of the modifier stack if in sculpt mode. Adds subsurf otherwise. If the modifier already exists, changes its settings. Check the redo panel for settings.

`d4q` **Bevel.** Adds a bevel modifier to the bottom of the modifier stack. If the modifier already exists, changes its settings.

`d4w` **Solidify.** Adds a solidify modifier to the bottom of the modifier stack. If the modifier already exists, changes its settings.

`d4e` **Triangulate.** Adds a triangulate modifier to the bottom of the modifier stack. If the modifier already exists, changes its settings.

`d4a` **Array.** Adds an array modifier. View-dependent, uses camera angle to determine offset vector.

`d4f` **Twist.** Adds a twist modifier.

`d4z` **Clear Modifiers.** Removes all of the modifiers from an object.

## Delete/Split

`dq1` ***Merge.*** Merge at center

`dq2` ***Merge By Distance.***

`dq3` ***Limited Dissolve.***

`dq4` ***Decimate Geometry.***

`dq5` ***Delete Loose.***

`dqq` **Delete Back Facing Faces.** View-depedent (90 deg snapped by default), deletes faces facing away from the camera. Works on selected geometry. Use redo panel to change threshold or make it use non-snapped camera angle.

`dqw` **Delete Back/Front Facing Faces.** View-depedent (90 deg snapped by default), deletes faces facing away from the camera and towards the camera. Works on selected geometry. Use redo panel to change threshold or make it use non-snapped camera angle.

`dqe` ***Edge Split.***

`dqr` **Separate by Loose Parts.** Separates selected geometry into loose parts and links their mesh data. Can be useful if you have several identical islands in edit mode that you want to edit simultaneously.

`dqs` ***Split.***

## UV/Textures

`dw1` **Mark Seam.** If in edge mode, mark seam. If in face mode, mark boundary loop as a seam. Optionally clear all of the seams inside of the selection before marking.

`dw2` **Clear Seam.** Same as previous, but clears seams instead.

`dw3` ***Unwrap.***

`dw4` **Straighten UVs.** Straightens a UV island (selection) by first straightening the active face, and then calling "Follow Active Quads".

`dw5` ***View Project.***

`dwq` **Mark Seams Sharp.** Selects sharp edges in selected geometry and marks them as seams. Optionally also marks seams from islands (see next operator). Use redo panel to tweak sharpness.

`dww` **Mark Seams From Islands.** Marks seams from islands in 3D view without having to open UV editor. Useful when you already have some geometry with proper UVs but without seams. For example, geometry generated with curves will already have proper UV's that can be marked.

`dwd` **Set Vertex Color.** Assigns unique vertex colors to selected geometry. Works with multiple objects. Every new call to this operator will assign a new color, different enough from the previous one (tested with Substance Painter). Optionally selects linked geometry before assigning colors. Can be used to copy vertex colors. Check "Set To Active" if you want to copy vertex color from active face to selected. You can also select your own color in the redo panel, make sure to uncheck "Set To Active" if you want to do so.

`dwf` **Select By Vertex Color.** Selects all of the faces that have the same color as the active one.

`dwg` **Bake ID Map.** Bakes an ID map from vertex colors of selected objects and saves it alongside your blend file. Blend file must be saved. Renderer must be set to Cycles. All of the selected objects must have exactly 1 material, which is the same in all of the objects. This operator is useful when working with texturing tools that don't have their own ID Map bakers (for example Quixel Mixer).

## Boolean/Knife

`de1` **Union.** Works in both object and edit mode. Will change display type to "bounds" when used in object mode. Optionally pre-scales the selected geometry to avoid problems with coplanar faces.

`de2` **Difference.** Same as `de1` but for difference operation. Cuts selected from active in object mode, or selected from unselected in edit mode.

`de3` **Intersect.** Same as `de1` but for intersect operation.

`deq` **Plane Intersect Island.** A view-dependent operator that cuts an island with a plane that goes through the center of the active element (optionally can be changed to the center of selected geometry) and is oriented towards the viewport camera (Snapped to 90 degrees by default). Convenient for cutting through complex meshes with ngons. Optionally clears the inner/outer side of the intersection plane. Optionally can be changed to cut through the whole mesh instead of the island.

`dew` **Plane Intersect Selection.** Same as `deq` but only cuts through selection

`dee` **Knife Intersect.** Similar to Blender's Intersect (Knife) (`Ctrl+F+K`), but removes the original geometry.

`der` **Projection Intersect.** View-depedent. Projects selected elements to unselected. Flattens selection before projecting. 

`dea` **Weld Edges into Faces.** Similar to `Ctrl+F+O` but selects everything before doing the operation.

## Animation

`dr1` **Parent To New Empty.** Parents selection to a new empty.

`dr2` ***Add Constraint.***

`drz` **Clear Drivers.** Removes all of the drivers from selected objects.

`drx` **Drivers Set Use Self.** Sets "Use Self" to true for all of the selected objects. "self" is useful when using driver expressions that need to access object they are used on.

## Snapping

`da1` **Bounding Box Pivot.** Sets transform pivot to bounding box center.

`da2` **Individual Pivot.** Sets transform pivot to individual origins.

`da3` **3D Cursor Pivot.** Sets transform pivot to 3D cursor.

`da4` **Global Orientation.** Sets transform orientation to global.

`da5` **Normal Orientation.** Sets transform orientation to normal. Sets transform pivot to the active element. Using normal orientation with active element pivot makes it possible to avoid having to create a new orientation in a lot of cases.

`da6` **New Orientation.** Creates a new orientation. Overwrites a custom orientation if it already exists.

`dav` **Vertices.** Sets snapping to vertices and edge centers.

`daf` **Faces.** Sets snapping to faces. Enables align rotation.

`dar` **Grid.** Sets snapping to grid.

`dac` **Closest.** Sets snapping to closest. Sets transform pivot to Bounding Box Center because it's what you usually want with closest snapping.

`dae` **Center.** Sets snapping to center.

## Tool

`dd1` ***Add Cube*** Works in both object mode and edit mode.

`dd2` ***Add Cylinder*** Works in both object mode and edit mode.

`dd3` ***Add Sphere***  Works in both object mode and edit mode.

`ddq` ***Shear***

## Mode

Faster than the default blender way of switching modes (`Ctrl+Tab+{1,2,3,...}`)

`dfq` **Paint.**

`dfw` **Edit.**

`dfa` **Sculpt.**

`dfs` **Object.**

`dfz` **Weight Paint.**

## Files

`dzz` **Export FBX.** Exports FBX alongside the saved blend file, using the same name as the blend file. Sets mesh smooth type to EDGE, applies modifiers (optionally), sets add leaf bones to False, sets bake anim use nla strips to False.

`dzx` **Export GLB.** Exports GLB alongside the saved blend file, using the same name as the blend file. Applies modifiers (optionally).

`dzc` **Reload All Textures.** Reloads all textures, useful when working with external texturing software.

## Other

`dv` **View Selected/Camera** View selected if anything is selected (in any mode), view camera otherwise. Faster than `Numpad .` and `Numpad 0` as it's on the left side of the keyboard and can be pressed without looking with a simple rolling finger motion. Faster than Blender 3.0 `D+mousemove` as there are 8 different items in the View menu, which means only 45 degrees per item, so it can be tricky to consistently hit what you want.
