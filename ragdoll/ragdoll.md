The control list in is a strong V1 minimum because it matches the two joint families we actually found in shipped files. But there are three hard caveats:

The current backend does not support per-joint limited hinge export yet. The schema only has one constraint shape with pivot, twist axes, plane axes, twist min/max, cone angle, and plane min/max in json_ragdoll_input.h:50, and the builder always creates hkpRagdollConstraintData in ragdoll_scene_builder.cpp:160. The current Python exporter also hardcodes ragdoll-style constraints in ragdoll_export.py:764. So a hinge type selector in the UI would be ahead of the actual exporter unless we extend the schema and C++ path first.
Joint friction torque is important in Relic data, but the current ragdoll constraint schema does not expose it. What exists today is rigid-body surface friction on RawRigidBody in json_ragdoll_input.h:29, mapped to body friction in ragdoll_scene_builder.cpp:148, and currently emitted as a body field in ragdoll_export.py:744. That is not the same thing as Havok joint friction torque from the constraint docs.
Havok’s own constraint model makes the limits meaningful only relative to the local joint frames. The doc is explicit that cone, plane, and twist are defined against the constraint axes in Havok Documentation 5.5.x.md:6320 and that the plane axis must be perpendicular to the twist axis in Havok Documentation 5.5.x.md:6343. So if the UI exposes only numbers and not the pivot plus frame axes, the user does not really have most of the control.
The good news is that rigid-body editing is already very feasible with the current backend. The raw rigid body schema already supports sphere, box, and capsule-like data in json_ragdoll_input.h:29, the builder creates those shapes in ragdoll_scene_builder.cpp:103, and the current exporter already auto-generates sphere or capsule bodies in ragdoll_export.py:676. So capsule radius and length resizing, skeleton generation, and viewport body previews are absolutely in scope right now.



Yes. The cleanest way to think about it is:

Animation skeleton: the normal character bone rig used by animation.
Ragdoll skeleton: the physics bone rig used by Havok.
Bone mapping: how a ragdoll bone points back to an animation bone.
Rigid body: the actual capsule, sphere, or box attached to one ragdoll bone.
Constraint: the joint rule between two rigid bodies, like shoulder, elbow, knee.
The current exporter data shape is defined in json_ragdoll_input.h:1, the current Python exporter is building that JSON in ragdoll_export.py:636, and there is still no ragdoll UI panel yet, only the existing physics panel pattern in physics_panels.py:1.

Plain-English Map

Thing	What it means in human terms
Animation skeleton	The normal character bones
Ragdoll skeleton	The physics version of the bones
Bone mapping	Which physics bone corresponds to which animation bone
Rigid body	The visible collision shape, usually a capsule
Constraint	The rule that says how one body may move relative to another
Pivot	The point where the joint connects
Twist axis	The axis the limb twists around
Plane axis	The axis used to clip the cone of motion
Cone limit	The main swing allowance
Plane min/max	The extra clipping of that swing allowance
Hinge min/max	The one-axis bend limit for hinge joints
Body friction	Surface friction of the rigid body itself
Joint friction torque	Resistance inside the joint itself
Skeleton And Mapping

Area	What we have for Blender backend	What we need for Blender backend/frontend	What DoW2 HKX files have / how we match it
Animation skeleton	Already supported: name, bones, parent indices, reference pose in json_ragdoll_input.h:9 and exported from ragdoll_export.py:636	UI to inspect it, but not much manual editing is needed for V1	DoW2 ragdolls are paired with animation skeleton data; this already matches the exporter model
Ragdoll skeleton	Already supported: name, bones, parent indices, reference pose in json_ragdoll_input.h:9	UI to create or edit which bones are part of the ragdoll and their hierarchy	Shipped HKX clearly has a ragdoll skeleton separate from animation; this matches the current exporter concept
Bone mapping	Already supported: ragdoll bone index, anim bone index, transform in json_ragdoll_input.h:17 and emitted in ragdoll_export.py:652	UI to show and override mappings when auto-detection is wrong	DoW2 HKX uses mapping between ragdoll and animation bones; current structure is aligned
Rigid Bodies

Property / area	What we have for Blender backend	What we need for Blender backend/frontend	What DoW2 HKX files have / how we match it
Rigid body list	Already supported in json_ragdoll_input.h:25 and created in ragdoll_export.py:676	UI list of one body per ragdoll bone	Shipped HKX has one rigid body per ragdoll link; current exporter model matches that
Name	Already supported	UI label only	Matches shipped named bodies
Bone index	Already supported	UI should show which ragdoll bone owns the body	Matches shipped rigid-body-to-bone relationship
Shape type	Already supports sphere, box, capsule in ragdoll_scene_builder.cpp:103	UI shape selector, likely V1 just sphere and capsule	Shipped ragdolls mainly use capsules and some spheres like heads; this matches
Radius	Already supported	UI numeric editing and gizmo resizing	Matches shipped body sizing
Vertex A / Vertex B	Already supported for capsules in json_ragdoll_input.h:25 and emitted in ragdoll_export.py:706	UI for capsule length/height editing; user does not need to think in raw vertices if you expose “capsule length”	This is how we match capsule height/orientation to shipped HKX
Half extents	Already supported for boxes	Probably advanced-only UI, not needed for first pass	Not important for matching sampled shipped ragdolls unless you later expose boxes
Mass	Already supported	UI numeric editing or presets per body type	Shipped bodies do have mass properties; current backend can represent them
Body friction	Already supported as rigid-body friction in json_ragdoll_input.h:25 and ragdoll_scene_builder.cpp:121	UI field if desired, but this is not joint friction	Present in Havok rigid bodies, but separate from the important joint friction we found in shipped constraints
Restitution	Already supported	Advanced-only UI	Can be exposed later
Motion type	Already supported in ragdoll_scene_builder.cpp:115	Likely hidden or advanced-only for ragdolls	DoW2 ragdoll bodies are dynamic physics bodies; current backend can express this
Position / rotation	Already supported	Mostly auto-derived; advanced manual override optional	Needed to match shipped placement
Linear damping / angular damping	Already supported	Advanced-only UI or presets	Relevant but not the first thing a user should see
Collision filter info	Already supported	Probably hidden in V1	Present in HKX, but not a core user control
Quality type	Already supported	Probably hidden in V1	Present in HKX, but not a core user control
Constraints / Joints

