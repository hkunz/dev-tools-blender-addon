=================================================================
# Dev Tools: The Unofficial JBeam Editor Addon for Blender
=================================================================

This is an unofficial Blender addon designed to simplify the process of editing JBeam files for BeamNG.drive. The addon provides an intuitive interface within Blender, enabling users to easily manipulate and visualize JBeam structures, such as nodes, beams, and triangles. In addition to basic editing, it also allows for the adjustment of scope modifiers related to each node, beam, and triangle. Whether you're working with vehicle mods or other custom JBeam configurations, this tool helps streamline the workflow by integrating JBeam editing directly within Blender's 3D environment.

![image](https://github.com/user-attachments/assets/2f429210-28d3-4437-bde5-6b4ce8094ba8)

**Features**:

* Edit and manage JBeam files without leaving Blender.

* Visualize nodes, beams, and triangles in the 3D view.

* Adjust scope modifiers related to each node, beam, and triangle.

* Simple integration with Blender's object and mesh system.

* Convenient for working on mods for BeamNG.drive.

**Importing JBeam Files**

When importing JBeam files, make sure every item ends with a comma. Since we use a JSON parser to read the files, any missing commas will result in the JBeam file being treated as invalid.

**Note**: This addon is not affiliated with BeamNG, and is meant as a community-driven tool to enhance Blender's utility for JBeam file manipulation.

=================================================================
# Create ZIP addon file (Unix & Linux)
=================================================================

* Run "make zip" or directly run ./scripts/build-zip.sh from root directory to create ZIP addon file
* Zip file will be created 1 level above the addon root folder

=================================================================
# Create ZIP addon file on Windows
=================================================================

* Make sure to install 7-Zip with 'C:\Program Files\7-Zip\7z.exe' present
* Go into scripts/windows/ folder
* Right click file build-zip.ps1 > Run with PowerShell to create ZIP addon file
* Zip file will be created 1 level above the addon root folder
