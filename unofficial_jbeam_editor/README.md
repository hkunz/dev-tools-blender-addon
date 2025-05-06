=================================================================
# Dev Tools: The Unofficial JBeam Editor Addon for Blender
=================================================================

This is an unofficial Blender addon designed to simplify the process of editing JBeam files for BeamNG.drive. The addon provides an intuitive interface within Blender, enabling users to easily manipulate and visualize JBeam structures, such as nodes, beams, and triangles. In addition to basic editing, it also allows for the adjustment of scope modifiers related to each node, beam, and triangle. Whether you're working with vehicle mods or other custom JBeam configurations, this tool helps streamline the workflow by integrating JBeam editing directly within Blender's 3D environment.

![image](https://github.com/user-attachments/assets/9d2e4940-cb38-43ec-85f3-81f87cda37a5)


![jbeam-editor2](https://github.com/user-attachments/assets/feb4828a-297a-4024-8a28-47017f0af657)





**Features**:

* Edit and manage JBeam files without leaving Blender.

* Visualize nodes, beams, and triangles in the 3D view.

* Adjust scope modifiers related to each node, beam, and triangle.

* Simple integration with Blender's object and mesh system.

* Convenient for working on mods for BeamNG.drive.

**Example Console Output When Importing single Jbeam Files**

![image](https://github.com/user-attachments/assets/cee1732a-b0b2-4f57-af86-96936dbe19b7)


**Example Console Output When Importing PC Files**

![image](https://github.com/user-attachments/assets/50853460-9f0e-4729-b0e0-9174335fb702)


**Note**: This addon is not affiliated with BeamNG, and is meant as a community-driven tool to enhance Blender's utility for JBeam file manipulation. If you're interested in contributing or helping extend the functionality of this addon, feel free to get in touch!

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