Property / area	What we have for Blender backend	What we need for Blender backend/frontend	What DoW2 HKX files have / how we match it
Constraint list	Already supported in schema and Python exporter	UI list of joints, usually one per non-root ragdoll bone	Matches shipped per-joint constraints
Constraint type	Not supported yet in the backend. Current schema only has one raw constraint shape in json_ragdoll_input.h:45, and builder always makes ragdoll constraints in ragdoll_scene_builder.cpp:160	Needed: enum for ragdoll vs limited hinge in backend and UI	Shipped HKX uses both hkRagdollConstraintData and hkLimitedHingeConstraintData, so we do not match fully yet
Body A / Body B	Already supported	UI can show parent body and child body, usually not editable for normal users	Matches shipped joint linkage
Pivot A / Pivot B	Already supported	Needed in UI if you want real control; otherwise limits will feel wrong	Shipped HKX absolutely has local joint frames and pivots; these are part of matching it correctly
Twist axis A / B	Already supported	Needed in UI or at least editable via advanced controls; also needed for accurate preview	Shipped ragdolls use twist axes; Havok docs define twist around this axis
Plane axis A / B	Already supported	Needed in UI or advanced controls; without this the plane min/max numbers are hard to understand	Shipped ragdolls use plane axes; this is how the cone is clipped
Twist min / max	Already supported and exported in ragdoll_export.py:778	UI slider or numeric fields	Shipped ragdolls use these heavily; direct match
Cone angle	Already supported	UI numeric field plus preview cone	Shipped ragdolls use cone max; direct match
Plane min / max	Already supported	UI numeric fields plus clipped-cone preview	Shipped ragdolls use plane min/max; direct match
Hinge min / max	Not supported yet in current schema/builder	Needed in backend and UI for elbows, knees, feet where DoW2 used limited hinge	Shipped HKX uses limited hinge on calves, forearms, and some feet
Joint friction torque	Not supported yet in current constraint schema	Needed in backend and UI if you want to match shipped stiffness	Shipped HKX uses meaningful joint friction values, especially on marine joints
Motors	Not really exposed in current exporter path	Safe to skip in V1	Shipped data had motors present but disabled, so not needed for first-pass matching
What DoW2 HKX Actually Has

DoW2 HKX feature	Current Blender backend	Needed to match it
Two real joint families: ragdoll and limited hinge	Partial	Add joint-type support
Ragdoll twist, cone, plane limits	Yes	Mostly UI and preview work
Limited hinge min/max	No	Add hinge fields and C++ builder support
Joint friction torque	No	Add constraint friction field and builder support
Local pivots and local joint axes	Yes in raw schema	Expose in advanced UI
Capsule and sphere bodies	Yes	Add editing UI and viewport gizmos
Separate animation skeleton and ragdoll skeleton	Yes	Add user-facing management UI
Bone mapping between skeletons	Yes	Add inspection and override UI
Frontend / UI State

UI area	What we have	What we need	How it helps match DoW2
Existing panel pattern	Yes, from physics UI in physics_panels.py:1	Reuse same pattern for ragdoll panel	Gives a familiar Blender-side workflow
Actual ragdoll panel	No	Add new ragdoll panel	Required
Skeleton selection UI	No	Needed	Lets user decide which bones become ragdoll bones
Rigid body editor	No	Needed	Lets user resize capsules and inspect bodies
Constraint editor	No	Needed	Lets user tune joints
Constraint type indicator	No	Needed	Makes hinge vs ragdoll obvious
Twist/cone/plane preview	No	Needed	Makes ragdoll joints understandable
Hinge arc preview	No	Needed	Makes hinge joints understandable
Advanced frame editing	No	Needed for accurate authoring	Necessary if the user wants more than presets
Short answer

If you want a non-overwhelming first version, the main user-facing controls should be:

V1 user control	Should it be in the UI?	Why
Ragdoll skeleton bone selection	Yes	Core workflow
Rigid body shape type	Yes	Core workflow
Capsule radius	Yes	Core workflow
Capsule height / length	Yes	Core workflow
Constraint type indicator	Yes	Core workflow
Ragdoll twist min/max	Yes	Core workflow
Ragdoll cone max	Yes	Core workflow
Ragdoll plane min/max	Yes	Core workflow
Hinge min/max	Yes, core flow
Joint friction torque, core flow
Pivot editing	Advanced	Important but can be hidden at first
Twist/plane axis editing	Advanced	Important but can be hidden at first
Body damping / restitution / filter flags	Advanced	Too much for most users at first
