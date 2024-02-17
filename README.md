## What is this?

These scripts can help you extract assets from the PC game Crimson Skies (2000). They use [tobywf's mech3ax](https://github.com/TerranMechworks/mech3ax) to extract useful data from proprietary `.zbd` files, and then assemble these into `.blend` files which you can use in your own projects. They are mostly based on his work.

The scripts are written to work on Windows with an installed copy of the game. You will have to adapt them if you want to run them on a different platform.

![Exported Devastator model shown in Blender](devastator.jpg)

## How do I work this?

Of course you will need a copy of Crimson Skies. I can't help you with this. Install the game as normal.

Then you can download the code in this repo. Click the green 'Code' button and then 'Download ZIP'. You should unzip it after.

Then you will need to install some free software:

- [Python](https://www.python.org/downloads/), a programming language, for running the script
- [Blender](https://www.blender.org/download/), a program for working with 3D models

Now you can open a command line in the folder you put my scripts in. You can do this by typing `cmd` into the address bar of that folder and hitting enter.

Install one last dependency from the command line:
```
> pip install pillow
```
Now we can run our script:
```
> python everything2blend.py --unzbd "path/to/unzbd.exe"
```

## Where is that large automobile?

It's in one of those `.blend` files that just appeared, go check it out in Blender. Each file contains all the data it was possible to extract for that plane or level, so there will be some stuff you aren't interested in. The script tries to hide the boring stuff, but you can make it appear again with the eye buttons in the right-hand pane of Blender.

There are only minor issues remaining with these files. A few meshes are borked, some materials are incorrect and one or two textures are missing. But the assets are definitely good enough to work with.

## But how can I - 

Shh.
```
usage: everything2blend.py [-h] [--unzbd EXE] [--blender EXE]
                           [--cs FOLDER] [--data FOLDER] [--out FOLDER]
                           [--skip-unzbd] [--skip-planes] [--skip-levels]

Convert dumped Crimson Skies plane model data to blender files.

options:
  -h, --help     show this help message and exit
  --unzbd EXE    Path to unzbd executable
  --blender EXE  Path to your Blender executable
  --cs FOLDER    Path to CS install folder
  --data FOLDER  Folder for intermediate data
  --out FOLDER   Folder to save .blend files
  --skip-unzbd   Use existing unzbd output
  --skip-planes  Don't generate .blends for planes
  --skip-levels  Don't generate .blends for levels
```

## BONUS ROUND: .rof extraction

You may have noticed only one skin is available for each plane, whereas many different ones are used in-game. These skins are actually dynamically generated from the configuration for each faction, but the necessary files for doing this are hidden away in another proprietary archive file, `crimson.rof`.

There is a script for unpacking this archive:
```
> python extract_rof.py
```
And then another for decoding the texture files within into something more useful:
```
> python extract_bm.py
```
